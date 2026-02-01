import os
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from utils import (
    delete_old_files,
    export_model_data,
    send_email,
)

from .exports import build_product_exports
from .models import (
    AdditionalMasterData,
    BlockedProduct,
    ExportTask,
    LogEntry,
    Product,
)
from .pricing import run_pricing_engine
from .utils import (
    CoreLog,
    FILE_ADDITIONAL_PRODUCTS,
    FILE_BLOCKED_PRODUCTS,
    FILE_PRODUCT_GTIN,
    sync_product_relations,
    upload_additional_products_to_db,
    upload_blocked_products_to_db,
    upload_product_gtin_to_db,
    validate_file_and_extract_rows,
)

from apps.aera.models import AeraCompetitorPrice, AeraProduct
from apps.aera.views import (
    clear_aera_session,
    fetch_aera_competitor_prices,
    fetch_aera_products,
    fetch_and_save_aera_orders,
    push_products_to_aera,
    push_products_to_aera_full_import,
)

from apps.shopware.models import ShopwareProduct
from apps.shopware.views import (
    push_products_to_shopware,
    fetch_shopware_products,
)

from apps.dentalheld.models import DentalheldProduct
from apps.dentalheld.views import (
    push_products_to_dentalheld,
    fetch_and_save_dentalheld_orders,
)

from apps.gls.models import (
    GLSMasterData,
    GLSPriceList,
    GLSPromotionPosition,
    GLSPromotionPrice,
    GLSSupplier,
    GLSProductGroup,
)
from apps.gls.views import (
    download_gls_files,
    fetch_gls_order_feedback,
    notify_cancelled_orders,
    parse_gls_file_data,
    push_dropshipping_orders_to_gls,
)

from apps.wawibox.models import WawiboxCompetitorPrice, WawiboxProduct
from apps.wawibox.views import (
    download_wawibox_files,
    fetch_and_save_wawibox_orders,
    parse_wawibox_file_data,
    push_products_to_wawibox,
)

from apps.weclapp.views import (
    sync_new_orders_from_marketplaces,
    sync_order_feedback_status,
    create_dropshipping_orders,
)

today = timezone.now().date()
is_first_day = today.day == 1


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def run_automations():
    eprint("started", timezone.now())

    # Fetch GLS data
    gls_files_downloaded = download_gls_files()
    eprint("gls_files_downloaded", timezone.now())
    gls_file_data_parsed = parse_gls_file_data()
    eprint("gls_file_data_parsed", timezone.now())
    gls_order_feedback_fetched = fetch_gls_order_feedback()
    eprint("gls_order_feedback_fetched", timezone.now())

    # Fetch Wawibox data
    wawibox_files_downloaded = download_wawibox_files()
    eprint("wawibox_files_downloaded", timezone.now())
    wawibox_file_data_parsed = parse_wawibox_file_data()
    eprint("wawibox_file_data_parsed", timezone.now())
    # wawibox_orders_fetched = fetch_and_save_wawibox_orders()
    # eprint("wawibox_orders_fetched", timezone.now())

    # Fetch Aera data
    clear_aera_session()
    if is_first_day:
        aera_products_fetched = fetch_aera_products()
        eprint("aera_products_fetched", timezone.now())
    aera_prices_fetched = fetch_aera_competitor_prices()
    eprint("aera_prices_fetched", timezone.now())
    aera_orders_fetched = fetch_and_save_aera_orders()
    eprint("aera_orders_fetched", timezone.now())

    # Fetch Dentalheld data
    dentalheld_orders_fetched = fetch_and_save_dentalheld_orders()
    eprint("dentalheld_orders_fetched", timezone.now())

    # Fetch Shopware data
    if is_first_day:
        shopware_products_fetched = fetch_shopware_products()
        eprint("shopware_products_fetched", timezone.now())

    # Update all db data
    create_missing_products()
    eprint("missing products updated", timezone.now())

    attach_product_fk()
    eprint("product fk attached", timezone.now())

    ############# Price Calculation and data push ##############

    # Calculate sales price
    prices_calculated = False
    if all(
        [
            gls_files_downloaded,
            gls_file_data_parsed,
            wawibox_files_downloaded,
            wawibox_file_data_parsed,
            aera_prices_fetched,
        ]
    ):
        prices_calculated = run_pricing_engine()
        eprint("prices_calculated", timezone.now())

    exports_prepared = False
    if prices_calculated:
        exports_prepared = build_product_exports()

    if exports_prepared:
        eprint("exports_prepared", timezone.now())
        # if is_first_day:
        #     push_products_to_aera_full_import()
        # else:
        #     push_products_to_aera()
        # push_products_to_wawibox()
        # push_products_to_shopware("sku here")
        # push_products_to_dentalheld()

    ############# Orders ##############
    # if all(
    #     [
    #         aera_orders_fetched,
    #         dentalheld_orders_fetched,
    #         # wawibox_orders_fetched,
    #     ]
    # ):
    #     sync_new_orders_from_marketplaces()

    create_dropshipping_orders()
    eprint("dropshipping orders created from weclapp", timezone.now())

    push_dropshipping_orders_to_gls()
    eprint("dropshipping orders pushed to gls", timezone.now())

    if gls_order_feedback_fetched:
        notify_cancelled_orders()
        eprint("notify_cancelled_orders", timezone.now())
        sync_order_feedback_status()
        eprint("synced_orders_to_weclapp", timezone.now())

    cleanup_logs(7)
    cleanup_exports(7)
    clear_aera_session()
    delete_old_files(7)
    eprint("Automation completed", timezone.now())

    return True


@staff_member_required
@require_POST
def upload_additional_products(request):
    uploaded_file = request.FILES.get("file")
    changelist_url = reverse("admin:core_additionalmasterdata_changelist")

    if not uploaded_file:
        messages.error(request, "Please choose a .xlsx file.")
        return redirect(changelist_url)

    try:
        rows = validate_file_and_extract_rows(uploaded_file, FILE_ADDITIONAL_PRODUCTS)
        upload_status = upload_additional_products_to_db(rows)
    except ValueError as err:
        messages.error(request, str(err))
        return redirect(changelist_url)
    except Exception as err:
        messages.error(request, f"Import failed: {err}")
        return redirect(changelist_url)

    filename = getattr(uploaded_file, "name", "")
    messages.success(
        request, f"Imported {upload_status.get('total', 0)} rows from “{filename}”."
    )
    return redirect(changelist_url)


@staff_member_required
@require_POST
def upload_blocked_products(request):
    uploaded_file = request.FILES.get("file")
    changelist_url = reverse("admin:core_blockedproduct_changelist")

    if not uploaded_file:
        messages.error(request, "Please choose a .xlsx file.")
        return redirect(changelist_url)

    try:
        rows = validate_file_and_extract_rows(uploaded_file, FILE_BLOCKED_PRODUCTS)
        upload_status = upload_blocked_products_to_db(rows)
    except ValueError as err:
        messages.error(request, str(err))
        return redirect(changelist_url)
    except Exception as err:
        messages.error(request, f"Import failed: {err}")
        return redirect(changelist_url)

    filename = getattr(uploaded_file, "name", "")
    messages.success(
        request, f"Imported {upload_status.get('total', 0)} rows from “{filename}”."
    )
    return redirect(changelist_url)


@staff_member_required
@require_POST
def upload_product_gtin(request):
    uploaded_file = request.FILES.get("file")
    changelist_url = reverse("admin:core_productgtin_changelist")

    if not uploaded_file:
        messages.error(request, "Please choose a .xlsx file.")
        return redirect(changelist_url)

    try:
        rows = validate_file_and_extract_rows(uploaded_file, FILE_PRODUCT_GTIN)
        upload_status = upload_product_gtin_to_db(rows)
    except ValueError as err:
        messages.error(request, str(err))
        return redirect(changelist_url)
    except Exception as err:
        messages.error(request, f"Import failed: {err}")
        return redirect(changelist_url)

    filename = getattr(uploaded_file, "name", "")
    messages.success(
        request, f"Imported {upload_status.get('total', 0)} rows from “{filename}”."
    )
    return redirect(changelist_url)


def create_missing_products():
    try:
        to_create = []

        # ---------------------------------------------------------
        # GLS PRODUCTS
        # ---------------------------------------------------------
        gls_items = GLSMasterData.objects.values(
            "article_no",
            "manufacturer_article_no",
            "article_group_no",
            "manufacturer",
            "description",
            "blocked",
            "store_refrigerated",
        )

        existing = set(Product.objects.values_list("supplier", "supplier_article_no"))

        incoming_gls = [
            (Product.SUPPLIER_GLS, item["article_no"])
            for item in gls_items
            if item["article_no"]
        ]

        missing_gls = [item for item in incoming_gls if item not in existing]

        gls_map = {g["article_no"]: g for g in gls_items}

        for supplier, supplier_article_no in missing_gls:
            g = gls_map.get(supplier_article_no)
            if not g:
                continue

            to_create.append(
                Product(
                    supplier=supplier,
                    supplier_article_no=supplier_article_no,
                    name=g.get("description"),
                    manufacturer_id=g.get("manufacturer"),
                    manufacturer_article_no=g.get("manufacturer_article_no"),
                    gls_article_group_no=g.get("article_group_no"),
                    is_blocked=g.get("blocked"),
                    store_refrigerated=g.get("store_refrigerated"),
                    sku=f"LG{supplier_article_no}",
                )
            )

        # ---------------------------------------------------------
        # NON-GLS PRODUCTS
        # ---------------------------------------------------------
        non_gls_items = AdditionalMasterData.objects.values(
            "article_no",
            "manufacturer_article_no",
            "manufacturer",
            "name",
            "store_refrigerated",
        )

        # refresh existing AFTER GLS additions
        existing = existing.union(set(missing_gls))

        incoming_non_gls = [
            (Product.SUPPLIER_NON_GLS, item["article_no"])
            for item in non_gls_items
            if item["article_no"]
        ]

        missing_non_gls = [item for item in incoming_non_gls if item not in existing]

        non_gls_map = {g["article_no"]: g for g in non_gls_items}

        for supplier, supplier_article_no in missing_non_gls:
            g = non_gls_map.get(supplier_article_no)

            if not g:
                continue

            manufacturer = g.get("manufacturer")

            if not manufacturer:
                continue

            to_create.append(
                Product(
                    supplier=supplier,
                    supplier_article_no=supplier_article_no,
                    name=g.get("name"),
                    manufacturer=manufacturer,
                    manufacturer_article_no=g.get("manufacturer_article_no"),
                    store_refrigerated=g.get("store_refrigerated"),
                    sku=f"{manufacturer[:2].upper()}{supplier_article_no}",
                )
            )

        if to_create:
            Product.objects.bulk_create(to_create, batch_size=5000)
            to_create = []

        # ---------------------------------------------------------
        # Blocked PRODUCTS
        # ---------------------------------------------------------
        blocked_items = BlockedProduct.objects.values(
            "article_no",
            "manufacturer_article_no",
            "manufacturer",
            "name",
        )

        blocked_skus = [
            item["article_no"] for item in blocked_items if item["article_no"]
        ]

        qs = Product.objects.filter(sku__in=blocked_skus)

        qs.update(is_blocked=True)

        existing_skus = set(qs.values_list("sku", flat=True))

        to_create = []
        blocked_map = {b["article_no"]: b for b in blocked_items}

        for sku in blocked_skus:
            if sku in existing_skus:
                continue

            b = blocked_map[sku]

            supplier = (
                Product.SUPPLIER_GLS
                if sku.startswith("LG")
                else Product.SUPPLIER_NON_GLS
            )

            to_create.append(
                Product(
                    supplier=supplier,
                    supplier_article_no=sku[2:],
                    sku=sku,
                    name=b.get("name"),
                    manufacturer=b.get("manufacturer"),
                    manufacturer_article_no=b.get("manufacturer_article_no"),
                    is_blocked=True,
                )
            )

        if to_create:
            Product.objects.bulk_create(to_create, batch_size=5000)

    except Exception:
        CoreLog.error(f"Product sync encountered an error: {traceback.format_exc()}")
        raise


def attach_product_fk():
    area_products_synced = sync_product_relations(AeraProduct, is_gls_model=False)
    area_price_synced = sync_product_relations(AeraCompetitorPrice, is_gls_model=False)
    wawi_products_synced = sync_product_relations(WawiboxProduct, is_gls_model=False)
    wawi_price_synced = sync_product_relations(
        WawiboxCompetitorPrice, is_gls_model=False
    )
    gls_mdata_synced = sync_product_relations(GLSMasterData)
    gls_price_synced = sync_product_relations(GLSPriceList)
    gls_promo_pos_synced = sync_product_relations(GLSPromotionPosition)
    gls_promo_price_synced = sync_product_relations(GLSPromotionPrice)
    add_mdata_synced = sync_product_relations(
        AdditionalMasterData, has_sku=False, is_gls_model=False
    )
    blocked_prod_synced = sync_product_relations(
        BlockedProduct, has_sku=False, is_gls_model=False
    )
    dentalheld_products_synced = sync_product_relations(
        DentalheldProduct, is_gls_model=False
    )
    shopware_products_synced = sync_product_relations(
        ShopwareProduct, is_gls_model=False
    )

    if all(
        [
            area_products_synced,
            area_price_synced,
            wawi_products_synced,
            wawi_price_synced,
            gls_mdata_synced,
            gls_price_synced,
            gls_promo_pos_synced,
            gls_promo_price_synced,
            add_mdata_synced,
            blocked_prod_synced,
            dentalheld_products_synced,
            shopware_products_synced,
        ]
    ):
        return True
    else:
        return False


@staff_member_required
@require_POST
def export_kaufland_data(request):
    file_type = request.POST.get("file_type") or "excel"
    changelist_url = reverse("admin:core_productgtin_changelist")

    if file_type not in ["csv", "excel"]:
        messages.error(request, "Please choose a valid file type.")
        return redirect(changelist_url)

    config = {
        "file_type": file_type,
        "model_label": "core.ProductGtin",
        "display_name": "Kaufland_GPRS",
        "exclude_fields": ["id", "article_no", "pk", "sku", "supplier", "updated_at"],
    }

    ExportTask.objects.create(
        user=request.user,
        name=config["display_name"],
        file_type=file_type,
        config=config,
    )

    messages.success(
        request,
        "Export task has been created. You will receive an email once it is ready for download.",
    )
    return redirect(changelist_url)


@staff_member_required
@require_POST
def export_amazon_data(request):
    file_type = request.POST.get("file_type") or "excel"
    changelist_url = reverse("admin:core_productgtin_changelist")

    if file_type not in ["csv", "excel"]:
        messages.error(request, "Please choose a valid file type.")
        return redirect(changelist_url)

    config = {
        "file_type": file_type,
        "model_label": "core.ProductGtin",
        "display_name": "Amazon_GPRS",
        "exclude_fields": ["id", "article_no", "pk", "sku", "supplier", "updated_at"],
    }

    ExportTask.objects.create(
        user=request.user,
        name=config["display_name"],
        file_type=file_type,
        config=config,
    )

    messages.success(
        request,
        "Export task has been created. You will receive an email once it is ready for download.",
    )
    return redirect(changelist_url)


def process_pending_exports():

    pending_tasks = ExportTask.objects.filter(
        status__in=[
            ExportTask.STATUS_PENDING,
            ExportTask.STATUS_FAILED,
        ]
    )

    for task in pending_tasks:
        task.status = ExportTask.STATUS_PROCESSING
        task.save(update_fields=["status"])

        try:
            response = export_model_data(task.config)
            file_ext = ".csv" if task.file_type == "csv" else ".xlsx"
            display_name = task.config.get("display_name")
            filename = f"{display_name}_{timezone.now().strftime('%d%m%Y')}{file_ext}"

            export_dir = Path(settings.MEDIA_ROOT) / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)

            file_path = export_dir / filename
            with open(file_path, "wb") as f:
                if isinstance(response, HttpResponse):
                    f.write(response.content)
                else:
                    f.write(response)

            download_url = get_download_url(file_path)
            task.download_url = download_url
            task.status = ExportTask.STATUS_DONE
            task.error_message = None
            task.completed_at = timezone.now()
            task.save(
                update_fields=[
                    "download_url",
                    "status",
                    "error_message",
                    "completed_at",
                ]
            )

            if task.user and task.user.email:
                subject = f"Your {task.file_type} export is ready"
                template = "email/file_export.html"
                context = {
                    "task": task,
                    "download_url": task.download_url,
                }
                send_email(subject, template, context, recipient_email=task.user.email)

        except Exception:
            task.status = ExportTask.STATUS_FAILED
            task.error_message = str(traceback.format_exc())
            task.save(update_fields=["status", "error_message"])

    return True


@require_GET
def download_file(request):
    file_path = request.GET.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise Http404("File not found")

    return FileResponse(
        open(file_path, "rb"), as_attachment=True, filename=os.path.basename(file_path)
    )


def get_download_url(file_path):
    return f"{settings.SITE_URL}{reverse('download_file')}?file_path={file_path}"


def cleanup_logs(days):
    limit = datetime.now() - timedelta(days=days)
    LogEntry.objects.filter(created_at__lt=limit).delete()


def cleanup_exports(days):
    limit = datetime.now() - timedelta(days=days)
    old_tasks = ExportTask.objects.filter(created_at__lt=limit)

    for task in old_tasks:
        if task.download_url:
            try:
                query = urlparse(task.download_url).query
                file_param = parse_qs(query).get("file_path", [])

                if file_param:
                    relative_path = file_param[0]
                    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

                    if os.path.isfile(full_path):
                        os.remove(full_path)

            except Exception:
                pass

        task.delete()


def reset_middleware_for_prod():
    from apps.weclapp.models import CustomsPositionMap

    Product.objects.update(weclapp_id=None)
    GLSSupplier.objects.update(weclapp_id=None)
    GLSProductGroup.objects.update(weclapp_id=None)
    CustomsPositionMap.objects.all().delete()


def core(request):
    from django.http import JsonResponse

    data = run_pricing_engine()
    # data = create_missing_products()
    # data = build_product_exports()
    # data = notify_cancelled_orders()
    return JsonResponse(data, safe=False)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from pathlib import Path
import os
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET

from apps.gls.views import (
    download_gls_files,
    parse_gls_file_data,
    push_dropshipping_orders_to_gls,
    fetch_gls_order_feedback,
    notify_cancelled_orders,
)
from apps.gls.models import (
    GLSMasterData,
    GLSPriceList,
    GLSPromotionPosition,
    GLSPromotionPrice,
)
from apps.aera.views import (
    fetch_aera_competitor_prices,
    push_aera_data,
    fetch_and_save_aera_orders,
    fetch_aera_products,
    clear_aera_session,
)
from apps.aera.models import (
    AeraCompetitorPrice,
    AeraProduct,
)
from apps.wawibox.models import (
    WawiboxProduct,
    WawiboxCompetitorPrice,
)
from apps.wawibox.views import (
    push_wawibox_data,
    fetch_and_save_wawibox_orders,
    download_wawibox_files,
    parse_wawibox_file_data,
)
from .utils import (
    validate_file_and_extract_rows,
    upload_additional_products_to_db,
    upload_blocked_products_to_db,
    FILE_ADDITIONAL_PRODUCTS,
    FILE_BLOCKED_PRODUCTS,
    sync_product_relations,
)
from utils import (
    export_model_data,
    send_email,
)
from .models import (
    AdditionalMasterData,
    BlockedProduct,
    ExportTask,
    Product,
)


def run_automations():
    print("started", timezone.now())

    # Fetch GLS data
    gls_files_downloaded = download_gls_files()
    print("finished stage1", timezone.now())
    gls_file_data_parsed = parse_gls_file_data()
    print("finished stage2", timezone.now())
    gls_order_feedback_fetched = fetch_gls_order_feedback()
    print("finished stage3", timezone.now())

    # Fetch Wawibox data
    wawibox_files_downloaded = download_wawibox_files()
    print("finished stage4", timezone.now())
    wawibox_file_data_parsed = parse_wawibox_file_data()
    print("finished stage5", timezone.now())
    wawibox_orders_fetched = fetch_and_save_wawibox_orders()
    print("finished stage6", timezone.now())

    # Fetch Aera data
    aera_products_fetched = fetch_aera_products()
    print("finished stage7", timezone.now())
    aera_prices_fetched = fetch_aera_competitor_prices()
    print("finished stage8", timezone.now())
    aera_orders_fetched = fetch_and_save_aera_orders()
    print("finished stage9", timezone.now())
    # dentalheld_orders_fetched = fetch_and_save_dentalheld_orders()

    # Update all db data
    create_missing_products()
    print("finished stage10", timezone.now())

    attach_product_fk()
    print("finished stage12", timezone.now())

    ############# Price Calculation and data push ##############

    # Calculate sales price
    # prices_calculated = False
    # if all(
    #     [
    #         gls_files_downloaded,
    #         gls_file_data_parsed,
    #         wawibox_files_downloaded,
    #         wawibox_file_data_parsed,
    #         aera_prices_fetched,
    #     ]
    # ):
    #     # Perform pricing calculation logic
    #     prices_calculated = True

    # if prices_calculated:
    #     pass
    #     # push_aera_data()
    #     # push_wawibox_data()
    #     # push_shopware_data()
    #     # push_dentalheld_data()
    #     # push_weclapp_data()

    ############# Orders ##############

    # if all(
    #     [
    #         aera_orders_fetched,
    #         wawibox_orders_fetched,
    #         # dentalheld_orders_fetched,
    #     ]
    # ):
    #     pass
    #     #  push_orders_to_weclapp()

    # dropshipping_ready = process_weclapp_dropshipping()
    # build the order to match the gls order header and order line models, infact populate those models
    # if dropshipping_ready:
    #     push_dropshipping_orders_to_gls()

    if gls_order_feedback_fetched:
        notify_cancelled_orders()
        print("finished stage13", timezone.now())
    # push_feedback_to_weclapp()

    clear_aera_session()
    print("finished stage14", timezone.now())

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


def create_missing_products():
    to_create = []

    # ---------------------------------------------------------
    # GLS PRODUCTS
    # ---------------------------------------------------------
    gls_items = GLSMasterData.objects.values(
        "article_no",
        "manufacturer_article_no",
        "manufacturer",
        "description",
        "blocked",
    )

    existing = set(Product.objects.values_list("supplier", "supplier_article_no"))

    incoming_gls = [
        ("GLS", item["article_no"]) for item in gls_items if item["article_no"]
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
                is_blocked=g.get("blocked"),
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
    )

    # refresh existing AFTER GLS additions
    existing = existing.union(set(missing_gls))

    incoming_non_gls = [
        ("NON-GLS", item["article_no"]) for item in non_gls_items if item["article_no"]
    ]

    missing_non_gls = [item for item in incoming_non_gls if item not in existing]

    non_gls_map = {g["article_no"]: g for g in non_gls_items}

    for supplier, supplier_article_no in missing_non_gls:
        g = non_gls_map.get(supplier_article_no)
        if not g:
            continue

        manufacturer = g.get("manufacturer")

        to_create.append(
            Product(
                supplier=supplier,
                supplier_article_no=supplier_article_no,
                name=g.get("name"),
                manufacturer=manufacturer,
                manufacturer_article_no=g.get("manufacturer_article_no"),
                sku=f"{(manufacturer or '')[:2].upper()}{supplier_article_no}",
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

    blocked_skus = [item["article_no"] for item in blocked_items if item["article_no"]]

    qs = Product.objects.filter(sku__in=blocked_skus)

    qs.update(is_blocked=True)

    existing_skus = set(qs.values_list("sku", flat=True))

    to_create = []
    blocked_map = {b["article_no"]: b for b in blocked_items}

    for sku in blocked_skus:
        if sku in existing_skus:
            continue

        b = blocked_map[sku]

        supplier = "GLS" if sku.startswith("LG") else "NON-GLS"

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


def attach_product_fk():
    area_price_synced = sync_product_relations(AeraCompetitorPrice, is_gls_model=False)
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

    if all(
        [
            area_price_synced,
            wawi_price_synced,
            gls_mdata_synced,
            gls_price_synced,
            gls_promo_pos_synced,
            gls_promo_price_synced,
            add_mdata_synced,
            blocked_prod_synced,
        ]
    ):
        return True
    else:
        return False


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
            filename = f"{task.model_label.replace('.', '_')}_{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"

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

        except Exception as e:
            task.status = ExportTask.STATUS_FAILED
            task.error_message = str(e)
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

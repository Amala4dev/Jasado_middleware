from apps.gls.models import GLSOrderStatus
from django.conf import settings
import time, requests
import traceback
from django.http import JsonResponse
from apps.core.models import Product
from apps.aera.models import AeraOrder
from django.http import JsonResponse
import json
from apps.dentalheld.models import DentalheldOrder
from apps.gls.models import (
    GLSSupplier,
    GLSMasterData,
    GLSProductGroup,
    GLSOrderHeader,
    GLSOrderLine,
)
from django.db import transaction
from .models import CustomsPositionMap
from apps.gls.utils import clean_gls_address
from .client import (
    fetch_order_by_order_number,
    create_weclapp_order,
    get_customer_id,
    create_weclapp_custom_number,
    create_weclapp_manufacturer,
    create_article_category,
    test_weclapp_endpoint,
    fetch_dropshipping_orders,
    get_customer,
    confirm_purchase_order,
    fetch_purchase_order_by_sales_order_id,
    update_purchase_order,
    create_invoice_from_shipment,
    fetch_latest_shipment_by_order_id,
    check_serial_number_required,
    set_purchase_order_for_entry,
    fetch_purchase_order_by_weclapp_id,
    fetch_sales_order_by_weclapp_id,
)
from copy import deepcopy

from utils import normalize_text

from .utils import (
    WeclappLog,
    weclapp_clean_payload,
    upsert_custom_attribute,
    parse_gls_expiry_date,
    parse_gls_shipping_date,
)

# Constants
WECLAPP_BASE_URL = settings.WECLAPP_BASE_URL
WECLAPP_API_TOKEN = settings.WECLAPP_API_TOKEN


def get_headers():
    headers = {
        "AuthenticationToken": WECLAPP_API_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "User-Agent": "Jasado Middleware",
    }

    return headers


def bootstrap_weclapp_ids():
    missing_ids_exists = Product.objects.filter(
        supplier=Product.SUPPLIER_GLS, is_blocked=False, weclapp_id__isnull=True
    ).exists()
    if not missing_ids_exists:
        return True

    headers = get_headers()
    page = 1
    page_size = 1000

    while True:
        url = f"{WECLAPP_BASE_URL}/article?page={page}&pageSize={page_size}"
        r = requests.get(url, headers=headers)
        r.raise_for_status()

        articles = r.json().get("result", [])
        if not articles:
            break

        sku_map = {
            a["articleNumber"]: {
                "id": a["id"],
                "supply_source_id": (
                    a["supplySources"][0].get("articleSupplySourceId")
                    if a.get("supplySources")
                    else None
                ),
            }
            for a in articles
            if a.get("articleNumber")
        }

        products = list(
            Product.objects.filter(
                sku__in=sku_map.keys(),
                weclapp_id__isnull=True,
            )
        )

        for p in products:
            data = sku_map.get(p.sku)
            if data:
                p.weclapp_id = data["id"]
                p.weclapp_article_supply_source_id = data["supply_source_id"]

        if products:
            Product.objects.bulk_update(
                products,
                ["weclapp_id", "weclapp_article_supply_source_id"],
                batch_size=1000,
            )

        page += 1
        time.sleep(0.2)
    return True


def bootstrap_manufacturer_weclapp_ids():
    suppliers = GLSSupplier.objects.filter(weclapp_id__isnull=True)
    if not suppliers:
        return True

    suppliers = list(suppliers)

    headers = get_headers()
    page = 1
    page_size = 1000
    id_map = {}

    while True:
        url = f"{WECLAPP_BASE_URL}/manufacturer?page={page}&pageSize={page_size}"
        r = requests.get(url, headers=headers)
        r.raise_for_status()

        manufacturers = r.json().get("result", [])
        if not manufacturers:
            break

        for m in manufacturers:
            id_map[normalize_text(m["name"])] = m["id"]

        page += 1
        time.sleep(0.2)

    for s in suppliers:
        key = normalize_text(s.name1)
        if key in id_map:
            s.weclapp_id = id_map[key]
        else:
            s.weclapp_id = create_weclapp_manufacturer(s.name1)

    GLSSupplier.objects.bulk_update(
        suppliers,
        ["weclapp_id"],
        batch_size=1000,
    )

    return True


def bootstrap_article_category_weclapp_ids():
    product_groups = GLSProductGroup.objects.filter(weclapp_id__isnull=True)
    if not product_groups:
        return True

    product_groups = list(product_groups)

    headers = get_headers()
    page = 1
    page_size = 1000
    id_map = {}

    while True:
        url = f"{WECLAPP_BASE_URL}/articleCategory?page={page}&pageSize={page_size}"
        r = requests.get(url, headers=headers)
        r.raise_for_status()

        categories = r.json().get("result", [])
        if not categories:
            break

        for c in categories:
            id_map[normalize_text(c["name"])] = c["id"]

        page += 1
        time.sleep(0.2)

    for p in product_groups:
        key = normalize_text(p.product_group_no)
        if key in id_map:
            p.weclapp_id = id_map[key]
        else:
            payload = {
                "description": p.product_group_name,
                "name": p.product_group_no,
            }
            p.weclapp_id = create_article_category(payload)

    GLSProductGroup.objects.bulk_update(
        product_groups,
        ["weclapp_id"],
        batch_size=1000,
    )

    return True


def bootstrap_customs_position_weclapp_ids():
    # customs_numbers = GLSMasterData.objects.exclude(
    #     customs_position__isnull=True
    # ).values_list("customs_position", flat=True)

    # existing = set(CustomsPositionMap.objects.values_list("customs_number", flat=True))

    # missing = set(customs_numbers) - existing

    missing = (
        GLSMasterData.objects.exclude(customs_position__isnull=True)
        .exclude(
            customs_position__in=CustomsPositionMap.objects.values_list(
                "customs_number", flat=True
            )
        )
        .values_list("customs_position", flat=True)
    )
    missing = set(missing)

    if not missing:
        return True

    headers = get_headers()
    page = 1
    page_size = 1000
    weclapp_map = {}

    while True:
        url = f"{WECLAPP_BASE_URL}/customsTariffNumber?page={page}&pageSize={page_size}"
        r = requests.get(url, headers=headers)
        r.raise_for_status()

        result = r.json().get("result", [])
        if not result:
            break

        for p in result:
            weclapp_map[p["name"]] = p["id"]

        page += 1
        time.sleep(0.2)

    objs = []
    for number in missing:
        weclapp_id = weclapp_map.get(number)
        if not weclapp_id:
            weclapp_id = create_weclapp_custom_number(number)

        objs.append(
            CustomsPositionMap(
                customs_number=number,
                weclapp_id=weclapp_id,
            )
        )

    CustomsPositionMap.objects.bulk_create(
        objs,
        ignore_conflicts=True,
        batch_size=1000,
    )

    return True


def sync_new_orders_from_marketplaces():
    try:
        ORDER_MODELS = [
            AeraOrder,
            DentalheldOrder,
            # WawiboxOrder,
        ]
        for model in ORDER_MODELS:
            app_name = model._meta.app_label
            orders = model.objects.filter(synced_to_weclapp=False)
            orders_created = []

            for order in orders:
                customer_id = get_customer_id(order)
                payload = order.build_weclapp_order_payload(customer_id)
                weclapp_order = create_weclapp_order(payload)

                if weclapp_order:
                    order.synced_to_weclapp = True
                    order.weclapp_id = weclapp_order["id"]
                    order.save()
                    orders_created.append(order.order_number)
                else:
                    WeclappLog.error(
                        f"Failed to create {app_name} order on weclapp with order number {order.order_number}."
                    )

            if orders_created:
                WeclappLog.info(
                    f"{app_name} orders with the following order_numbers were created on weclapp successfully: {', '.join(orders_created)}."
                )

    except Exception:
        WeclappLog.error(
            f"Error occured during order creation to weclapp: {traceback.format_exc()}."
        )


def process_dropshipping(purchase_order, feedback_status):
    confirm_purchase_order(purchase_order["id"])
    url = f"{WECLAPP_BASE_URL}/purchaseOrder/id/{purchase_order['id']}/processDropshipping"
    headers = get_headers()
    payload = {
        "shipmentParameters": {
            "deliveryDate": parse_gls_shipping_date(feedback_status.delivery_date),
            "deliveryNoteNumber": feedback_status.control_number,
            "shippingDate": parse_gls_shipping_date(feedback_status.pack_date),
        },
        "processPurchaseOrderItems": [],
    }

    po_items = purchase_order.get("purchaseOrderItems", [])

    for po_item in po_items:
        if str(po_item.get("positionNumber")) == str(feedback_status.position):
            serial_no_required = check_serial_number_required(po_item)
            if serial_no_required:
                payload["processPurchaseOrderItems"].append(
                    {
                        "purchaseOrderItemId": po_item["id"],
                        "quantity": feedback_status.ordered_qty,
                    }
                )
            else:
                payload["processPurchaseOrderItems"].append(
                    {
                        "purchaseOrderItemId": po_item["id"],
                        "quantity": feedback_status.delivered_qty,
                    }
                )

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()

    try:
        error = response.json()
        message = (
            error.get("messages", [{}])[0].get("message")
            or error.get("detail")
            or error.get("error")
        )
    except ValueError:
        message = response.text

    WeclappLog.error(
        f"Process dropshipping failed for purchase order with weclapp id = {purchase_order['id']}: {message}"
    )

    return False


def build_purchase_order_update_payload(feedback_status, weclapp_po_payload):
    payload = deepcopy(weclapp_po_payload)

    package_number = feedback_status.package_number

    if package_number:
        payload["packageTrackingNumber"] = package_number

    po_items = payload.get("purchaseOrderItems", [])

    for item in po_items:
        if str(item.get("positionNumber")) == str(feedback_status.position):

            if feedback_status.backorder_text:
                item["note"] = feedback_status.backorder_text

            if feedback_status.status_info:
                attrs = item.get("customAttributes", [])
                attrs = upsert_custom_attribute(
                    attrs,
                    attr_id="314851734",
                    stringValue=feedback_status.status_info,
                )
                item["customAttributes"] = attrs

            serial_no_required = check_serial_number_required(item)
            if serial_no_required and feedback_status.batch_number:
                item["batchSerialNumbers"] = [
                    {
                        "batchNumber": feedback_status.batch_number,
                        "quantity": str(feedback_status.ordered_qty),
                        "expirationDate": parse_gls_expiry_date(
                            feedback_status.expiry_date
                        ),
                    }
                ]

    payload["purchaseOrderItems"] = po_items

    return weclapp_clean_payload(payload)


def sync_order_feedback_status():
    try:
        feedback_status_qs = GLSOrderStatus.objects.sync_to_weclapp()

        orders_synced = []

        for status in feedback_status_qs:
            order_number = status.order_number
            control_number = status.control_number

            sales_order = fetch_order_by_order_number(order_number)
            if not sales_order:
                WeclappLog.error(
                    f"GLS feedback for order {order_number}, but sales order not found."
                )
                continue

            purchase_order = fetch_purchase_order_by_sales_order_id(sales_order["id"])
            if not purchase_order:
                WeclappLog.error(
                    f"No purchase order found for sales order {order_number}."
                )
                continue

            set_purchase_order_for_entry(purchase_order["id"])
            purchase_order = fetch_purchase_order_by_sales_order_id(sales_order["id"])

            po_payload = build_purchase_order_update_payload(status, purchase_order)
            po_updated = update_purchase_order(po_payload)
            if po_updated:
                dropship = process_dropshipping(purchase_order, status)
                if dropship:
                    sales_order_id = dropship["result"]["salesOrderId"]
                    shipment = fetch_latest_shipment_by_order_id(sales_order_id)
                    create_invoice_from_shipment(shipment["id"])

                    GLSOrderStatus.objects.filter(
                        order_number=order_number,
                        control_number=control_number,
                    ).update(synced_to_weclapp=True)

                    orders_synced.append(order_number)

        if orders_synced:
            WeclappLog.info(
                f"The following gls order feedbacks updated on weclapp succesfully {', '.join(orders_synced)}."
            )

    except Exception:
        WeclappLog.error(
            f"Error occurred during order sync to weclapp: {traceback.format_exc()}"
        )


def create_dropshipping_orders(orders=None):
    if not orders:
        orders = fetch_dropshipping_orders()

    for order in orders:
        order_number = order.get("orderNumber")
        if not order_number:
            continue

        try:
            with transaction.atomic():
                customer = get_customer(order.get("customerId"))
                header, created = GLSOrderHeader.objects.get_or_create(
                    order_number=order_number,
                    defaults={
                        "customer_id": order.get("customerId"),
                        "end_customer_no": order.get("customerId"),
                        "billing_name": clean_gls_address(
                            order.get("invoiceAddress", {}).get("company")
                        ),
                        "billing_name2": clean_gls_address(
                            order.get("invoiceAddress", {}).get("company2")
                        ),
                        "billing_street": clean_gls_address(
                            f"{order.get('invoiceAddress', {}).get('street1')}, {order.get('invoiceAddress', {}).get('street2')}"
                        ),
                        "billing_zip": order.get("invoiceAddress", {}).get("zipcode"),
                        "billing_city": clean_gls_address(
                            order.get("invoiceAddress", {}).get("city")
                        ),
                        "billing_country": order.get("invoiceAddress", {}).get(
                            "countryCode"
                        ),
                        "shipping_name": clean_gls_address(
                            order.get("deliveryAddress", {}).get("company")
                        ),
                        "shipping_name2": clean_gls_address(
                            order.get("deliveryAddress", {}).get("company2")
                        ),
                        "shipping_street": clean_gls_address(
                            f"{order.get('deliveryAddress', {}).get('street1')}, {order.get('deliveryAddress', {}).get('street2')}"
                        ),
                        "shipping_zip": order.get("deliveryAddress", {}).get("zipcode"),
                        "shipping_city": clean_gls_address(
                            order.get("deliveryAddress", {}).get("city")
                        ),
                        "shipping_country": order.get("deliveryAddress", {}).get(
                            "countryCode"
                        ),
                        "email_address": order.get("deliveryEmailAddresses", {}).get(
                            "toAddresses"
                        ),
                        "phone_number": customer.get("phone"),
                        "vat_id": customer.get("vatIdentificationNumber"),
                    },
                )

                if not created:
                    continue

                for item in order.get("orderItems", []):

                    product = Product.objects.filter(
                        weclapp_id=item.get("articleId")
                    ).first()
                    if not product or not product.supplier_article_no:
                        raise ValueError(
                            f"Missing product for articleId={item.get('articleId')}, "
                            f"order={order_number}"
                        )

                    if product.supplier != Product.SUPPLIER_GLS:
                        WeclappLog.warning(
                            f"Skipping dropshipping for artcle with articleId={item.get('articleId')}, it is not supplied by GLS"
                        )
                        continue

                    GLSOrderLine.objects.create(
                        order_header=header,
                        order_number=order_number,
                        position=item.get("positionNumber"),
                        gls_article_no=product.supplier_article_no,
                        customer_article_no=product.sku,
                        qty=item.get("quantity"),
                    )
        except Exception:
            WeclappLog.error(str(traceback.format_exc()))
            continue


def purchase_order_webhook(request):
    from apps.gls.views import push_dropshipping_orders_to_gls

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body)

        entity_id = payload.get("entityId")
        entity_name = payload.get("entityName")
        event_type = payload.get("type")

        if entity_name == "PURCHASE_ORDER" and event_type == "CREATE":
            purchase_order = fetch_purchase_order_by_weclapp_id(entity_id)
            sales_order = fetch_sales_order_by_weclapp_id(
                purchase_order["salesOrderId"]
            )
            create_dropshipping_orders([sales_order])
            # push_dropshipping_orders_to_gls()
        return JsonResponse(status=200)

    except Exception:
        WeclappLog.error(f"Error occured with webhook {str(traceback.format_exc())}")
        return JsonResponse(status=400)


def index(request):
    # from .client import process_dropshipping
    from .client import create_dropshipping_from_order

    # data = fetch_and_save_aera_orders()
    # data = test_weclapp_endpoint()
    # data = fetch_dropshipping_orders()
    # data = get_customer("279654987")
    # data = create_weclapp_order()
    # data = fetch_latest_shipment_by_order_id("314853249")
    # data = create_shipment_from_order("312794644")
    # data = update_article_category_desc()
    # data = bootstrap_article_category_weclapp_ids()
    # data = clean_article_category_weclapp_ids()
    # data = bootstrap_manufacturer_weclapp_ids()
    # data = bootstrap_customs_position_weclapp_ids()
    # data = create_dropshipping_orders()
    # data = create_shipment_from_order("314851222")
    # data = process_dropshipping("314852021", order_status_to_sync)
    data = sync_order_feedback_status()
    # data = confirm_purchase_order("314853645")
    # data = sync_new_orders_from_marketplaces()
    # data = create_dropshipping_from_order()
    # data = check_serial_number_required()
    # return HttpResponse(data)
    return JsonResponse(data, safe=False)

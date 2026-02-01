from datetime import date
import traceback

import requests

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from utils import clean_payload, make_time_zone_aware

from .models import (
    AeraCompetitorPrice,
    AeraExport,
    AeraOrder,
    AeraOrderItem,
    AeraProduct,
    AeraSession,
)
from .utils import AeraLog


# Constants
AERA_BASE_URL = settings.AERA_BASE_URL
AERA_COMPANY_ID = settings.AERA_COMPANY_ID
AERA_LOGIN_NAME = settings.AERA_LOGIN_NAME
AERA_PASSWORD = settings.AERA_PASSWORD


def get_aera_session_id():
    session_obj = AeraSession.objects.first()
    if session_obj:
        session_id = session_obj.session_id
    else:
        session_id = create_aera_session()
    return session_id


def clear_aera_session():
    AeraSession.objects.all().delete()


def create_aera_session():
    url = f"{AERA_BASE_URL}/login"
    payload = {
        "Data": {
            "CreateUserSessionData": {
                "LoginName": AERA_LOGIN_NAME,
                "Password": AERA_PASSWORD,
            }
        }
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        session_id = data["Data"]["UserSessionForInfo"]["Id"]
        AeraSession.objects.update_or_create(pk=1, defaults={"session_id": session_id})
        return session_id

    else:
        AeraLog.error("Failed to obtain Aera session ID from login")
        raise


def fetch_aera_products():
    url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Offers"
    session_id = get_aera_session_id()

    headers = {
        "Ao-SessionId": session_id,
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    items = response.json()["Data"]["OfferList"]["Items"]

    objs = []
    existing_skus_on_db = set(AeraProduct.objects.values_list("sku", flat=True))

    for p in items:
        if p["SKU"] in existing_skus_on_db:
            continue
        objs.append(AeraProduct(sku=p["SKU"], aera_id=p["ProductId"]))

    if objs:
        AeraProduct.objects.bulk_create(objs, batch_size=5000)


def fetch_aera_competitor_prices(sku=None):
    url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Offers/CompetitorOffers"
    params = {
        "ResultType": "OfferListWithTop",
        "OfferPriceTypeId": 1,
    }
    if sku:
        params["SKU"] = sku

    session_id = get_aera_session_id()

    headers = {
        "Ao-SessionId": session_id,
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        AeraLog.error("Failed to fetch competitor prices")
        response.raise_for_status()

    AeraLog.info("Fetched competitor prices successfully")
    data = response.json()
    prices = data["Data"]["OfferListWithTop"]["Items"]
    batch_size = 500
    now = timezone.now()

    for i in range(0, len(prices), batch_size):
        batch = prices[i : i + batch_size]
        sku_list = [b["SKU"] for b in batch]

        existing_skus = {
            p.sku: p for p in AeraCompetitorPrice.objects.filter(sku__in=sku_list)
        }
        updated_products = []
        new_products = []

        for item in batch:
            sku = item["SKU"]
            if sku in existing_skus.keys():
                p = existing_skus[sku]
                p.net_own = item["OwnNetPrice"]
                p.net_top_1 = item["Top1NetPrice"]
                p.net_top_2 = item["Top2NetPrice"]
                p.net_top_3 = item["Top3NetPrice"]
                p.last_fetch_from_aera = now
                updated_products.append(p)
            else:
                new_products.append(
                    AeraCompetitorPrice(
                        sku=sku,
                        net_own=item["OwnNetPrice"],
                        net_top_1=item["Top1NetPrice"],
                        net_top_2=item["Top2NetPrice"],
                        net_top_3=item["Top3NetPrice"],
                        last_fetch_from_aera=now,
                    )
                )

        with transaction.atomic():
            if updated_products:
                AeraCompetitorPrice.objects.bulk_update(
                    updated_products,
                    [
                        "net_own",
                        "net_top_1",
                        "net_top_2",
                        "net_top_3",
                        "last_fetch_from_aera",
                    ],
                )
            if new_products:
                AeraCompetitorPrice.objects.bulk_create(new_products)

    return True


def push_products_to_aera(sku=None):
    BATCH_SIZE = 300000
    batch_payload = []
    batch_ids = []
    total_synced = 0
    processing_date = date.today().isoformat()

    try:
        product_exports = (
            AeraExport.objects.filter(sku=sku) if sku else AeraExport.objects.all()
        )
        for p in product_exports.iterator(chunk_size=BATCH_SIZE):
            if not p.sales_price:
                continue

            product_payload = {
                "SKU": p.sku,
                "Manufacturer": p.manufacturer,
                "MPN": p.mpn,
                "OfferTypeId": p.offer_type_id,
                "GTIN": p.gtin,
                "ProductName": p.product_name,
                "AvailabilityTypeId": p.availability_type_id,
                "DifferentDeliveryTime": p.different_delivery_time,
                "LowerBound1": 1,
                "NetPrice1": p.sales_price,
                "ShippedTemperatureStable": p.shipped_temperature_stable,
            }

            product_payload = clean_payload(product_payload)

            batch_payload.append(product_payload)
            batch_ids.append(p.id)

            if len(batch_payload) >= BATCH_SIZE:
                _upsert_product_batch(batch_payload, batch_ids, processing_date)
                total_synced += len(batch_payload)
                batch_payload.clear()
                batch_ids.clear()

        if batch_payload:
            _upsert_product_batch(batch_payload, batch_ids, processing_date)
            total_synced += len(batch_payload)

        push_special_offers_to_aera(sku=sku)
        AeraLog.info(
            f"Product update on marketplace completed successfully. Total products updated:{total_synced}"
        )

    except Exception:
        AeraLog.error(
            f"Product update on marketplace failed after updating {total_synced} products: {traceback.format_exc()}"
        )


def push_special_offers_to_aera(sku=None):
    BATCH_SIZE = 300000
    batch_payload = []
    processing_date = date.today().isoformat()

    try:
        product_exports = (
            AeraExport.objects.filter(sku=sku, gift_sales_price__isnull=False)
            if sku
            else AeraExport.objects.filter(gift_sales_price__isnull=False)
        )

        for p in product_exports.iterator(chunk_size=BATCH_SIZE):

            product_payload = {
                "SKU": p.sku,
                "ValidThrough": p.gift_valid_until.isoformat(),
                "Discountable": False,
                "LowerBound1": p.gift_min_qty,
                "NetPrice1": p.gift_sales_price,
            }

            product_payload = clean_payload(product_payload)
            batch_payload.append(product_payload)

            if len(batch_payload) >= BATCH_SIZE:
                _upsert_special_offer_batch(batch_payload, processing_date)
                batch_payload.clear()

        if batch_payload:
            _upsert_special_offer_batch(batch_payload, processing_date)

    except Exception:
        AeraLog.error(
            f"Product special offer update on marketplace failed: {traceback.format_exc()}"
        )


def _upsert_product_batch(payload_list, ids, processing_date):
    url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Offers/PartialImports"

    payload = {"Data": {"CreateOfferImportDataList": {"Items": payload_list}}}

    params = {
        "ProcessingDate": processing_date,
        "Currency": "EUR",
        "ValidateOnly": True,
    }
    session_id = get_aera_session_id()
    headers = {
        "Ao-SessionId": session_id,
        "Accept": "application/json",
    }
    response = requests.post(url, json=payload, headers=headers, params=params)
    if not response.ok:
        raise Exception(
            f"Product price update failed, {response.status_code}: {response.text}"
        )

    response.raise_for_status()

    AeraExport.objects.filter(id__in=ids).update(last_pushed_to_aera=timezone.now())


def _upsert_special_offer_batch(payload_list, processing_date):
    url = (
        f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/SpecialOffers/PartialImports"
    )

    payload = {"Data": {"CreateSpecialOfferImportDataList": {"Items": payload_list}}}

    params = {
        "ProcessingDate": processing_date,
        "Currency": "EUR",
        "ValidateOnly": True,
    }

    headers = {
        "Ao-SessionId": get_aera_session_id(),
        "Accept": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, params=params)
    if not response.ok:
        raise Exception(
            f"Product gift price update failed, {response.status_code}: {response.text}"
        )

    response.raise_for_status()


def fetch_aera_orders(test_mode=False):
    url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Orders"
    orders = []

    session_id = get_aera_session_id()
    headers = {
        "Ao-SessionId": session_id,
        "Accept": "application/json",
    }
    params = {
        "SortKey": "OrderDateDsc",
        "TestMode": test_mode,
        "PageSize": 100,
        "page": 1,
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        AeraLog.error(f"Failed to fetch orders: {response.text}")
        response.raise_for_status()

    try:
        data = response.json()
        orders = data["Data"]["OrderList"]["Items"]
        tokens = [o["OrderToken"] for o in orders]
        existing = {
            o.order_token: o for o in AeraOrder.objects.filter(order_token__in=tokens)
        }
        new_orders = []
        updated_orders = []

        for item in orders:
            token = item["OrderToken"]
            if token in existing:
                o = existing[token]
                o.order_number = item["OrderNumber"]
                o.buyer_name = item["BuyerCompanyDisplayName"]
                o.date_transfer_released = make_time_zone_aware(
                    item["DateTransferReleased"]
                )
                o.fetched_at = timezone.now()
                updated_orders.append(o)
            else:
                new_orders.append(
                    AeraOrder(
                        order_token=token,
                        order_number=item["OrderNumber"],
                        buyer_name=item["BuyerCompanyDisplayName"],
                        date_transfer_released=make_time_zone_aware(
                            item["DateTransferReleased"]
                        ),
                        fetched_at=timezone.now(),
                    )
                )

        with transaction.atomic():
            if updated_orders:
                AeraOrder.objects.bulk_update(
                    updated_orders,
                    [
                        "order_number",
                        "buyer_name",
                        "date_transfer_released",
                        "fetched_at",
                    ],
                )

            if new_orders:
                AeraOrder.objects.bulk_create(new_orders)

    except Exception:
        AeraLog.error(f"Failed to fetch orders: {traceback.format_exc()}")
        raise

    return True, orders


def fetch_order_detail(order_token):
    try:
        url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Orders/{order_token}"
        session_id = get_aera_session_id()
        headers = {
            "Ao-SessionId": session_id,
            "Accept": "application/json",
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            AeraLog.error(
                f"Failed to fetch order detail for {order_token}: {response.text}"
            )
            response.raise_for_status()

        detail = response.json()["Data"]["OrderForView"]
        billing = detail.get("BillingAddress", {})
        delivery = detail.get("DeliveryAddress", {})
        items = detail.get("OrderItemList", {}).get("Items", [])
        return detail
        order = AeraOrder.objects.get(order_token=order_token)

        order.billing_name1 = billing.get("Name1")
        order.billing_name2 = billing.get("Name2")
        order.billing_line1 = billing.get("Line1")
        order.billing_line2 = billing.get("Line2")
        order.billing_city = billing.get("City")
        order.billing_postcode = billing.get("PostCode")
        order.billing_country_code = billing.get("CountryIsoCode2")
        order.billing_email = billing.get("Email")
        order.billing_phone = billing.get("Phone1")
        order.billing_vat_number = billing.get("VatRegistrationNumber")

        order.delivery_name1 = delivery.get("Name1")
        order.delivery_name2 = delivery.get("Name2")
        order.delivery_line1 = delivery.get("Line1")
        order.delivery_line2 = delivery.get("Line2")
        order.delivery_city = delivery.get("City")
        order.delivery_postcode = delivery.get("PostCode")
        order.delivery_country_code = delivery.get("CountryIsoCode2")
        order.delivery_email = delivery.get("Email")
        order.delivery_phone = delivery.get("Phone1")
        order.delivery_vat_number = delivery.get("VatRegistrationNumber")

        order.company_vat_number = detail.get("BuyerCompanyVatRegistrationNumber")
        order.currency = detail.get("Currency")
        order.gross_amount = detail.get("GrossAmount")
        order.net_amount = detail.get("NetAmount")
        order.postage = detail.get("Postage")
        order.payment_method_id = detail.get("PaymentMethodId")
        order.order_type_id = detail.get("OrderTypeId")
        order.fetched_at = timezone.now()

        with transaction.atomic():
            order.save()
            AeraOrderItem.objects.filter(order=order).delete()
            bulk_items = [
                AeraOrderItem(
                    order=order,
                    sku=i.get("SKU"),
                    product_name=i.get("ProductName"),
                    product_id=i.get("ProductId"),
                    index_id=i.get("IndexId"),
                    order_quantity=i.get("OrderQuantity"),
                    unit_price=i.get("UnitPrice"),
                    total_price=i.get("TotalPrice"),
                    discount_rate=i.get("DiscountRate"),
                    discount_amount=i.get("DiscountAmount"),
                    vat_type_id=i.get("VatTypeId"),
                    remark=i.get("Remark"),
                )
                for i in items
            ]
            if bulk_items:
                AeraOrderItem.objects.bulk_create(bulk_items)
        return True

    except Exception:
        AeraLog.error(f"Error fetching order {order_token}: {traceback.format_exc()}")


def fetch_and_save_aera_orders():
    success, orders = fetch_aera_orders()

    for order in orders:
        fetch_order_detail(order["OrderToken"])

    AeraLog.info(f"Fetched and saved {len(orders)} orders")
    return success


def index(request):
    clear_aera_session()
    # data = fetch_and_save_aera_orders()
    data = fetch_order_detail("b86495b1-0908-491d-9f11-292984060a48")
    # data = fetch_aera_orders()
    # data = fetch_aera_products()
    # data = push_products_to_aera()
    # data = push_products_to_aera_full_import()
    # return HttpResponse(data)
    return JsonResponse(data, safe=False)


### Full Product imports, should only run ocassionally and carefully


def push_products_to_aera_full_import(sku=None):
    BATCH_SIZE = 300000
    batch_payload = []
    batch_ids = []
    total_synced = 0
    processing_date = date.today().isoformat()

    try:
        product_exports = (
            AeraExport.objects.filter(sku=sku) if sku else AeraExport.objects.all()
        )

        for p in product_exports.iterator(chunk_size=BATCH_SIZE):

            product_payload = {
                "SKU": p.sku,
                "Manufacturer": p.manufacturer,
                "MPN": p.mpn,
                "OfferTypeId": p.offer_type_id,
                "GTIN": p.gtin,
                "ProductName": p.product_name,
                "AvailabilityTypeId": p.availability_type_id,
                "DifferentDeliveryTime": p.different_delivery_time,
                "Discountable": True,
                "Refundable": True,
                "LowerBound1": 1,
                "NetPrice1": p.sales_price,
                "ShippedTemperatureStable": p.shipped_temperature_stable,
            }

            product_payload = clean_payload(product_payload)

            batch_payload.append(product_payload)
            batch_ids.append(p.id)

            if len(batch_payload) >= BATCH_SIZE:
                _upsert_product_batch_full(batch_payload, batch_ids, processing_date)
                total_synced += len(batch_payload)
                batch_payload.clear()
                batch_ids.clear()

        if batch_payload:
            _upsert_product_batch_full(batch_payload, batch_ids, processing_date)
            total_synced += len(batch_payload)

        push_special_offers_to_aera(sku=sku)

        AeraLog.info(
            f"FULL product import completed. Total products imported to Aera: {total_synced}"
        )

    except Exception as e:
        AeraLog.error(
            f"FULL product import failed after importing {total_synced} products: {traceback.format_exc()}"
        )


def _upsert_product_batch_full(payload_list, ids, processing_date):
    url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Offers/FullImports"

    payload = {"Data": {"CreateOfferImportDataList": {"Items": payload_list}}}

    params = {
        "ProcessingDate": processing_date,
        "Currency": "EUR",
        "ClearSpecialOffer": True,
        "ValidateOnly": True,
    }

    headers = {
        "Ao-SessionId": get_aera_session_id(),
        "Accept": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, params=params)
    if not response.ok:
        raise Exception(
            f"Product full import update failed, {response.status_code}: {response.text}"
        )

    response.raise_for_status()

    AeraExport.objects.filter(id__in=ids).update(last_pushed_to_aera=timezone.now())

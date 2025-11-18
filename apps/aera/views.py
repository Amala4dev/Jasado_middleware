from django.conf import settings
import requests
from datetime import date
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

import time
from django.http import JsonResponse, HttpResponse
from .models import (
    AeraSession,
    AeraProduct,
    AeraProductUpdate,
    AeraCompetitorPrice,
    AeraOrder,
    AeraOrderItem,
)
from .utils import (
    AeraLog,
)
from utils import make_time_zone_aware
from apps.core.models import (
    TaskStatus,
    DynamicPrice,
    AdditionalMasterData,
    BlockedProduct,
)
from apps.gls.models import (
    GLSMasterData,
    GLSStockLevel,
)

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
    for p in items:
        objs.append(
            AeraProduct(
                sku=p["SKU"],
                aera_product_id=p.get("ProductId"),
                manufacturer=p.get("Manufacturer"),
                mpn=p.get("MPN"),
                offer_type_id=p.get("OfferTypeId"),
                discontinuation=p.get("Discontinuation"),
                discontinuation_date=p.get("DiscontinuationDate"),
                availability_type_id=p.get("AvailabilityTypeId"),
                different_delivery_time=p.get("DifferentDeliveryTime"),
                discountable=p.get("Discountable"),
                refundable=p.get("Refundable"),
                lower_bound_1=p.get("LowerBound1"),
                net_price_1=p.get("NetPrice1"),
                lower_bound_2=p.get("LowerBound2"),
                net_price_2=p.get("NetPrice2"),
                lower_bound_3=p.get("LowerBound3"),
                net_price_3=p.get("NetPrice3"),
                lower_bound_4=p.get("LowerBound4"),
                net_price_4=p.get("NetPrice4"),
                lower_bound_5=p.get("LowerBound5"),
                net_price_5=p.get("NetPrice5"),
                special_offer_valid_through=p.get("SpecialOfferValidThrough"),
                special_offer_discountable=p.get("SpecialOfferDiscountable"),
                special_offer_lower_bound_1=p.get("SpecialOfferLowerBound1"),
                special_offer_net_price_1=p.get("SpecialOfferNetPrice1"),
                special_offer_lower_bound_2=p.get("SpecialOfferLowerBound2"),
                special_offer_net_price_2=p.get("SpecialOfferNetPrice2"),
                special_offer_lower_bound_3=p.get("SpecialOfferLowerBound3"),
                special_offer_net_price_3=p.get("SpecialOfferNetPrice3"),
                special_offer_lower_bound_4=p.get("SpecialOfferLowerBound4"),
                special_offer_net_price_4=p.get("SpecialOfferNetPrice4"),
                special_offer_lower_bound_5=p.get("SpecialOfferLowerBound5"),
                special_offer_net_price_5=p.get("SpecialOfferNetPrice5"),
                shipped_temperature_stable=p.get("ShippedTemperatureStable"),
            )
        )

    with transaction.atomic():
        AeraProduct.objects.all().delete()
        AeraProduct.objects.bulk_create(objs, batch_size=5000)


def fetch_aera_competitor_prices(sku=None):
    # should_run = TaskStatus.should_run(TaskStatus.FETCH_PRICES_AERA)
    should_run = 1
    if not should_run:
        return False

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

    TaskStatus.set_success(TaskStatus.FETCH_PRICES_AERA)
    return True


@transaction.atomic
def _prepare_aera_data():
    all_ok = True

    try:
        blocked_articles = set(
            BlockedProduct.objects.values_list("article_no", flat=True)
        )
        stock_map = {s.article_no: s.inventory for s in GLSStockLevel.objects.all()}
        calculated_price = {
            s.article_no: s.calculated_sales_price for s in DynamicPrice.objects.all()
        }
        now = timezone.now()

        instances = []

        # --- GLS Master Data ---
        master_data = GLSMasterData.objects.exclude(article_no__in=blocked_articles)
        for data in master_data:
            stock = stock_map.get(data.article_no, Decimal("0"))
            offer_type_id = 1
            availability_type_id = 1 if stock > 0 else 2
            different_delivery_time = 3 if stock > 0 else 14
            shipped_temperature_stable = not data.store_refrigerated

            instances.append(
                AeraProductUpdate(
                    sku=data.article_no,
                    product_name=data.description,
                    manufacturer=data.manufacturer_name,
                    mpn=data.manufacturer_article_no,
                    gtin=data.pzn_no,
                    offer_type_id=offer_type_id,
                    availability_type_id=availability_type_id,
                    different_delivery_time=different_delivery_time,
                    shipped_temperature_stable=shipped_temperature_stable,
                    calculated_sales_price=calculated_price[data.article_no],
                    updated_at=now,
                )
            )

        # --- Additional Products ---
        additional_products = AdditionalMasterData.objects.exclude(
            article_no__in=blocked_articles
        )
        for data in additional_products:
            stock = stock_map.get(data.article_no, Decimal("0"))
            offer_type_id = 1
            availability_type_id = 1 if stock > 0 else 2
            different_delivery_time = 3 if stock > 0 else 14

            instances.append(
                AeraProductUpdate(
                    sku=data.article_no,
                    product_name=data.name,
                    manufacturer=data.manufacturer,
                    mpn=data.manufacturer_article_no,
                    gtin=data.gtin,
                    offer_type_id=offer_type_id,
                    availability_type_id=availability_type_id,
                    different_delivery_time=different_delivery_time,
                    shipped_temperature_stable=True,
                    calculated_sales_price=calculated_price[data.article_no],
                    updated_at=now,
                )
            )

        AeraProductUpdate.objects.all().delete()
        AeraProductUpdate.objects.bulk_create(instances, batch_size=500)

        AeraLog.info("Data for transfer prepared successfully")
    except Exception as e:
        all_ok = False
        AeraLog.error(f"Failed to prepare data for transfer: {str(e)}")

    if all_ok:
        TaskStatus.set_success(TaskStatus.PREPARE_DATA_AERA)
    else:
        TaskStatus.set_failure(TaskStatus.PREPARE_DATA_AERA)

    return all_ok


def push_aera_data(sku=None):
    should_run = TaskStatus.should_run(TaskStatus.DATA_TRANSFER_AERA)
    aera_data_prepared = _prepare_aera_data()
    if not (should_run and aera_data_prepared):
        return

    url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Offers/PartialImports"

    products = (
        AeraProductUpdate.objects.filter(sku__in=sku)
        if sku
        else AeraProductUpdate.objects.all()
    )
    valid_products = [
        p for p in products if p.calculated_sales_price and p.calculated_sales_price > 0
    ]

    payload = {
        "Data": {
            "CreateOfferImportDataList": {
                "Items": [
                    {
                        "SKU": p.sku,
                        "Manufacturer": p.manufacturer,
                        "MPN": p.mpn,
                        "OfferTypeId": p.offer_type_id,
                        "GTIN": p.gtin,
                        "ProductName": p.product_name,
                        "AvailabilityTypeId": p.availability_type_id,
                        "DifferentDeliveryTime": p.different_delivery_time,
                        "LowerBound1": 1,
                        "NetPrice1": p.calculated_sales_price,
                        "ShippedTemperatureStable": p.shipped_temperature_stable,
                    }
                    for p in valid_products
                ]
            }
        }
    }

    params = {
        "ProcessingDate": date.today().isoformat(),
        "Currency": "EUR",
        "ValidateOnly": True,
    }
    session_id = get_aera_session_id()
    headers = {
        "Ao-SessionId": session_id,
        "Accept": "application/json",
    }
    response = requests.post(url, json=payload, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        AeraLog.info("Product data updated successfully")
        TaskStatus.set_success(TaskStatus.DATA_TRANSFER_AERA)
        return data

    AeraLog.error(f"Product data update failed: {response.text}")
    response.raise_for_status()


# def update_sales_prices(sku=None):
#     # should_run = TaskStatus.should_run(TaskStatus.UPDATE_PRICES_AERA)
#     should_run = 1
#     if not should_run:
#         return

#     url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Offers/PartialImports"

#     products = Product.objects.filter(sku__in=sku) if sku else Product.objects.all()
#     valid_products = [p for p in products if p.calculated_price and p.calculated_price > 0]

#     payload = {
#         "Data": {
#             "CreateOfferImportDataList": {
#                 "Items": [
#                     {
#                         "SKU": p.sku,
#                         "OfferTypeId": 1,
#                         "LowerBound1": 1,
#                         "NetPrice1": p.calculated_price,
#                     }
#                     for p in valid_products
#                 ]
#             }
#         }
#     }

#     params = {
#         "ProcessingDate": date.today().isoformat(),
#         "Currency": "EUR",
#         "ValidateOnly": True,
#     }
#     session_id = get_aera_session_id()
#     headers = {
#         "Ao-SessionId": session_id,
#         "Accept": "application/json",
#     }
#     response = requests.post(url, json=payload, headers=headers, params=params)
#     if response.status_code == 200:
#         data = response.json()
#         AeraLog.info("Updated sales prices successfully")
#         TaskStatus.set_success(TaskStatus.UPDATE_PRICES_AERA)
#         return data

#     AeraLog.error(f"sales price update failed: {response.text}")
#     response.raise_for_status()


def fetch_aera_orders(test_mode=False):
    # should_run = TaskStatus.should_run(TaskStatus.FETCH_ORDERS_AERA)
    should_run = 1
    if not should_run:
        return False

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
                o.seller_name = item["SellerCompanyDisplayName"]
                o.date_transfer_confirmed = make_time_zone_aware(
                    item["DateTransferConfirmed"]
                )
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
                        seller_name=item["SellerCompanyDisplayName"],
                        date_transfer_confirmed=make_time_zone_aware(
                            item["DateTransferConfirmed"]
                        ),
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
                        "seller_name",
                        "date_transfer_confirmed",
                        "date_transfer_released",
                        "fetched_at",
                    ],
                )

            if new_orders:
                AeraOrder.objects.bulk_create(new_orders)

        TaskStatus.set_success(TaskStatus.FETCH_ORDERS_AERA)

    except Exception as e:
        AeraLog.error(f"Failed to fetch orders: {str(e)}")
        raise

    AeraLog.info(f"Fetched {len(orders)} orders successfully")
    return True, orders


# def fetch_orderss(test_mode=True):
#     url = f"{AERA_BASE_URL}/Roles/Sellers/{AERA_COMPANY_ID}/Orders"
#     page = 1
#     all_orders = []

#     while True:
#         time.sleep(0.2)
#         session_id = get_aera_session_id()
#         headers = {
#             "Ao-SessionId": session_id,
#             "Accept": "application/json",
#         }
#         params = {
#             "page": page,
#             "SortKey": "OrderDateDsc",
#             "TestMode": test_mode,
#         }

#         response = requests.get(url, headers=headers, params=params)
#         if response.status_code != 200:
#             AeraLog.error(f"Failed to fetch orders: {response.text}")
#             response.raise_for_status()

#         try:
#             data = response.json()
#             orders = data["Data"]["OrderList"]["Items"]
#             print(f"order page {page}")
#             print(orders)
#             if not orders:
#                 break

#             tokens = [o["OrderToken"] for o in orders]
#             existing = {
#                 o.order_token: o
#                 for o in AeraOrder.objects.filter(order_token__in=tokens)
#             }
#             new_orders = []
#             updated_orders = []

#             for item in orders:
#                 token = item["OrderToken"]
#                 if token in existing:
#                     o = existing[token]
#                     o.order_number = item["OrderNumber"]
#                     o.buyer_name = item["BuyerCompanyDisplayName"]
#                     o.seller_name = item["SellerCompanyDisplayName"]
#                     o.date_transfer_confirmed = make_time_zone_aware(
#                         item["DateTransferConfirmed"]
#                     )
#                     o.date_transfer_released = make_time_zone_aware(
#                         item["DateTransferReleased"]
#                     )
#                     o.fetched_at = timezone.now()
#                     updated_orders.append(o)
#                 else:
#                     new_orders.append(
#                         AeraOrder(
#                             order_token=token,
#                             order_number=item["OrderNumber"],
#                             buyer_name=item["BuyerCompanyDisplayName"],
#                             seller_name=item["SellerCompanyDisplayName"],
#                             date_transfer_confirmed=make_time_zone_aware(
#                                 item["DateTransferConfirmed"]
#                             ),
#                             date_transfer_released=make_time_zone_aware(
#                                 item["DateTransferReleased"]
#                             ),
#                             fetched_at=timezone.now(),
#                         )
#                     )

#             with transaction.atomic():
#                 if updated_orders:
#                     AeraOrder.objects.bulk_update(
#                         updated_orders,
#                         [
#                             "order_number",
#                             "buyer_name",
#                             "seller_name",
#                             "date_transfer_confirmed",
#                             "date_transfer_released",
#                             "fetched_at",
#                         ],
#                     )

#                 if new_orders:
#                     AeraOrder.objects.bulk_create(new_orders)

#             all_orders.extend(orders)
#             page += 1
#         except Exception as e:
#             AeraLog.error(f"Failed to fetch orders: {str(e)}")
#             raise

#     AeraLog.info(f"Fetched {len(all_orders)} orders successfully")
#     return all_orders


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

        order.currency = detail.get("Currency")
        order.gross_amount = detail.get("GrossAmount")
        order.net_amount = detail.get("NetAmount")
        order.vat_amount_full = detail.get("VatAmountFull")
        order.vat_amount_half = detail.get("VatAmountHalf")
        order.vat_rate_full = detail.get("VatRateFull")
        order.vat_rate_half = detail.get("VatRateHalf")
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
                    order_quantity=i.get("OrderQuantity"),
                    total_quantity=i.get("TotalQuantity"),
                    unit_price=i.get("UnitPrice"),
                    total_price=i.get("TotalPrice"),
                    total_value_of_goods=i.get("TotalValueOfGoods"),
                    unit_of_measure=i.get("UnitOfMeasure"),
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

    except Exception as e:
        AeraLog.error(f"Error fetching order {order_token}: {str(e)}")
        raise


def fetch_and_save_aera_orders():
    success, orders = fetch_aera_orders()

    for order in orders:
        fetch_order_detail(order["OrderToken"])

    AeraLog.info(f"Fetched and saved {len(orders)} orders with details")
    return success


def index(request):
    # data = fetch_and_save_aera_orders()
    data = fetch_and_save_aera_orders()
    # return HttpResponse(data)
    return JsonResponse(data, safe=False)

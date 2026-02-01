from utils import (
    to_unix_ms,
    make_json_safe,
    remove_null_keys,
)
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from apps.core.models import (
    Product,
    ProductGtin,
    LogEntry,
)
from apps.gls.models import (
    GLSPromotionHeader,
    GLSHandlingSurcharge,
)
from decimal import Decimal
from .models import SyncStatus


class WeclappLog:
    @staticmethod
    def info(msg):
        LogEntry.objects.create(
            source=LogEntry.WECLAPP, level=LogEntry.INFO, message=msg
        )

    @staticmethod
    def warning(msg):
        LogEntry.objects.create(
            source=LogEntry.WECLAPP, level=LogEntry.WARNING, message=msg
        )

    @staticmethod
    def error(msg):
        LogEntry.objects.create(
            source=LogEntry.WECLAPP, level=LogEntry.ERROR, message=msg
        )

    @staticmethod
    async def ainfo(msg):
        await sync_to_async(WeclappLog.info)(msg)

    @staticmethod
    async def awarning(msg):
        await sync_to_async(WeclappLog.warning)(msg)

    @staticmethod
    async def aerror(msg):
        await sync_to_async(WeclappLog.error)(msg)


class AsyncDb:

    @staticmethod
    def _fetch_gls_products(limit=False):
        products = Product.objects.filter(
            supplier=Product.SUPPLIER_GLS,
            is_blocked=False,
            weclapp_id__isnull=False,
        )
        if limit:
            products = products[:2]
        return products

    @staticmethod
    def _fetch_gls_product_ids(limit=False):
        qs = Product.objects.filter(
            supplier=Product.SUPPLIER_GLS, is_blocked=False, sku="LG18767"
        ).values_list("id", flat=True)
        if limit:
            qs = qs[:200000]
        return list(qs)

    @staticmethod
    def _fetch_product_by_sku(sku):
        return Product.objects.get(sku=sku)

    @staticmethod
    def _fetch_products_by_ids(ids):
        return list(Product.objects.filter(id__in=ids))

    @staticmethod
    def _fetch_gtin_map():
        return dict(ProductGtin.objects.all().values_list("article_no", "gtin"))

    @staticmethod
    def _fetch_master_data(product):
        return product.gls_master_data.first()

    @staticmethod
    def _fetch_price_list(product):
        return product.gls_price_list.first()

    @staticmethod
    def _fetch_promotional_price(product):
        return product.gls_promotional_price.first()

    @staticmethod
    def _fetch_gls_handling_surcharge():
        surcharge_map = {}
        for obj in GLSHandlingSurcharge.objects.only(
            "article_group_no", "value", "fee_type"
        ):
            surcharge_map[obj.article_group_no] = obj.normalised_value
        return surcharge_map

    @staticmethod
    def _fetch_promo_header(action_code):
        return GLSPromotionHeader.objects.filter(action_code=action_code).first()

    @staticmethod
    def _get_instance_property(obj, property_name):
        return getattr(obj, property_name)

    @staticmethod
    def _get_is_sync_ongoing():
        return SyncStatus.is_ongoing()

    @staticmethod
    def _set_sync_ongoing():
        SyncStatus.set_ongoing()

    @staticmethod
    def _set_sync_completed():
        SyncStatus.set_completed()

    # ---- async wrappers ----

    get_product_by_sku = staticmethod(sync_to_async(_fetch_product_by_sku))
    get_products_by_ids = staticmethod(sync_to_async(_fetch_products_by_ids))
    get_gtin_map = staticmethod(sync_to_async(_fetch_gtin_map))
    get_master_data = staticmethod(sync_to_async(_fetch_master_data))
    get_price_list = staticmethod(sync_to_async(_fetch_price_list))
    get_promotional_price = staticmethod(sync_to_async(_fetch_promotional_price))
    get_promo_header = staticmethod(sync_to_async(_fetch_promo_header))
    get_gls_handling_surcharge = staticmethod(
        sync_to_async(_fetch_gls_handling_surcharge)
    )
    get_model_property = staticmethod(sync_to_async(_get_instance_property))
    get_gls_products = staticmethod(sync_to_async(_fetch_gls_products))
    get_gls_product_ids = staticmethod(sync_to_async(_fetch_gls_product_ids))
    is_sync_ongoing = staticmethod(sync_to_async(_get_is_sync_ongoing))
    set_sync_ongoing = staticmethod(sync_to_async(_set_sync_ongoing))
    set_sync_completed = staticmethod(sync_to_async(_set_sync_completed))


def vat_rate_type(rate):
    return "STANDARD" if rate == 19 else "REDUCED" if rate == 7 else None


def upsert_custom_attribute(attrs, attr_id, **values):
    for a in attrs:
        if a.get("attributeDefinitionId") == attr_id:
            a.update(values)
            return attrs

    attrs.append(
        {
            "attributeDefinitionId": attr_id,
            **values,
        }
    )
    return attrs


def upsert_rrp(prices, price):
    for p in prices:
        if p.get("articleCalculationPriceType") == "RECOMMENDED_RETAIL_PRICE":
            p["price"] = str(price)
            return prices

    prices.append(
        {
            "articleCalculationPriceType": "RECOMMENDED_RETAIL_PRICE",
            "price": str(price),
        }
    )
    return prices


def upsert_sales_price(prices, channel, price, start=None, end=None):
    for p in prices:
        if p.get("salesChannel") == channel:
            p.update(
                {
                    "price": str(price),
                    "startDate": to_unix_ms(start) if start else None,
                    "endDate": to_unix_ms(end) if end else None,
                }
            )
            return prices

    prices.append(
        {
            "salesChannel": channel,
            "price": str(price),
            "startDate": to_unix_ms(start) if start else None,
            "endDate": to_unix_ms(end) if end else None,
        }
    )
    return prices


def upsert_promo_purchase_price(prices, price, min_qty, start=None, end=None):
    for p in prices:
        p.update(
            {
                "price": str(price),
                "priceScaleValue": str(min_qty),
                "startDate": to_unix_ms(start) if start else None,
                "endDate": to_unix_ms(end) if end else None,
            }
        )
        return prices

    prices.append(
        {
            "price": str(price),
            "priceScaleValue": str(min_qty),
            "startDate": to_unix_ms(start) if start else None,
            "endDate": to_unix_ms(end) if end else None,
        }
    )
    return prices


def strip_system_fields(data):
    REMOVE = {
        "createdDate",
        "lastModifiedDate",
        "lastModifiedByUserId",
        "lowLevelCode",
        "recordItemGroupName",
        "systemCode",
        # from shipment fields
        "creatorId",
        "statusHistory",
        "picksComplete",
        "purchaseOrders",
        "recipientCustomerNumber",
        "recipientSupplierNumber",
        "confirmedByUserId",
        "confirmedDate",
        "bookedDate",
        "sourceInternalTransportReferenceId",
        "sourceStoragePlaceId",
        "transportationOrderId",
    }

    if isinstance(data, dict):
        return {k: strip_system_fields(v) for k, v in data.items() if k not in REMOVE}

    if isinstance(data, list):
        return [strip_system_fields(i) for i in data]

    return data


def weclapp_clean_payload(payload):
    # payload = remove_null_keys(payload)
    payload = strip_system_fields(payload)
    payload = make_json_safe(payload)
    return payload


def parse_gls_expiry_date(value):
    if not value:
        return None
    try:
        date = datetime.strptime(value, "%d.%m.%Y")
        return to_unix_ms(date)
    except ValueError:
        return None


def parse_gls_shipping_date(value):
    if not value:
        return None
    try:
        date = datetime.strptime(value, "%Y-%m-%d")
        return to_unix_ms(date)
    except ValueError:
        return None


def get_gls_delivery_date(value):
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%d") + timedelta(days=2)
        return to_unix_ms(dt)
    except ValueError:
        return None

from django.db import transaction
import traceback

from .utils import CoreLog
from .models import (
    Product,
    AdditionalMasterData,
    ProductGtin,
)
from apps.aera.models import (
    AeraExport,
    AeraProduct,
)
from apps.wawibox.models import (
    WawiboxExport,
    WawiboxProduct,
)
from apps.dentalheld.models import (
    # DentalheldProduct,
    DentalheldExport,
)
from apps.shopware.models import (
    ShopwareProduct,
    ShopwareExport,
)
from apps.gls.models import (
    GLSStockLevel,
    GLSSupplier,
    GLSMasterData,
)


def get_delivery_time(stock):
    return 3 if stock > 0 else 14


def get_gls_stock():
    stock_map = {
        article_no: float(inventory or 0)
        for article_no, inventory in GLSStockLevel.objects.values_list(
            "article_no", "inventory"
        )
    }

    return stock_map


def get_non_gls_stock():
    stock_map = {
        article_no: float(stock or 0)
        for article_no, stock in AdditionalMasterData.objects.values_list(
            "article_no", "stock"
        )
    }

    return stock_map


def get_manufacturer_map():
    manufacturer_map = {
        supplier_no: name1
        for supplier_no, name1 in GLSSupplier.objects.values_list(
            "supplier_no", "name1"
        )
    }
    return manufacturer_map


def get_gtin_map():
    gtin_map = {
        article_no: gtin
        for article_no, gtin in ProductGtin.objects.values_list("article_no", "gtin")
    }
    return gtin_map


def get_vat_rate_map():
    vat_rate_map = {
        article_no: vat_rate
        for article_no, vat_rate in GLSMasterData.objects.values_list(
            "article_no", "vat_rate"
        )
    }
    return vat_rate_map


def build_aera_export(
    product,
    gls_stock_map,
    non_gls_stock_map,
    manufacturer_map,
    gtin_map,
):
    supplier_article_no = product.supplier_article_no

    if product.supplier == Product.SUPPLIER_GLS:
        stock = gls_stock_map.get(supplier_article_no, 0)
        manufacturer_name = manufacturer_map.get(product.manufacturer_id)
    else:
        stock = non_gls_stock_map.get(supplier_article_no, 0)
        manufacturer_name = product.manufacturer

    availability_type_id = 1 if stock > 0 else 2

    export = AeraExport(
        sku=product.sku,
        product_name=product.name,
        manufacturer=manufacturer_name,
        mpn=product.manufacturer_article_no,
        offer_type_id=1,
        gtin=gtin_map.get(supplier_article_no),
        availability_type_id=availability_type_id,
        different_delivery_time=get_delivery_time(stock),
        shipped_temperature_stable=product.store_refrigerated,
        sales_price=product.aera_sales_price,
        gift_sales_price=product.aera_gift_sales_price,
        gift_min_qty=product.gift_min_qty,
        gift_valid_until=product.gift_valid_until,
    )

    return export


def build_shopware_export(
    product,
    gls_stock_map,
    non_gls_stock_map,
    manufacturer_map,
    gtin_map,
    vat_rate_map,
):
    shopware_id = product.shopware_product.shopware_id
    master_data = product.gls_master_data.first()

    if not shopware_id:
        return None

    supplier_article_no = product.supplier_article_no
    if product.supplier == Product.SUPPLIER_GLS:
        stock = gls_stock_map.get(supplier_article_no, 0)
        vat_rate = vat_rate_map.get(supplier_article_no)
        manufacturer_name = manufacturer_map.get(product.manufacturer_id)
    else:
        stock = non_gls_stock_map.get(supplier_article_no, 0)
        vat_rate = None
        manufacturer_name = product.manufacturer

    export = ShopwareExport(
        shopware_id=shopware_id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        sales_price=product.aera_sales_price,
        gift_sales_price=product.aera_gift_sales_price,
        gift_min_qty=product.gift_min_qty,
        gift_paid_qty=product.gift_paid_qty,
        gift_free_qty=product.gift_free_qty,
        gift_valid_from=product.gift_valid_from,
        gift_valid_until=product.gift_valid_until,
        manufacturer=manufacturer_name,
        mpn=product.manufacturer_article_no,
        gtin=gtin_map.get(supplier_article_no),
        shipped_temperature_stable=product.store_refrigerated,
        length=master_data.length,
        width=master_data.width,
        height=master_data.height,
        weight=master_data.weight,
        stock=stock,
        tax_rate=vat_rate,
    )

    return export


def build_wawibox_export(product, gls_stock_map, non_gls_stock_map, vat_rate_map):
    vat_map = {
        0: 2,
        7: 1,
        19: 0,
    }

    supplier_article_no = product.supplier_article_no
    if product.supplier == Product.SUPPLIER_GLS:
        stock = gls_stock_map.get(supplier_article_no, 0)
        vat_rate = int(float(vat_rate_map.get(supplier_article_no)))
    else:
        stock = non_gls_stock_map.get(supplier_article_no, 0)
        vat_rate = None

    export = WawiboxExport(
        internal_number=product.sku,
        name=product.name,
        manufacturer_article_no=product.manufacturer_article_no,
        order_number=f"{product.sku}-BASE",
        sales_price=product.wawibox_sales_price,
        order_number_2=f"{product.sku}-GIFT",
        min_order_quantity_2=product.gift_min_qty,
        price_2=product.wawibox_gift_sales_price,
        valid_from=product.gift_valid_from,
        valid_until=product.gift_valid_until,
        vat_category=vat_map.get(vat_rate, 0),
        delivery_time=get_delivery_time(stock),
        is_available=stock > 0,
    )
    return export


def build_dentalheld_export(
    product,
    gls_stock_map,
    non_gls_stock_map,
    manufacturer_map,
    gtin_map,
):

    supplier_article_no = product.supplier_article_no
    if product.supplier == Product.SUPPLIER_GLS:
        stock = gls_stock_map.get(supplier_article_no, 0)
        manufacturer_name = manufacturer_map.get(product.manufacturer_id)
    else:
        stock = non_gls_stock_map.get(supplier_article_no, 0)
        manufacturer_name = product.manufacturer

    export = DentalheldExport(
        article_id=product.sku,
        ean=gtin_map.get(supplier_article_no),
        name=product.name,
        net_price=product.aera_sales_price,
        manufacturer_name=manufacturer_name,
        manufacturer_article_number=product.manufacturer_article_no,
        delivery_status=2 if stock > 0 else 1,
        delivery_time_days=get_delivery_time(stock),
        stock_level=stock,
        tier_qty_1=product.gift_min_qty,
        tier_price_1=product.aera_gift_sales_price,
    )

    return export


def build_product_exports():
    try:
        aera = []
        wawi = []
        dentalheld = []
        shopware = []

        products = Product.objects.filter(is_blocked=False)
        aera_skus = set(AeraProduct.objects.values_list("sku", flat=True))
        wawibox_skus = set(WawiboxProduct.objects.values_list("sku", flat=True))
        # dentalheld_skus = set(DentalheldProduct.objects.values_list("sku", flat=True))
        shopware_skus = set(ShopwareProduct.objects.values_list("sku", flat=True))
        gls_stock_map = get_gls_stock()
        non_gls_stock_map = get_non_gls_stock()
        manufacturer_map = get_manufacturer_map()
        gtin_map = get_gtin_map()
        vat_rate_map = get_vat_rate_map()

        for product in products:
            if product.aera_sales_price and (product.sku in aera_skus):
                aera_export = build_aera_export(
                    product,
                    gls_stock_map,
                    non_gls_stock_map,
                    manufacturer_map,
                    gtin_map,
                )
                if aera_export:
                    aera.append(aera_export)

            if product.wawibox_sales_price and (product.sku in wawibox_skus):
                wawibox_export = build_wawibox_export(
                    product,
                    gls_stock_map,
                    non_gls_stock_map,
                    vat_rate_map,
                )
                if wawibox_export:
                    wawi.append(wawibox_export)

            if product.aera_sales_price and (
                product.sku in wawibox_skus
            ):  # wawibox skus is used here since dentalhed has no means to fetch existing products
                dentalheld_export = build_dentalheld_export(
                    product,
                    gls_stock_map,
                    non_gls_stock_map,
                    manufacturer_map,
                    gtin_map,
                )
                if dentalheld_export:
                    dentalheld.append(dentalheld_export)

            if product.aera_sales_price and (product.sku in shopware_skus):
                shopware_export = build_shopware_export(
                    product,
                    gls_stock_map,
                    non_gls_stock_map,
                    manufacturer_map,
                    gtin_map,
                    vat_rate_map,
                )
                if shopware_export:
                    shopware.append(shopware_export)

        with transaction.atomic():
            AeraExport.objects.all().delete()
            DentalheldExport.objects.all().delete()
            ShopwareExport.objects.all().delete()
            WawiboxExport.objects.all().delete()

            AeraExport.objects.bulk_create(aera, batch_size=5000)
            DentalheldExport.objects.bulk_create(dentalheld, batch_size=5000)
            ShopwareExport.objects.bulk_create(shopware, batch_size=5000)
            WawiboxExport.objects.bulk_create(wawi, batch_size=5000)
            CoreLog.info("Product exports prepared successfully")
        return True
    except Exception:
        CoreLog.error(
            f"Product exports preparation encountered an error: {traceback.format_exc()}"
        )
        return False

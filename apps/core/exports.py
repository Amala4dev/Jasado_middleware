from decimal import Decimal
from django.db import transaction

from .utils import (
    CoreLog,
)
from .models import (
    Product,
    AdditionalMasterData,
)
from apps.aera.models import (
    AeraExport,
    AeraProduct,
)
from apps.wawibox.models import (
    WawiboxExport,
    WawiboxProduct,
)
from apps.gls.models import (
    GLSStockLevel,
)


def get_gls_stock():
    stock_map = {
        article_no: inventory
        for article_no, inventory in GLSStockLevel.objects.values_list(
            "article_no", "inventory"
        )
    }

    return stock_map


def get_non_gls_stock():
    stock_map = {
        article_no: stock
        for article_no, stock in AdditionalMasterData.objects.values_list(
            "article_no", "stock"
        )
    }

    return stock_map


def get_delivery_time(stock):
    return 3 if stock > 0 else 14


def build_aera_export(product, gls_stock_map, non_gls_stock_map):

    if product.supplier == Product.SUPPLIER_GLS:
        gls_article_no = product.supplier_article_no

        stock = gls_stock_map.get(gls_article_no, Decimal("0"))
        availability_type_id = 1 if stock > 0 else 2

        export = AeraExport(
            sku=product.sku,
            product_name=product.name,
            manufacturer=product.manufacturer,
            mpn=product.manufacturer_article_no,
            offer_type_id=1,
            availability_type_id=availability_type_id,
            different_delivery_time=get_delivery_time(stock),
            shipped_temperature_stable=product.store_refrigerated,
            sales_price=product.sales_price,
        )

    else:
        supplier_article_no = product.supplier_article_no

        stock = non_gls_stock_map.get(supplier_article_no, Decimal("0"))
        availability_type_id = 1 if stock > 0 else 2

        export = AeraExport(
            sku=product.sku,
            product_name=product.name,
            manufacturer=product.manufacturer,
            mpn=product.manufacturer_article_no,
            shipped_temperature_stable=product.store_refrigerated,
            gtin=product.gtin,
            sales_price=product.sales_price,
            offer_type_id=1,
            availability_type_id=availability_type_id,
            different_delivery_time=get_delivery_time(stock),
        )

    return export


def build_wawibox_export(product):
    export = WawiboxExport(
        internal_number=product.sku,
        name=product.name,
        manufacturer_article_no=product.manufacturer_article_no,
        sales_price=product.sales_price,
    )
    return export


def build_product_exports():
    try:
        aera = []
        wawi = []
        # dental = []
        # weclapp = []
        # shopware = []

        products = Product.objects.filter(is_blocked=False, sales_price__isnull=False)
        aera_skus = AeraProduct.objects.values_list("sku", flat=True)
        wawibox_skus = set(WawiboxProduct.objects.values_list("sku", flat=True))
        gls_stock_map = get_gls_stock()
        non_gls_stock_map = get_non_gls_stock()

        for product in products:
            if product.sku in aera_skus:
                aera_export = build_aera_export(
                    product, gls_stock_map, non_gls_stock_map
                )
                aera.append(aera_export)

            if product.sku in wawibox_skus:
                wawibox_export = build_wawibox_export(product)
                wawi.append(wawibox_export)

            # dental.append(
            #     DentalheldExport(
            #         product_id=pid,
            #         article_no=p["sku"],
            #         name=p["name"],
            #         ean=p["ean"],
            #         manufacturer=p["manufacturer_name"],
            #         manufacturer_article_no=p["manufacturer_article_no"],
            #         sales_price=sp,
            #         stock=stk,
            #     )
            # )

            # weclapp.append(
            #     WeclappExport(
            #         product_id=pid,
            #         uvp=p.get("uvp", 0),
            #         cogs=cogs,
            #         sales_price=sp,
            #     )
            # )

            # shopware.append(
            #     ShopwareExport(
            #         product_id=pid,
            #         article_no=p["sku"],
            #         name=p["name"],
            #         manufacturer=p["manufacturer_name"],
            #         manufacturer_article_no=p["manufacturer_article_no"],
            #         ean=p["ean"],
            #         sales_price=sp,
            #         temperature_stable_shipping=p["store_refrigerated"],
            #         weight=p["weight"],
            #         length=p["length"],
            #         width=p["width"],
            #         height=p["height"],
            #         stock=stk,
            #         tax_rate=p["tax_rate"],
            #         tracking_number=p["tracking_number"],
            #     )
            # )

        with transaction.atomic():
            AeraExport.objects.all().delete()
            WawiboxExport.objects.all().delete()

            AeraExport.objects.bulk_create(aera, batch_size=5000)
            WawiboxExport.objects.bulk_create(wawi, batch_size=5000)
            CoreLog.info("Product exports prepared successfully")
        return True
    except Exception as e:
        CoreLog.error(f"Product exports preparation encountered an error: {str(e)}")
        return False

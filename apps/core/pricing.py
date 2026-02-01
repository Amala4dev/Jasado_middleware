from datetime import datetime, timedelta
from decimal import Decimal
from django.db import transaction
from collections import defaultdict
import traceback

from .utils import (
    CoreLog,
)
from .models import (
    Product,
    MiddlewareSetting,
    ProductPriceHistory,
    AdditionalMasterData,
)
from apps.aera.models import (
    AeraCompetitorPrice,
)
from apps.wawibox.models import (
    WawiboxCompetitorPrice,
)
from apps.gls.models import (
    GLSPriceList,
    GLSPromotionHeader,
    GLSPromotionPosition,
    GLSPromotionPrice,
    GLSHandlingSurcharge,
)


def get_product_ids_and_groups():
    """
    Return a list of tuples containing (id, gls_article_group_no)
    for all gls products in the database.
    """
    id_article_group_no_list = list(
        Product.objects.filter(
            supplier=Product.SUPPLIER_GLS,
        ).values_list("id", "gls_article_group_no")
    )
    return id_article_group_no_list


def get_non_gls_product_ids():
    """
    Return a list containing id
    for all non gls products in the database.
    """
    id_list = list(
        Product.objects.filter(supplier=Product.SUPPLIER_NON_GLS).values_list(
            "id", flat=True
        )
    )
    return id_list


def fetch_gls_prices():
    gls_price_list = GLSPriceList.objects.values_list("product_id", "bill_back_price")
    price_map = {
        product_id: bill_back_price for product_id, bill_back_price in gls_price_list
    }
    return price_map


def fetch_non_gls_prices():
    price_list = AdditionalMasterData.objects.values_list(
        "product_id", "article_calculation_price"
    )
    price_map = {
        product_id: article_calculation_price
        for product_id, article_calculation_price in price_list
    }
    return price_map


def fetch_gls_handling_surcharge():
    surcharge_map = {}
    for obj in GLSHandlingSurcharge.objects.only(
        "article_group_no", "value", "fee_type"
    ):
        surcharge_map[obj.article_group_no] = obj.normalised_value
    return surcharge_map


def fetch_aera_competitive_prices():
    data = {}
    aera_prices = AeraCompetitorPrice.objects.values_list(
        "product_id", "net_top_1", "net_top_2", "net_top_3"
    )
    for product_id, *prices in aera_prices:
        price_list = [p for p in prices if p]
        if price_list:
            data[product_id] = price_list
    return data


def fetch_wawibox_competitive_prices():
    data = {}
    rows = WawiboxCompetitorPrice.objects.values(
        "product_id",
        "net_top_1",
        "vendor_id_1",
        "net_top_2",
        "vendor_id_2",
        "net_top_3",
        "vendor_id_3",
        "net_top_4",
        "vendor_id_4",
        "net_top_5",
        "vendor_id_5",
        "net_top_6",
        "vendor_id_6",
    )

    for row in rows:
        pid = row["product_id"]
        prices = []

        for i in range(1, 7):
            price = row[f"net_top_{i}"]
            vendor_id = row[f"vendor_id_{i}"]

            if vendor_id == WawiboxCompetitorPrice.JASADO_VENDOR_ID:
                continue

            if price:
                prices.append(price)

        if prices:
            data[pid] = prices

    return data


def fetch_promotions():
    headers = {h.action_code: h for h in GLSPromotionHeader.objects.all()}

    promo_price = {}
    for p in GLSPromotionPrice.objects.all():
        promo_price.setdefault(p.product_id, []).append(p)

    promo_pos = {}
    blocked_action_codes = set()
    for p in GLSPromotionPosition.objects.all():
        promo_pos.setdefault(p.product_id, []).append(p)
        if p.qty_editable in ("1", 1):
            blocked_action_codes.add(p.action_code)

    return headers, promo_price, promo_pos, blocked_action_codes


def compute_cogs(pid, gls_prices, headers, promo_price):
    today = datetime.today().date()

    cogs = gls_prices.get(pid)
    if not cogs:
        return None

    # ---------- 503 PRICE PROMOTION ----------
    for p in promo_price.get(pid, []):
        header = headers.get(p.action_code)

        if not header.action_type in ["3", "03"]:
            continue

        # date validation
        valid = True
        if p.valid_from and p.valid_to:
            valid = p.valid_from <= today <= p.valid_to
        elif header and header.valid_from and header.valid_to:
            valid = header.valid_from <= today <= header.valid_to

        # if 503 contains promotional_purchase_price always use it
        if valid and p.promotional_purchase_price and p.promotional_purchase_price > 0:
            return p.promotional_purchase_price

    return cogs


def compute_gift_info(pid, cogs, headers, promo_pos, blocked_action_codes):
    today = datetime.today().date()

    promo_positions = promo_pos.get(pid, [])

    for pos in promo_positions:
        action_code = pos.action_code

        if action_code in blocked_action_codes:
            continue

        header = headers.get(action_code)
        if not header:
            continue

        if header.action_type not in ["5", "05", "6", "06", "7", "07"]:
            continue

        try:
            if Decimal(header.natural_discount_qty) <= 0:
                continue
        except Exception:
            CoreLog.error(
                f"Sales prices calculation encountered an error, "
                f"natural_discount_qty may have invalid value for {header.action_code}: "
                f"{traceback.format_exc()}"
            )
            continue

        if header.valid_from and header.valid_to:
            if not (header.valid_from <= today <= header.valid_to):
                continue

        free_qty = Decimal(header.natural_discount_qty or 0)
        total_qty = Decimal(header.min_qty or 0)

        if free_qty > 0 and total_qty > free_qty:
            paid_qty = total_qty - free_qty
            gift_cogs = (cogs * paid_qty) / total_qty
            return {
                "gift_cogs": gift_cogs,
                "free_qty": int(free_qty),
                "paid_qty": int(paid_qty),
                "min_qty": int(total_qty),
                "gift_valid_from": header.valid_from,
                "gift_valid_until": header.valid_to,
                "gift_promo_code": header.action_code,
                "gift_action_type": header.action_type,
            }
    return None


def compute_gls_sales_price(
    pid,
    handling_surcharge,
    cogs,
    competitor_prices,
    middleware_settings,
):
    if not cogs:
        return None

    competitor_rule = middleware_settings.competitor_rule
    min_margin = middleware_settings.normalised_minimum_margin
    undercut = middleware_settings.undercut_value

    base_price = cogs * (1 + handling_surcharge) * (1 + min_margin)

    product_competitor_prices = competitor_prices.get(pid, [])

    if not product_competitor_prices:
        return base_price

    product_competitor_prices.sort()

    if competitor_rule == MiddlewareSetting.RULE_AVERAGE:
        ref_price = sum(product_competitor_prices[:3]) / 3
    else:
        ref_price = product_competitor_prices[0]

    top_comp = ref_price

    if base_price > top_comp:
        return base_price

    return top_comp - undercut


def compute_non_gls_sales_price(
    pid,
    non_gls_price_list,
    competitor_prices,
    middleware_settings,
):

    competitor_rule = middleware_settings.competitor_rule
    min_margin = middleware_settings.normalised_minimum_margin
    undercut = middleware_settings.undercut_value
    price_with_handling_fee = non_gls_price_list.get(pid)

    base_price = price_with_handling_fee * (1 + min_margin)

    product_competitor_prices = competitor_prices.get(pid, [])

    if not product_competitor_prices:
        return base_price

    product_competitor_prices.sort()

    if competitor_rule == MiddlewareSetting.RULE_AVERAGE:
        ref_price = sum(product_competitor_prices[:3]) / 3
    else:
        ref_price = product_competitor_prices[0]

    top_comp = ref_price

    if base_price > top_comp:
        return base_price

    return top_comp - undercut


def update_products(prices, gift_updates):
    """prices = {product_id: {aera: sales_price, wawibox: sales_price,}}"""
    """gift_updates = {product_id: {aera: (gift_sp, min_qty), wawibox: (gift_sp, min_qty)}}"""
    """gift_updates = {product_id: {aera_gift_sp: 2.1, wawibox_gift_sp: 2.2, min_qty: 4, gift_valid_from: 2026/01/05, gift_valid_until: 2026/04/05,}}"""
    ids = list(set(prices.keys()) | set(gift_updates.keys()))
    BATCH = 500

    for i in range(0, len(ids), BATCH):
        chunk = ids[i : i + BATCH]

        products = Product.objects.filter(id__in=chunk).only(
            "id",
            "aera_sales_price",
            "wawibox_sales_price",
            "aera_gift_sales_price",
            "wawibox_gift_sales_price",
            "gift_min_qty",
            "gift_valid_from",
            "gift_valid_until",
            "has_gift_price",
        )
        batch = []
        for p in products:
            if p.id in prices:
                p.aera_sales_price = prices[p.id]["aera"]
                p.wawibox_sales_price = prices[p.id]["wawibox"]

            if p.id in gift_updates:
                p.aera_gift_sales_price = gift_updates[p.id]["aera_gift_sp"]
                p.wawibox_gift_sales_price = gift_updates[p.id]["wawibox_gift_sp"]
                p.gift_min_qty = gift_updates[p.id]["min_qty"]
                p.gift_free_qty = gift_updates[p.id]["free_qty"]
                p.gift_paid_qty = gift_updates[p.id]["paid_qty"]
                p.gift_valid_from = gift_updates[p.id]["gift_valid_from"]
                p.gift_valid_until = gift_updates[p.id]["gift_valid_until"]
                p.gift_promo_code = gift_updates[p.id]["gift_promo_code"]
                p.gift_action_type = gift_updates[p.id]["gift_action_type"]
                p.has_gift_price = True
            else:
                p.aera_gift_sales_price = None
                p.wawibox_gift_sales_price = None
                p.gift_min_qty = None
                p.gift_free_qty = None
                p.gift_paid_qty = None
                p.gift_valid_from = None
                p.gift_valid_until = None
                p.gift_promo_code = None
                p.gift_action_type = None
                p.has_gift_price = False

            batch.append(p)

        if batch:
            Product.objects.bulk_update(
                batch,
                [
                    "aera_sales_price",
                    "wawibox_sales_price",
                    "aera_gift_sales_price",
                    "wawibox_gift_sales_price",
                    "gift_min_qty",
                    "gift_free_qty",
                    "gift_paid_qty",
                    "gift_valid_from",
                    "gift_valid_until",
                    "gift_promo_code",
                    "gift_action_type",
                    "has_gift_price",
                ],
                batch_size=BATCH,
            )


def save_price_history(prices, gift_updates):
    """prices = {product_id: {aera: sales_price, wawibox: sales_price,}}"""
    """gift_updates = {product_id: {aera: (gift_sp, min_qty), wawibox: (gift_sp, min_qty)}}"""
    """gift_updates = {product_id: {aera_gift_sp: 2.1, wawibox_gift_sp: 2.2, min_qty: 4, gift_valid_from: 2026/01/05, gift_valid_until: 2026/04/05,}}"""

    objs = []

    for pid, sp_dict in prices.items():
        gift_dict = gift_updates.get(pid, {})

        objs.append(
            ProductPriceHistory(
                product_id=pid,
                aera_sales_price=sp_dict["aera"],
                wawibox_sales_price=sp_dict["wawibox"],
                aera_gift_sales_price=gift_dict.get("aera_gift_sp"),
                wawibox_gift_sales_price=gift_dict.get("wawibox_gift_sp"),
                gift_min_qty=gift_dict.get("min_qty"),
                gift_free_qty=gift_dict.get("free_qty"),
                gift_paid_qty=gift_dict.get("paid_qty"),
                gift_valid_from=gift_dict.get("gift_valid_from"),
                gift_valid_until=gift_dict.get("gift_valid_until"),
            )
        )

    ProductPriceHistory.objects.bulk_create(objs, batch_size=5000)


def cleanup_history():
    limit = datetime.now() - timedelta(days=90)
    ProductPriceHistory.objects.filter(calculated_at__lt=limit).delete()


def run_pricing_engine():
    try:
        middleware_settings = MiddlewareSetting.objects.first()
        aera_comp_prices = fetch_aera_competitive_prices()
        wawi_comp_prices = fetch_wawibox_competitive_prices()

        pid_sales_price_dict = defaultdict(dict)
        gift_updates = defaultdict(dict)

        # Calculate for GLS products
        product_id_group_id = get_product_ids_and_groups()
        gls_price_list = fetch_gls_prices()
        gls_handling_surcharge = fetch_gls_handling_surcharge()
        promo_headers, promo_price, promo_pos, blocked_action_codes = fetch_promotions()

        for pid, article_group_no in product_id_group_id:
            # Normal sales price
            cogs = compute_cogs(pid, gls_price_list, promo_headers, promo_price)
            handling_surcharge = gls_handling_surcharge.get(article_group_no, 0)
            aera_sp = compute_gls_sales_price(
                pid,
                handling_surcharge,
                cogs,
                aera_comp_prices,
                middleware_settings,
            )
            wawibox_sp = compute_gls_sales_price(
                pid,
                handling_surcharge,
                cogs,
                wawi_comp_prices,
                middleware_settings,
            )

            if aera_sp or wawibox_sp:
                pid_sales_price_dict[pid]["aera"] = aera_sp
                pid_sales_price_dict[pid]["wawibox"] = wawibox_sp

            # Gift sales price
            gift_info = compute_gift_info(
                pid,
                cogs,
                promo_headers,
                promo_pos,
                blocked_action_codes,
            )
            if gift_info:
                aera_gift_sp = compute_gls_sales_price(
                    pid,
                    handling_surcharge,
                    gift_info["gift_cogs"],
                    aera_comp_prices,
                    middleware_settings,
                )
                wawibox_gift_sp = compute_gls_sales_price(
                    pid,
                    handling_surcharge,
                    gift_info["gift_cogs"],
                    wawi_comp_prices,
                    middleware_settings,
                )

                gift_updates[pid]["aera_gift_sp"] = aera_gift_sp
                gift_updates[pid]["wawibox_gift_sp"] = wawibox_gift_sp
                gift_updates[pid]["min_qty"] = gift_info["min_qty"]
                gift_updates[pid]["free_qty"] = gift_info["free_qty"]
                gift_updates[pid]["paid_qty"] = gift_info["paid_qty"]
                gift_updates[pid]["gift_valid_from"] = gift_info["gift_valid_from"]
                gift_updates[pid]["gift_valid_until"] = gift_info["gift_valid_until"]
                gift_updates[pid]["gift_promo_code"] = gift_info["gift_promo_code"]
                gift_updates[pid]["gift_action_type"] = gift_info["gift_action_type"]

        # Calculate for non GLS products
        product_ids = get_non_gls_product_ids()
        non_gls_price_list = fetch_non_gls_prices()

        for pid in product_ids:
            aera_sp = compute_non_gls_sales_price(
                pid,
                non_gls_price_list,
                aera_comp_prices,
                middleware_settings,
            )

            wawibox_sp = compute_non_gls_sales_price(
                pid,
                non_gls_price_list,
                wawi_comp_prices,
                middleware_settings,
            )

            if aera_sp or wawibox_sp:
                pid_sales_price_dict[pid]["aera"] = aera_sp
                pid_sales_price_dict[pid]["wawibox"] = wawibox_sp

        with transaction.atomic():
            update_products(pid_sales_price_dict, gift_updates)
            save_price_history(pid_sales_price_dict, gift_updates)
            cleanup_history()
            CoreLog.info("Sales prices calculated successfully")
        return True
    except Exception:
        CoreLog.error(
            f"Sales prices calculation encountered an error: {traceback.format_exc()}"
        )
        return False

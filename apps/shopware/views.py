from django.conf import settings
import requests
from django.utils import timezone
from collections import defaultdict
import traceback

import time
from django.http import JsonResponse
from .models import (
    AccessToken,
    ShopwareProduct,
    ShopwareExport,
)
from .utils import (
    ShopwareLog,
    get_rule_name,
    get_promotion_name,
)
from utils import (
    clean_payload,
)


# Constants
SHOPWARE_BASE_URL = settings.SHOPWARE_BASE_URL
SHOPWARE_ACCESS_ID = settings.SHOPWARE_ACCESS_ID
SHOPWARE_ACCESS_KEY = settings.SHOPWARE_ACCESS_KEY
SHOPWARE_EUR_CURRENCY_ID = settings.SHOPWARE_EUR_CURRENCY_ID
SHOPWARE_GIFT_RULE_ID = settings.SHOPWARE_GIFT_RULE_ID
TAX_ID_BY_RATE = {
    19: "0192761ae324701f8c02399de67bb89c",
    7: "0192761ae324701f8c02399de749c8b1",
    0: "0192761afe4173bf8e5b9f487fd6e6f0",
}


def get_headers():
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def get_access_token():
    token_obj = AccessToken.objects.first()

    if token_obj and token_obj.is_valid():
        return token_obj.token

    url = f"{SHOPWARE_BASE_URL}/oauth/token"
    url = "https://stage.jasado.de/api/oauth/token"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    payload = {
        "grant_type": "client_credentials",
        "client_id": SHOPWARE_ACCESS_ID,
        "client_secret": SHOPWARE_ACCESS_KEY,
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()

    AccessToken.objects.update_or_create(
        id=token_obj.id if token_obj else None,
        defaults={
            "token": data["access_token"],
            "issued_at": timezone.now(),
            "expires_in": data["expires_in"],
        },
    )

    return data["access_token"]


def fetch_shopware_products():
    try:
        url = f"{SHOPWARE_BASE_URL}/product"
        page = 1
        limit = 500

        existing_skus = set(ShopwareProduct.objects.values_list("sku", flat=True))
        existing_skus_on_shopware = set()
        objs = []

        while True:
            params = {
                "page": page,
                "limit": limit,
            }

            response = requests.get(url, headers=get_headers(), params=params)
            response.raise_for_status()
            data = response.json()

            items = data.get("data", [])
            total = data.get("total", 0)

            if total == 0:
                break

            for p in items:
                existing_skus_on_shopware.add(p["productNumber"])

                if p["productNumber"] in existing_skus:
                    continue

                objs.append(
                    ShopwareProduct(
                        shopware_id=p["id"],
                        sku=p.get("productNumber"),
                        name=p.get("name"),
                    )
                )

            page += 1
            time.sleep(0.05)

        # qs = ShopwareProduct.objects.exclude(sku__in=existing_skus_on_shopware)

        # while qs.exists():
        #     ids = list(qs.values_list("id", flat=True)[:5000])
        #     ShopwareProduct.objects.filter(id__in=ids).delete()

        if objs:
            ShopwareProduct.objects.bulk_create(objs, batch_size=5000)
    except Exception:
        ShopwareLog.error(
            f"Error in fetching current products from shopware: {traceback.format_exc()}"
        )


def test_fetch_products():
    # url = f"{SHOPWARE_BASE_URL}/product"
    # url = f"{SHOPWARE_BASE_URL}/product/0192d278b0e5737b8c94c0bb434597f1"
    url = f"{SHOPWARE_BASE_URL}/product/0192d57935f1727bbf5371b73d31e129"
    # url = f"{SHOPWARE_BASE_URL}/product/0192d4750c3070a6a1ee030873428d90"  # wit gift price
    # url = f"{SHOPWARE_BASE_URL}/promotion"
    # url = f"{SHOPWARE_BASE_URL}/rule-condition"
    page = 1
    limit = 100

    params = {
        "page": page,
        "limit": limit,
    }

    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()
    return response.json()


def push_products_to_shopware(sku=None):
    BATCH_SIZE = 1000
    batch_payload = []
    batch_ids = []
    total_synced = 0

    try:
        product_exports = (
            ShopwareExport.objects.filter(sku=sku)
            if sku
            else ShopwareExport.objects.all()
        )
        for p in product_exports.iterator(chunk_size=BATCH_SIZE):
            if not p.shopware_id or not p.sales_price:
                continue
            product_payload = {
                "id": p.shopware_id,
                "productNumber": p.sku,
                "name": p.name,
                "description": p.description,
                "stock": int(p.stock) if p.stock is not None else None,
                "weight": float(p.weight) if p.weight else None,
                "width": float(p.width) if p.width else None,
                "height": float(p.height) if p.height else None,
                "length": float(p.length) if p.length else None,
                "manufacturerNumber": p.mpn,
                "ean": p.gtin,
                "price": [
                    {
                        "currencyId": SHOPWARE_EUR_CURRENCY_ID,
                        "net": float(p.sales_price),
                        "linked": True,
                    }
                ],
            }

            if p.tax_rate is not None:
                tax_id = TAX_ID_BY_RATE.get(int(float(p.tax_rate)))
                if not tax_id:
                    raise ValueError(f"Missing taxId mapping for rate {p.tax_rate}")
                product_payload["taxId"] = tax_id

            product_payload = clean_payload(product_payload, json_safe=False)

            batch_payload.append(product_payload)
            batch_ids.append(p.shopware_id)

            if len(batch_payload) >= BATCH_SIZE:
                _upsert_product_batch(batch_payload, batch_ids)
                total_synced += len(batch_payload)
                batch_payload.clear()
                batch_ids.clear()

        if batch_payload:
            _upsert_product_batch(batch_payload, batch_ids)
            total_synced += len(batch_payload)

        push_special_offers_to_shopware(sku=sku)
        ShopwareLog.info(
            f"Product sync completed successfully. Total products synced:{total_synced}"
        )

    except Exception:
        ShopwareLog.error(
            f"Product sync failed after syncing {total_synced} products: {traceback.format_exc()}"
        )


def _upsert_product_batch(payload, ids):
    url = f"{SHOPWARE_BASE_URL}/_action/sync"

    sync_body = {
        "product-upsert": {
            "entity": "product",
            "action": "upsert",
            "payload": payload,
        }
    }

    headers = get_headers()
    headers["indexing-behavior"] = "use-queue-indexing"
    headers["sw-skip-trigger-flow"] = "1"

    response = requests.post(
        url,
        headers=headers,
        json=sync_body,
    )
    if response.status_code not in [200, 204]:
        ShopwareLog.error(f"Failed to push product updates: {response.text}")
    response.raise_for_status()

    ShopwareExport.objects.filter(shopware_id__in=ids).update(
        last_pushed_to_shopware=timezone.now()
    )


def index(request):
    data = test_fetch_products()
    # data = fetch_shopware_products()
    # data = push_products_to_shopware("LGZA6A410SOVIT")
    # return HttpResponse(data)
    return JsonResponse(data, safe=False)


def find_promotion(name):
    url = f"{SHOPWARE_BASE_URL}/search/promotion"
    payload = {
        "filter": [
            {
                "type": "equalsAny",
                "field": "name",
                "value": name,
            }
        ]
    }

    r = requests.post(url, headers=get_headers(), json=payload)
    r.raise_for_status()
    data = r.json()["data"]
    return data[0] if data else None


def get_or_create_rule(paid_qty, free_qty):
    name = get_rule_name(paid_qty, free_qty)
    min_qty = paid_qty + free_qty

    url = f"{SHOPWARE_BASE_URL}/search/rule"
    payload = {
        "filter": [
            {
                "type": "equalsAny",
                "field": "name",
                "value": name,
            }
        ]
    }

    r = requests.post(url, headers=get_headers(), json=payload)
    r.raise_for_status()
    data = r.json()["data"]

    if data:
        return data[0]["id"]

    payload = {
        "name": name,
        "priority": 1,
        "conditions": [
            {
                "type": "lineItemQuantity",
                "value": {
                    "operator": ">=",
                    "quantity": min_qty,
                },
            }
        ],
    }

    r = requests.post(url, headers=get_headers(), json=payload)

    r.raise_for_status()
    return r.json()["data"]["id"]


def create_or_update_promotion(
    paid_qty, free_qty, valid_from, valid_until, product_ids
):
    name = get_promotion_name(paid_qty, free_qty, valid_from, valid_until)
    rule_id = get_or_create_rule(paid_qty, free_qty)

    existing = find_promotion(name)

    payload = {
        "name": name,
        "active": True,
        "priority": 1,
        "useSetGroups": True,
        "preventCombination": True,
        "validFrom": valid_from,
        "validUntil": valid_until,
        "orderRules": [
            {
                "conditions": [
                    {
                        "type": "product",
                        "value": {
                            "operator": "=",
                            "productIds": [],
                        },
                    },
                    {
                        "type": "rule",
                        "value": {
                            "operator": "=",
                            "ruleIds": [rule_id],
                        },
                    },
                ]
            }
        ],
        "setgroups": [
            {
                "packagerKey": "COUNT",
                "value": paid_qty + free_qty,
                "sorterKey": "PRICE_ASC",
                "discounts": [
                    {
                        "type": "percentage",
                        "value": 100,
                        "scope": "set",
                        "applyToQuantity": free_qty,
                    }
                ],
            }
        ],
    }

    if existing:
        url = f"{SHOPWARE_BASE_URL}/promotion/{existing['id']}"
        r = requests.get(url, headers=get_headers())
        r.raise_for_status()

        existing_product_ids = set()
        for cond in r.json()["data"]["orderRules"][0]["conditions"]:
            if cond["type"] == "product":
                existing_product_ids = set(cond["value"].get("productIds", []))
                break

        merged_product_ids = list(existing_product_ids | set(product_ids))
        payload["orderRules"][0]["conditions"][0]["value"][
            "productIds"
        ] = merged_product_ids

        res = requests.patch(url, headers=get_headers(), json=payload)
        res.raise_for_status()
        return existing["id"]

    payload["orderRules"][0]["conditions"][0]["value"]["productIds"] = product_ids

    url = f"{SHOPWARE_BASE_URL}/promotion"
    r = requests.post(url, headers=get_headers(), json=payload)
    r.raise_for_status()
    return r.json()["data"]["id"]


def push_special_offers_to_shopware(sku=None):
    BATCH_SIZE = 1000
    product_count = 0
    try:
        product_exports = (
            ShopwareExport.objects.filter(sku=sku, gift_sales_price__isnull=False)
            if sku
            else ShopwareExport.objects.filter(gift_sales_price__isnull=False)
        )
        promotion_groups = defaultdict(list)

        for p in product_exports.iterator(chunk_size=BATCH_SIZE):
            key = (
                p.gift_paid_qty,
                p.gift_free_qty,
                p.gift_valid_from,
                p.gift_valid_until,
            )
            promotion_groups[key].append(p.shopware_id)
            product_count += 1

            if product_count >= BATCH_SIZE:
                _upsert_special_offer_batch(promotion_groups)
                promotion_groups.clear()
                product_count = 0

        if promotion_groups:
            _upsert_special_offer_batch(promotion_groups)

    except Exception:
        ShopwareLog.error(
            f"Product special offer update on marketplace failed: {traceback.format_exc()}"
        )


def _upsert_special_offer_batch(promotion_groups):
    MAX_PRODUCTS_PER_PROMO = 500

    for (
        paid_qty,
        free_qty,
        valid_from,
        valid_until,
    ), product_ids in promotion_groups.items():
        for i in range(0, len(product_ids), MAX_PRODUCTS_PER_PROMO):
            chunk = product_ids[i : i + MAX_PRODUCTS_PER_PROMO]

            create_or_update_promotion(
                paid_qty=paid_qty,
                free_qty=free_qty,
                valid_from=valid_from,
                valid_until=valid_until,
                product_ids=chunk,
            )

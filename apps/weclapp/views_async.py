import asyncio
import aiohttp
import random
from django.conf import settings
from .utils import (
    WeclappLog,
    vat_rate_type,
    upsert_custom_attribute,
    upsert_rrp,
    upsert_sales_price,
    upsert_promo_purchase_price,
    AsyncDb,
    weclapp_clean_payload,
)
from utils import (
    g_to_kg,
    mm_to_m,
    truncate_max_length,
    to_unix_ms,
)
from collections import Counter

from copy import deepcopy

WECLAPP_BASE_URL = settings.WECLAPP_BASE_URL
WECLAPP_API_TOKEN = settings.WECLAPP_API_TOKEN

SEM = asyncio.Semaphore(10)
MAX_RETRIES = 3
BATCH_SIZE = 200


def get_headers():
    return {
        "AuthenticationToken": WECLAPP_API_TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "User-Agent": "Jasado Middleware",
    }


async def raise_for_status_with_message(response):
    if response.status < 400:
        return

    try:
        data = await response.json()
        message = (
            data.get("messages", [{}])[0].get("message")
            or data.get("detail")
            or data.get("error")
        )
    except Exception:
        message = await response.text()

    raise aiohttp.ClientResponseError(
        request_info=response.request_info,
        history=response.history,
        status=response.status,
        message=message,
        headers=response.headers,
    )


async def fetch_article(session, weclapp_id):
    async with session.get(
        f"{WECLAPP_BASE_URL}/article/id/{weclapp_id}",
        headers=get_headers(),
    ) as response:
        if response.status == 429:
            raise aiohttp.ClientResponseError(
                response.request_info, response.history, status=429
            )
        await raise_for_status_with_message(response)
        return await response.json()


async def fetch_article_supply_source(session, supply_source_id):
    async with session.get(
        f"{WECLAPP_BASE_URL}/articleSupplySource/id/{supply_source_id}",
        headers=get_headers(),
    ) as response:
        if response.status == 429:
            raise aiohttp.ClientResponseError(
                response.request_info, response.history, status=429
            )
        return await response.json()


async def put_article(session, weclapp_id, payload):
    async with session.put(
        f"{WECLAPP_BASE_URL}/article/id/{weclapp_id}?ignoreMissingProperties=true&dryRun=true",
        headers=get_headers(),
        json=payload,
    ) as response:
        if response.status == 429:
            raise aiohttp.ClientResponseError(
                response.request_info, response.history, status=429
            )
        await raise_for_status_with_message(response)
        return response.status


async def post_article(session, payload):
    async with session.post(
        f"{WECLAPP_BASE_URL}/article?dryRun=true",
        headers=get_headers(),
        json=payload,
    ) as response:
        if response.status == 429:
            raise aiohttp.ClientResponseError(
                response.request_info, response.history, status=429
            )
        await raise_for_status_with_message(response)
        return response.status


async def put_supply_source(session, supply_source_id, payload):
    async with session.put(
        f"{WECLAPP_BASE_URL}/articleSupplySource/id/{supply_source_id}?ignoreMissingProperties=true&dryRun=true",
        headers=get_headers(),
        json=payload,
    ) as response:
        if response.status == 429:
            raise aiohttp.ClientResponseError(
                response.request_info, response.history, status=429
            )
        await raise_for_status_with_message(response)
        return response.status


async def post_supply_source(session, payload):
    async with session.post(
        f"{WECLAPP_BASE_URL}/articleSupplySource?dryRun=true",
        headers=get_headers(),
        json=payload,
    ) as response:
        if response.status == 429:
            raise aiohttp.ClientResponseError(
                response.request_info, response.history, status=429
            )
        await raise_for_status_with_message(response)
        return response.status


async def build_article_payload(product, gtin_map, weclapp_article=None):
    payload = deepcopy(weclapp_article) if weclapp_article else {}

    md = await AsyncDb.get_master_data(product)
    if md:
        payload.update(
            {
                "articleNumber": product.sku,
                "name": md.description,
                "ean": gtin_map.get(product.supplier_article_no),
                "manufacturerId": await AsyncDb.get_model_property(
                    md, "manufacturer_weclapp_id"
                ),
                "customsTariffNumberId": await AsyncDb.get_model_property(
                    md, "customs_number_weclapp_id"
                ),
                "articleCategoryId": await AsyncDb.get_model_property(
                    md, "product_group_weclapp_id"
                ),
                "manufacturerPartNumber": md.manufacturer_article_no,
                "articleNetWeight": g_to_kg(md.weight),
                "articleLength": mm_to_m(md.length),
                "articleWidth": mm_to_m(md.width),
                "articleHeight": mm_to_m(md.height),
                "description": product.description,
                "countryOfOriginCode": truncate_max_length(md.country_of_origin_alt, 5),
                # "batchNumberRequired": md.batch_number_required,
                # "serialNumberRequired": md.serial_number_required,
                "active": not md.blocked,
                "launchDate": to_unix_ms(md.created_on),
                "taxRateType": vat_rate_type(md.vat_rate),
            }
        )

    # Custom attributes
    attributes_to_upsert = {
        "314848757": {"numberValue": md.product_group_no},
        "314848761": {"booleanValue": md.freely_available},
        "314848763": {"dateValue": to_unix_ms(md.last_fetch_from_gls)},
        "314848765": {"numberValue": md.manufacturer},
        "314848767": {"numberValue": md.article_group_no},
        "314848769": {"stringValue": md.abc_license_plate},
        "314848771": {"stringValue": md.packaging_unit},
        "314848774": {"stringValue": md.alternative_article_no},
        "314848776": {"numberValue": str(md.package_contents)},
        "314848779": {"stringValue": md.packing_unit},
        "314850569": {"stringValue": md.medical_device},
        "314850572": {"stringValue": md.drug},
        "314848785": {"stringValue": md.pzn_no},
        "314848787": {"booleanValue": md.batch_number_required},
        "314848789": {"booleanValue": md.serial_number_required},
        "314848791": {"booleanValue": md.mhd_compulsory},
        "314848793": {"stringValue": md.un_number},
        "314848884": {"stringValue": md.hazard_code},
        "314848717": {"booleanValue": md.store_refrigerated},
        "314848797": {"stringValue": md.hibc_manufacturer_id},
        "314848799": {"stringValue": md.hibc_article_no},
        "314848801": {"stringValue": md.hibc_packaging_index},
    }

    attrs = payload.get("customAttributes", [])
    for attr_id, values in attributes_to_upsert.items():
        attrs = upsert_custom_attribute(
            attrs,
            attr_id=attr_id,
            **values,
        )

    payload["customAttributes"] = attrs

    # rrp
    calculation_prices = payload.get("articleCalculationPrices", [])
    pl = await AsyncDb.get_price_list(product)

    if pl and pl.recommended_retail_price is not None:
        calculation_prices = upsert_rrp(
            calculation_prices,
            pl.recommended_retail_price,
        )

    payload["articleCalculationPrices"] = calculation_prices

    # Sales Price
    promo_price = await AsyncDb.get_promotional_price(product)

    start = promo_price.valid_from if promo_price else None
    end = promo_price.valid_to if promo_price else None

    sales_prices_to_upsert = {
        "NET1": {
            "price": product.aera_sales_price,
            "start": start,
            "end": end,
        },
        "NET2": {
            "price": product.aera_sales_price,
            "start": start,
            "end": end,
        },
        "NET3": {
            "price": product.wawibox_sales_price,
            "start": start,
            "end": end,
        },
        "NET4": {
            "price": product.aera_sales_price,
            "start": start,
            "end": end,
        },
        "NET5": {
            "price": product.aera_sales_price,
            "start": start,
            "end": end,
        },
    }

    sales_price_list = payload.get("articlePrices", [])
    for sales_channel, values in sales_prices_to_upsert.items():

        sales_price_list = upsert_sales_price(
            sales_price_list,
            sales_channel,
            **values,
        )

    payload["articlePrices"] = sales_price_list
    payload = weclapp_clean_payload(payload)

    return payload


async def build_supply_source_payload(product, gtin_map, weclapp_supply_source=None):
    payload = deepcopy(weclapp_supply_source) if weclapp_supply_source else {}

    md = await AsyncDb.get_master_data(product)
    pl = await AsyncDb.get_price_list(product)

    if md:
        payload.update(
            {
                "articleNumber": md.article_no,
                "name": md.description,
                "ean": gtin_map.get(product.supplier_article_no),
                "taxRateType": vat_rate_type(md.vat_rate),
            }
        )

    # Custom attributes
    attributes_to_upsert = {
        "314848803": {"numberValue": str(pl.purchase_price)},
        "314848805": {"numberValue": str(pl.bill_back_price)},
        "314848763": {"dateValue": to_unix_ms(md.last_fetch_from_gls)},
    }

    attrs = payload.get("customAttributes", [])
    for attr_id, values in attributes_to_upsert.items():
        attrs = upsert_custom_attribute(
            attrs,
            attr_id=attr_id,
            **values,
        )

    payload["customAttributes"] = attrs

    # purchase Price
    promo_price = await AsyncDb.get_promotional_price(product)

    if promo_price:
        promo_header = await AsyncDb.get_promo_header(promo_price.action_code)

        min_qty = promo_header.min_qty
        start = promo_price.valid_from
        end = promo_price.valid_to

        gls_handling_surcharge = await AsyncDb.get_gls_handling_surcharge()
        handling_surcharge = gls_handling_surcharge.get(md.article_group_no, 0)
        price = pl.bill_back_price * (1 + handling_surcharge)

        price_data = {
            "price": price,
            "min_qty": min_qty,
            "start": start,
            "end": end,
        }

        article_price_list = payload.get("articlePrices", [])
        article_price_list = upsert_promo_purchase_price(
            article_price_list,
            **price_data,
        )

        payload["articlePrices"] = article_price_list

    payload = weclapp_clean_payload(payload)
    return payload


async def sync_one_product(session, product, gtin_map, DEBUG=False):

    async with SEM:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if product.weclapp_id:
                    article = await fetch_article(session, product.weclapp_id)
                    article_payload = await build_article_payload(
                        product, gtin_map, weclapp_article=article
                    )
                    await put_article(session, product.weclapp_id, article_payload)
                else:
                    article_payload = await build_article_payload(product, gtin_map)
                    await post_article(session, article_payload)

                if product.weclapp_article_supply_source_id:
                    supply_source = await fetch_article_supply_source(
                        session, product.weclapp_article_supply_source_id
                    )
                    supply_source_payload = await build_supply_source_payload(
                        product, gtin_map, weclapp_supply_source=supply_source
                    )
                    await put_supply_source(
                        session,
                        product.weclapp_article_supply_source_id,
                        supply_source_payload,
                    )
                else:
                    supply_source_payload = await build_supply_source_payload(
                        product, gtin_map
                    )
                    await post_supply_source(session, supply_source_payload)

                if DEBUG:
                    import json

                    with open("article_before.json", "w") as f:
                        json.dump(article, f, indent=2)

                    with open("article_after.json", "w") as f:
                        json.dump(article_payload, f, indent=2)

                    with open("supply_source_before.json", "w") as f:
                        json.dump(supply_source, f, indent=2)

                    with open("supply_source_after.json", "w") as f:
                        json.dump(supply_source_payload, f, indent=2)

                await asyncio.sleep(0.3)
                return True

            except aiohttp.ClientResponseError as e:
                if e.status == 429 and attempt < MAX_RETRIES:
                    await asyncio.sleep(2**attempt + random.random())
                    continue

                return {
                    "error_type": str(e.status),
                    "error_message": str(e.message),
                }

            except Exception as e:
                return {
                    "error_type": "exception",
                    "error_message": str(e)[:400],
                }


async def sync_products(product_ids):
    timeout = aiohttp.ClientTimeout(total=120)
    failed_total = 0
    total_products = len(product_ids)
    error_counter = Counter()
    sample_failed_products = []
    MAX_SAMPLE = 20
    gtin_map = await AsyncDb.get_gtin_map()

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for i in range(0, total_products, BATCH_SIZE):
            batch_ids = product_ids[i : i + BATCH_SIZE]
            product_batch = await AsyncDb.get_products_by_ids(batch_ids)
            tasks = [sync_one_product(session, p, gtin_map) for p in product_batch]
            results = await asyncio.gather(*tasks, return_exceptions=False)

            for product, result in zip(product_batch, results):
                if result is not True:
                    failed_total += 1

                    # result contains error info
                    error_type = result.get("error_type", "unknown")
                    error_counter[error_type] += 1

                    if len(sample_failed_products) < MAX_SAMPLE:
                        sample_failed_products.append(
                            {
                                "sku": product.sku,
                                "error_type": error_type,
                                "error_message": result.get("error_message"),
                            }
                        )

    if failed_total:
        message = (
            f"Weclapp product sync had {failed_total} failures | "
            f"errors={dict(error_counter)} | "
            f"failed_products={sample_failed_products}"
        )
        await WeclappLog.aerror(message)

    else:
        await WeclappLog.ainfo(f"{total_products} product sync completed successfully")


async def sync_master_data():
    await AsyncDb.set_sync_completed()

    is_sync_ongoing = await AsyncDb.is_sync_ongoing()
    if not is_sync_ongoing:
        await AsyncDb.set_sync_ongoing()
        product_ids = await AsyncDb.get_gls_product_ids(limit=True)
        await sync_products(product_ids)
        await AsyncDb.set_sync_completed()


# async def debug_one_product():
#     print("DEBUG STARTED")
#     DEBUG_SKU = "LG00011"
#     timeout = aiohttp.ClientTimeout(total=120)
#     gtin_map = await AsyncDb.get_gtin_map()

#     async with aiohttp.ClientSession(timeout=timeout) as session:
#         product = await AsyncDb.get_product_by_sku(DEBUG_SKU)
#         await sync_one_product(session, product, gtin_map, DEBUG=False)


# import asyncio
# import aiohttp

# from apps.weclapp.views_async import debug_one_product, sync_master_data

# # asyncio.run(debug_one_product())
# asyncio.run(sync_master_data())

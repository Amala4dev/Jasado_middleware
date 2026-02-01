from django.conf import settings
import requests
from django.db import transaction
from datetime import datetime
from django.utils import timezone
import time
import traceback
from django.http import JsonResponse
from .models import (
    DentalheldOrder,
    DentalheldOrderItem,
    DentalheldExport,
)
from .utils import (
    DentalheldLog,
    export_dentalheld_products_to_csv,
)
from utils import (
    make_time_zone_aware,
    ftp_connection,
)


# Constants
DENTALHELD_BASE_URL = settings.DENTALHELD_BASE_URL
DENTALHELD_API_KEY = settings.DENTALHELD_API_KEY
DENTALHELD_FTP_HOST = settings.DENTALHELD_FTP_HOST
DENTALHELD_FTP_USER = settings.DENTALHELD_FTP_USER
DENTALHELD_FTP_PASSWORD = settings.DENTALHELD_FTP_PASSWORD
DENTALHELD_FTP_PORT = settings.DENTALHELD_FTP_PORT
DENTALHELD_DOWNLOAD_PATH = settings.DENTALHELD_DOWNLOAD_PATH
PENDING_DELETION_PATH = settings.PENDING_DELETION_PATH


def push_products_to_dentalheld():
    exports = DentalheldExport.objects.all()

    if not exports.exists():
        DentalheldLog.warning("No Dentalheld export rows found, skipping upload")
        return

    update_file = export_dentalheld_products_to_csv(exports)

    with ftp_connection(
        DENTALHELD_FTP_HOST,
        DENTALHELD_FTP_USER,
        DENTALHELD_FTP_PASSWORD,
        port=DENTALHELD_FTP_PORT,
    ) as ftp:
        try:
            ftp.upload_file(update_file)
            DentalheldExport.objects.all().update(
                last_pushed_to_dentalheld=timezone.now()
            )
            DentalheldLog.info("Product data updated successfully")
        except Exception:
            DentalheldLog.error(f"Product data update failed: {traceback.format_exc()}")


def fetch_orders():
    url = f"{DENTALHELD_BASE_URL}/orders"
    order_list = []
    page = 1
    while True:
        params = {
            "api_key": DENTALHELD_API_KEY,
            "page": page,
            # "status": None,
        }

        response = requests.get(url, params=params)

        if response.status_code != 200:
            DentalheldLog.error(f"Failed to fetch orders: {response.text}")
            response.raise_for_status()

        try:
            result = response.json()
            orders = result.get("data", [])
            order_list.extend(orders)

            last_page = result.get("last_page", 1)
            if page >= last_page:
                break
        except Exception:
            DentalheldLog.error(f"Failed to fetch orders: {traceback.format_exc()}")

        page += 1
        time.sleep(0.2)

    return order_list


def fetch_order_detail(order_number):
    url = f"{DENTALHELD_BASE_URL}/orders/details"
    params = {
        "api_key": DENTALHELD_API_KEY,
        "order": order_number,
    }
    data = None
    response = requests.get(url, params=params)
    if response.status_code != 200:
        DentalheldLog.error(
            f"Failed to fetch order detail with order number {order_number}: {response.text}"
        )
        response.raise_for_status()

    try:
        response = requests.get(url, params=params)

        data = response.json()
        if "error" in data:
            DentalheldLog.error(
                f"Failed to fetch order detail with order number {order_number}: {data['error']}"
            )
            return None

        with transaction.atomic():
            order, _ = DentalheldOrder.objects.update_or_create(
                order_number=order_number,
                defaults={
                    # user
                    "user_salutation": data.get("user_salutation"),
                    "user_prename": data.get("user_prename"),
                    "user_name": data.get("user_name"),
                    "user_email": data.get("user_email"),
                    "user_phone": data.get("user_phone"),
                    "comment": data.get("comment"),
                    "created_at": make_time_zone_aware(data.get("created_at")),
                    "cancelled": bool(data.get("cancelled")),
                    "customer_number": data.get("customer_nr"),
                    "merchant_customer_number": data.get("merchant_customer_nr"),
                    "user_type": data.get("user_type"),
                    "user_tax_number": data.get("user_tax_number"),
                    # billing address
                    "billing_salutation": data.get("billing_salutation"),
                    "billing_prename": data.get("billing_prename"),
                    "billing_name": data.get("billing_name"),
                    "billing_company": data.get("billing_company"),
                    "billing_street": data.get("billing_street"),
                    "billing_street_nr": data.get("billing_street_nr"),
                    "billing_location": data.get("billing_location"),
                    "billing_zipcode": data.get("billing_zipcode"),
                    "billing_country": data.get("billing_country"),
                    # delivery address
                    "delivery_salutation": data.get("delivery_salutation"),
                    "delivery_prename": data.get("delivery_prename"),
                    "delivery_name": data.get("delivery_name"),
                    "delivery_company": data.get("delivery_company"),
                    "delivery_street": data.get("delivery_street"),
                    "delivery_street_nr": data.get("delivery_street_nr"),
                    "delivery_location": data.get("delivery_location"),
                    "delivery_zipcode": data.get("delivery_zipcode"),
                    "delivery_country": data.get("delivery_country"),
                    # totals
                    "gross_amount": data.get("total"),
                    "net_amount": data.get("sum"),
                    "tax": data.get("tax"),
                    "shipping_costs": data.get("shipping_costs"),
                    "low_quantity_surcharge": data.get("low_quantity_surcharge"),
                },
            )

            order.items.all().delete()

            for article in data.get("articles", []):
                DentalheldOrderItem.objects.create(
                    order=order,
                    article_id=article.get("article_id"),
                    sku=article.get("merchant_article_id"),
                    name=article.get("name"),
                    manufacturer=article.get("manufacturer"),
                    price=article.get("price"),
                    quantity=article.get("quantity"),
                    packing_unit=article.get("packing_unit"),
                    packing_size=article.get("packing_size"),
                    tax=article.get("tax"),
                    merchant_manufacturer_id=article.get("merchant_manufacturer_id"),
                    was_taxed=bool(article.get("was_taxed")),
                    cancelled=bool(article.get("cancelled")),
                )

    except Exception:
        DentalheldLog.error(
            f"Failed to fetch order detail with order number {order_number}: {traceback.format_exc()}"
        )

    return data


def fetch_and_save_dentalheld_orders():
    orders = fetch_orders()
    successful = 0
    for order in orders:
        date_created = make_time_zone_aware(order.get("created_at"))
        if date_created < timezone.make_aware(datetime(2026, 2, 2)):
            continue
        time.sleep(0.2)
        order = fetch_order_detail(order["number"])
        if order:
            successful += 1

    DentalheldLog.info(f"Fetched and saved {successful} new orders with details")
    return True


def index(request):
    data = fetch_orders()
    # data = fetch_and_save_dentalheld_orders()
    # data = fetch_order_detail("438-5513559-5210023")
    # return HttpResponse(data)
    return JsonResponse(data, safe=False)

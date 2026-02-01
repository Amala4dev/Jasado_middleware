from django.conf import settings
import requests
from .utils import WeclappLog
from utils import to_unix_ms
from datetime import date

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


def test_weclapp_endpoint():
    # page = 1
    # page_size = 800
    # sku = "LG00003"
    # sku = "LG00011"
    # url = f"{WECLAPP_BASE_URL}/article?articleNumber-eq={sku}"
    # url = f"{WECLAPP_BASE_URL}/article?articleCategoryId-eq=44006325"
    # url = f"{WECLAPP_BASE_URL}/article"
    # url = f"{WECLAPP_BASE_URL}/article/id/10227"
    # url = f"{WECLAPP_BASE_URL}/article/id/999998"
    # url = f"{WECLAPP_BASE_URL}/salesOrder/id/314854156"
    # url = f"{WECLAPP_BASE_URL}/salesOrder/id/314853249/createDropshipping"
    url = f"{WECLAPP_BASE_URL}/articleSupplySource/id/463949"
    # url = f"{WECLAPP_BASE_URL}/articleSupplySource?dropshippingPossible-eq=false"
    # url = f"{WECLAPP_BASE_URL}/articleSupplySource"
    # url = f"{WECLAPP_BASE_URL}/articlePrice"
    # url = f"{WECLAPP_BASE_URL}/manufacturer"
    # url = f"{WECLAPP_BASE_URL}/customsTariffNumber"
    # url = f"{WECLAPP_BASE_URL}/customsTariffNumber?page=1&pageSize=1000"

    # url = f"{WECLAPP_BASE_URL}/salesOrder"
    # url = f"{WECLAPP_BASE_URL}/paymentMethod"
    # url = f"{WECLAPP_BASE_URL}/salesOrder?orderNumber-eq=10270"

    # url = f"{WECLAPP_BASE_URL}/customAttributeDefinition"
    # url = f"{WECLAPP_BASE_URL}/party"
    # url = f"{WECLAPP_BASE_URL}/salesChannel/activeSalesChannels"

    # url = f"{WECLAPP_BASE_URL}/articleCategory?page={page}&pageSize={page_size}"
    # url = f"{WECLAPP_BASE_URL}/fulfillmentProvider"
    # url = f"{WECLAPP_BASE_URL}/purchaseOrder"
    # url = f"{WECLAPP_BASE_URL}/purchaseOrder/id/314853263"
    # url = f"{WECLAPP_BASE_URL}/incomingGoods/id/314852138"
    # url = f"{WECLAPP_BASE_URL}/shipment"
    # url = f"{WECLAPP_BASE_URL}/purchaseOrder?salesOrderId-eq=314852006"
    # url = f"{WECLAPP_BASE_URL}/salesOrder"

    headers = get_headers()

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    items = response.json()

    # print(len(items["result"]))

    return items


def fetch_order_by_order_number(order_number):
    url = f"{WECLAPP_BASE_URL}/salesOrder?orderNumber-eq={order_number}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        WeclappLog.error(f"Failed to fetch orders: {response.text}")
        response.raise_for_status()

    results = response.json().get("result", [])

    if not results:
        WeclappLog.error(f"Weclapp order not found for order number {order_number}")
        return None

    if len(results) > 1:
        WeclappLog.error(
            f"Multiple order instances found for order number {order_number}"
        )
        return None

    return results[0]


def fetch_purchase_order_by_sales_order_id(sales_order_weclapp_id):
    url = f"{WECLAPP_BASE_URL}/purchaseOrder?salesOrderId-eq={sales_order_weclapp_id}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        WeclappLog.error(f"Failed to fetch purchase order: {response.text}")
        response.raise_for_status()

    results = response.json().get("result", [])

    if not results:
        WeclappLog.error(
            f"Weclapp purchase order not found for order id {sales_order_weclapp_id}"
        )
        return None

    if len(results) > 1:
        WeclappLog.error(
            f"Multiple purchase order instances found for order id {sales_order_weclapp_id}"
        )
        return None

    return results[0]


def fetch_purchase_order_by_weclapp_id(weclapp_id):
    url = f"{WECLAPP_BASE_URL}/purchaseOrder/id/{weclapp_id}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        WeclappLog.error(
            f"Failed to fetch purchase order by weclapp_id: {response.text}"
        )
        response.raise_for_status()
    return response.json()


def fetch_sales_order_by_weclapp_id(weclapp_id):
    url = f"{WECLAPP_BASE_URL}/salesOrder/id/{weclapp_id}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        WeclappLog.error(f"Failed to fetch sales order by weclapp_id: {response.text}")
        response.raise_for_status()
    return response.json()


def get_sales_orders_with_multiple_shipments():

    from collections import defaultdict

    order_to_shipments = defaultdict(set)
    params = {
        "properties": "id,salesOrders.id",
        "page": 1,
        "pageSize": 1000,
    }
    total_shipments_processed = 0

    while True:

        url = f"{WECLAPP_BASE_URL}/shipment"
        response = requests.get(url, headers=get_headers(), params=params)
        response.raise_for_status()

        shipments = response.json().get("result", [])
        if not shipments:
            break
        total_shipments_processed += len(shipments)

        for shipment in shipments:
            for so in shipment.get("salesOrders", []):
                order_to_shipments[so["id"]].add(shipment["id"])

        params["page"] += 1

    # keep only sales orders with more than one shipment
    print("Total shipments processed:", total_shipments_processed)
    print("Total distinct sales orders found:", len(order_to_shipments))
    return {
        sales_order_id: list(shipment_ids)
        for sales_order_id, shipment_ids in order_to_shipments.items()
        if len(shipment_ids) > 1
    }


def fetch_dropshipping_orders():
    url = f"{WECLAPP_BASE_URL}/salesOrder"
    params = {
        "status-eq": "ORDER_CONFIRMATION_PRINTED",
        "page": 1,
        "pageSize": 100,
    }

    results = []

    while True:
        response = requests.get(url, headers=get_headers(), params=params)
        if response.status_code != 200:
            WeclappLog.error(f"Failed to fetch dropshipping orders: {response.text}")
            response.raise_for_status()

        data = response.json()

        items = data.get("result", [])
        results.extend(items)

        if len(items) < params["pageSize"]:
            break

        params["page"] += 1

    return results


def fetch_latest_shipment_by_order_id(order_weclapp_id):
    url = f"{WECLAPP_BASE_URL}/shipment?salesOrders.id-eq={order_weclapp_id}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        WeclappLog.error(f"Failed to fetch shipment by order_id: {response.text}")
        response.raise_for_status()
    results = response.json().get("result", [])

    if not results:
        return None

    return max(results, key=lambda s: s["createdDate"])


def fetch_shipment_by_order_id(order_weclapp_id):
    url = f"{WECLAPP_BASE_URL}/shipment?salesOrders.id-eq={order_weclapp_id}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        WeclappLog.error(f"Failed to fetch shipment by order_id: {response.text}")
        response.raise_for_status()
    results = response.json().get("result", [])

    return results


def check_serial_number_required(po_item):
    article_id = po_item["articleId"]
    article = fetch_article_by_weclapp_id(article_id)
    batch_number_required = article["batchNumberRequired"]
    serial_number_required = article["serialNumberRequired"]

    return batch_number_required or serial_number_required


def fetch_article_by_weclapp_id(weclapp_id):
    url = f"{WECLAPP_BASE_URL}/article/id/{weclapp_id}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        WeclappLog.error(f"Failed to fetch article by weclapp_id: {response.text}")
        response.raise_for_status()
    return response.json()


def fetch_article_by_sku(sku):
    url = f"{WECLAPP_BASE_URL}/article?articleNumber-eq={sku}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        WeclappLog.error(f"Failed to fetch article by sku: {response.text}")
        response.raise_for_status()
    results = response.json().get("result", [])

    if len(results) > 1:
        WeclappLog.error(f"Multiple articles found for sku {sku}")
        return None

    return results[0]


def create_shipment_from_order(order_weclapp_id):
    # url = f"{WECLAPP_BASE_URL}/salesOrder/id/{order_weclapp_id}/createShipment?dryRun=true"
    url = f"{WECLAPP_BASE_URL}/salesOrder/id/{order_weclapp_id}/createShipment"
    headers = get_headers()
    payload = {"additionalSalesOrderIds": []}
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
        f"Create shipment failed for order with weclapp id = {order_weclapp_id}: {message}"
    )
    return None


# def create_dropshipping_from_order(order_weclapp_id, order_item_ids):
def create_dropshipping_from_order():
    # url = f"{WECLAPP_BASE_URL}/salesOrder/id/{order_weclapp_id}/createDropshipping"
    url = f"{WECLAPP_BASE_URL}/salesOrder/id/314853249/createDropshipping"
    headers = get_headers()
    payload = {
        "orderItemIds": ["314853254"],
        "supplierId": "6836",
    }
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
        # f"Create shipment failed for order with weclapp id = {order_weclapp_id}: {message}"
        f"Create shipment failed for order with weclapp id = : {message}"
    )
    return None


def confirm_purchase_order(purchase_order_weclapp_id):
    url = f"{WECLAPP_BASE_URL}/purchaseOrder/id/{purchase_order_weclapp_id}?ignoreMissingProperties=true"
    payload = {
        "status": "CONFIRMED",
    }
    headers = get_headers()
    response = requests.put(url, json=payload, headers=headers)
    response.raise_for_status()


def set_purchase_order_for_entry(purchase_order_weclapp_id):
    url = f"{WECLAPP_BASE_URL}/purchaseOrder/id/{purchase_order_weclapp_id}?ignoreMissingProperties=true"

    payload = {
        "status": "ORDER_ENTRY_IN_PROGRESS",
    }
    headers = get_headers()
    response = requests.put(url, json=payload, headers=headers)
    response.raise_for_status()


def create_invoice_from_shipment(shipment_weclapp_id):
    url = f"{WECLAPP_BASE_URL}/shipment/id/{shipment_weclapp_id}/createSalesInvoice"
    payload = {}
    headers = get_headers()
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()


def update_purchase_order(payload):
    purchase_order_id = payload["id"]
    url = f"{WECLAPP_BASE_URL}/purchaseOrder/id/{purchase_order_id}?ignoreMissingProperties=true"
    headers = get_headers()
    response = requests.put(url, json=payload, headers=headers)

    updated = response.status_code == 200
    if not updated:
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
            f"Update failed for Purchase order with weclapp id = {purchase_order_id}: {message}"
        )
    return updated


def create_weclapp_order(payload=None):
    if not payload:
        return
    url = f"{WECLAPP_BASE_URL}/salesOrder"
    headers = get_headers()
    response = requests.post(url, json=payload, headers=headers)
    created = response.status_code in [201, 200]
    if not created:
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
            f"Order creation failed:error_message = {message}, payload={payload}"
        )
        return None
    return response.json()


def get_customer_id(order):
    headers = get_headers()
    email = order.customer_email
    url = f"{WECLAPP_BASE_URL}/party?email-eq={email}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    result = response.json().get("result")
    if result:
        customer_id = result[0]["id"]
    else:
        url = f"{WECLAPP_BASE_URL}/party?dryRun=true"
        payload = order.build_weclapp_customer_payload()
        response = requests.post(url, json=payload, headers=headers)
        created = response.status_code in [201, 200]
        if not created:
            WeclappLog.error(f"Failed to create new customer: {response.text}")
            response.raise_for_status()
        customer_id = response.json()["id"]
    return customer_id


def get_customer(id):
    headers = get_headers()
    url = f"{WECLAPP_BASE_URL}/party/id/{id}"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        WeclappLog.error(f"Failed to get customer with id {id}: {response.text}")
        response.raise_for_status()
    return response.json()


def create_weclapp_manufacturer(name):
    url = f"{WECLAPP_BASE_URL}/manufacturer"
    headers = get_headers()

    payload = {
        "name": name,
    }
    response = requests.post(url, json=payload, headers=headers)
    created = response.status_code in [201, 200]
    if not created:
        WeclappLog.error(
            f"Failed to create manufacturer with name {name}: {response.text}"
        )
        response.raise_for_status()
    return response.json()["id"]


def create_article_category(payload):
    url = f"{WECLAPP_BASE_URL}/articleCategory"
    headers = get_headers()
    response = requests.post(url, json=payload, headers=headers)
    created = response.status_code in [201, 200]
    if not created:
        WeclappLog.error(
            f"Failed to create article category with payload {payload}: {response.text}"
        )
        response.raise_for_status()

    return response.json()["id"]


def create_weclapp_custom_number(name):
    url = f"{WECLAPP_BASE_URL}/customsTariffNumber"
    headers = get_headers()

    payload = {
        "name": name,
    }
    response = requests.post(url, json=payload, headers=headers)
    created = response.status_code in [201, 200]
    if not created:
        WeclappLog.error(
            f"Failed to create custom number with name {name}: {response.text}"
        )
        response.raise_for_status()
    return response.json()["id"]

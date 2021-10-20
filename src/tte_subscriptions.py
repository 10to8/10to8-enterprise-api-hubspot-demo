"""
Webhook endpoint handling Subscription Notification callbacks from 10to8.
"""
import multiprocessing
from pprint import pprint
from flask import Flask, request
from requests.exceptions import RequestException, HTTPError

from config import WEBHOOK_HOST
from tte_client import tte_get_customer, tte_update_customer, get_hubspot_ids
from hubspot_client import create_hubspot_contact, \
    update_hubspot_contact_if_changed, \
    delete_hubspot_contact, convert_to_hubspot_data, \
    get_hubspot_contact_by_id, block_outbound_sync_for_invalid_fields

app = Flask(__name__)

SUBSCRIPTION_ROUTE = "/tte/enterprise_api/webhook/customers/"


def get_subscription_url():
    """
    Returns the URL for the 10to8 Subscription Notification for Customers.
    """
    return f"{WEBHOOK_HOST}{SUBSCRIPTION_ROUTE}"


def tte_sync_customer(customer_uri):
    """
    Syncs a single Customer from 10to8 into HubSpot.

    Syncs create, update and delete operations from 10to8 into HubSpot.
    For create and update operations, we get the latest data from 10to8.
    When the customer_uri is not found in 10to8, we assume it is a deletion.

    To keep track of the identity of the record in the other system, we store
    the HubSpot ID in a Custom Field "External ID" on the 10to8 Customer,
    and the 10to8 Customer URI on a custom HubSpot field on the HubSpot
    Contact.

    :param customer_uri: URI for the 10to8 Customer to sync.
    """
    print(f">>> 10to8 -> HubSpot: Syncing {customer_uri} into HubSpot")

    try:
        tte_customer = tte_get_customer(customer_uri)
        new_hubspot_data = convert_to_hubspot_data(tte_customer)
        hubspot_ids = get_hubspot_ids(tte_customer)

        current_hubspot_data = None
        if hubspot_ids is not None and len(hubspot_ids) == 1:
            # Sometimes for a 10to8 customer merge we have multiple hubspot ids
            # For now, we'll just create a new HubSpot Contact.
            current_hubspot_data = get_hubspot_contact_by_id(hubspot_ids[0])

        if current_hubspot_data:
            new_hubspot_data = block_outbound_sync_for_invalid_fields(
                new_hubspot_data
            )
            has_changed = update_hubspot_contact_if_changed(
                hubspot_ids[0],
                current_hubspot_data=current_hubspot_data,
                new_hubspot_data=new_hubspot_data
            )
            if has_changed:
                tte_update_customer(
                    tte_customer["resource_uri"],
                    status=new_hubspot_data["tte_customer_sync_status"]
                )
        else:
            new_hubspot_data = block_outbound_sync_for_invalid_fields(
                new_hubspot_data
            )
            hubspot_id = create_hubspot_contact(
                properties=new_hubspot_data
            )
            tte_update_customer(
                tte_customer["resource_uri"],
                external_id=hubspot_id,
                status=new_hubspot_data["tte_customer_sync_status"]
            )

    except HTTPError as http_error:
        if http_error.response.status_code == 404:
            delete_hubspot_contact(customer_uri)
        else:
            raise

    print(f">>> 10to8 -> HubSpot: Synced {customer_uri} into HubSpot\n")


def tte_sync_customers(customer_uris):
    """
    Processes a list of 10to8 Customer URIs from a Subscription Notification.

    :param customer_uris: A list of 10to8 Customer URIs that need syncing.
    """
    for customer_uri in customer_uris:
        try:
            tte_sync_customer(customer_uri)
        except RequestException as exception:
            error = (f"Skipped customer id {customer_uri}:"
                     f" Exception: {exception}\n")
            print(error)


@app.route(SUBSCRIPTION_ROUTE, methods=['POST'])
def customer_webhook():
    """
    Webhook receiving Subscription Notifications from 10to8 for Customers.

    Asynchronously processes Customer updates to ensure we avoid timeouts on
    the Webhook request.
    """
    notification = request.get_json()
    print(">>> 10to8: Customer notification from 10to8")
    pprint(notification)
    if "scope" in notification and notification["scope"] == "customer":
        if "items" not in notification:
            return "OK", 200

        # For simplicity, we are using multiprocessing
        # In production, we recommend a task queue such as Celery.
        process = multiprocessing.Process(
            target=tte_sync_customers,
            args=(notification["items"],)
        )
        process.start()
        print(">>> 10to8: Customer notification from 10to8: processing\n")

    return "OK", 200

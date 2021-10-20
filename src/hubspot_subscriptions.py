"""
Webhook endpoints for live syncing updates from HubSpot into 10to8.
"""
import multiprocessing
from urllib.parse import urlencode
from pprint import pprint
from flask import Flask, request, redirect
from requests.exceptions import RequestException
import requests
from hubspot.crm.contacts import ApiException

from config import WEBHOOK_HOST, HUBSPOT_CLIENT_ID, HUBSPOT_CLIENT_SECRET, \
    HUBSPOT_SCOPES
from inbound_sync import inbound_sync_create_customer, \
    inbound_sync_update_customer
from tte_client import convert_to_tte_customer_data, \
    tte_delete_customer
from hubspot_client import get_hubspot_contact_by_id


app = Flask(__name__)

SUBSCRIPTION_ROUTE = "/hubspot/webhook"
START_INSTALL_ROUTE = "/hubspot/start"
INSTALL_ROUTE = "/hubspot/install"


def get_subscription_url():
    """
    Returns the URL for the HubSpot Webhook for Contact data.
    """
    return f"{WEBHOOK_HOST}{SUBSCRIPTION_ROUTE}"


def get_install_url():
    """
    Returns the Callback URL for the HubSpot App installation flow.
    """
    return f"{WEBHOOK_HOST}{INSTALL_ROUTE}"


def handle_hubspot_notification(notification):
    """
    Processes a single notification from a HubSpot Webhook for Contact data.

    Syncs create, update and delete operations from HubSpot into 10to8.
    For create and update operations, we get the latest data from HubSpot.

    To keep track of the identity of the record in the other system, we store
    the HubSpot ID in a Custom Field "External ID" on the 10to8 Customer,
    and the 10to8 Customer URI on a custom HubSpot field on the HubSpot
    Contact.

    :param notification: a single notification from a HubSpot Webhook.
    """
    print(">>> HubSpot -> 10to8: Syncing into 10to8")
    try:
        subscription_type = notification.get("subscriptionType", None)
        if subscription_type == "contact.propertyChange":
            hubspot_id = notification["objectId"]
            hubspot_contact_properties = get_hubspot_contact_by_id(
                hubspot_id
            )
            tte_customer_data = convert_to_tte_customer_data(
                hubspot_contact_properties
            )
            if tte_customer_data.get("tte_resource_uri", None) is not None:
                inbound_sync_update_customer(
                    hubspot_contact_properties,
                    tte_customer_data
                )
            else:
                print(f"Skipping notification {notification}"
                      f" - tte_resource_uri not found")

        if subscription_type == "contact.creation":
            hubspot_id = notification["objectId"]
            hubspot_contact_properties = get_hubspot_contact_by_id(
                hubspot_id
            )
            tte_customer_data = convert_to_tte_customer_data(
                hubspot_contact_properties
            )
            inbound_sync_create_customer(
                tte_customer_data,
                True
            )
        if subscription_type == "contact.deletion":
            hubspot_id = notification["objectId"]
            hubspot_contact_properties = get_hubspot_contact_by_id(
                hubspot_id, deleted=True
            )
            # Note: we're forcing deletions even if the 10to8 Customer has
            # future Events booked in 10to8.

            # To build a system that allows the user to intervene
            # when a 10to8 Customer has future Events, set force=False
            # and handle the 409 conflict error.

            # See https://10to8.com/api/enterprise/v2/#operation/delete-api-enterprise-v2-customer-id
            # for more about deletion and conflicts.
            tte_delete_customer(
                hubspot_contact_properties["tte_customer_uri"],
                force=True
            )
    except ApiException as exception:
        print(f"Skipping notification {notification}"
              f" Exception: {exception}")
    except RequestException as exception:
        print(f"Skipping notification {notification}"
              f" Exception: {exception}")

    print(">>> HubSpot -> 10to8: Synced into 10to8")


def handle_hubspot_notifications(notifications):
    """
    Processes a list of Contact notifications from a HubSpot Webhook.

    :param notifications: list of notifications from HubSpot.
    """
    for notification in notifications:
        handle_hubspot_notification(notification)


@app.route(SUBSCRIPTION_ROUTE, methods=['POST'])
def hubspot_webhook():
    """
    Webhook receiving notifications from HubSpot for Contact updates.

    Asynchronously processes Contact updates to ensure we avoid timeouts on
    the Webhook request.
    """
    notifications = request.get_json()
    print(">>> HubSpot -> 10to8: HubSpot notifications")
    pprint(notifications)

    # For simplicity, we are using multiprocessing
    # In a production environment, we recommend a task queue such as Celery.
    process = multiprocessing.Process(
        target=handle_hubspot_notifications,
        args=(notifications,)
    )
    process.start()

    print(">>> HubSpot -> 10to8: HubSpot notifications completed")

    return "OK", 200


@app.route(START_INSTALL_ROUTE, methods=['GET'])
def start_install():
    """
    Endpoint used to initiate HubSpot App installation flow.

    Navigate to this endpoint in a browser to install your HubSpot App.

    Required to enable HubSpot App installation, which is needed to enable
    Webhooks in HubSpot.
    """
    query_args = {
        "client_id": HUBSPOT_CLIENT_ID,
        "redirect_uri": get_install_url(),
        "scope": HUBSPOT_SCOPES
    }
    redirect_url = (f"https://app.hubspot.com/oauth/authorize"
                    f"?{urlencode(query_args)}")
    print(redirect_url)
    return redirect(redirect_url)


@app.route(INSTALL_ROUTE, methods=['GET'])
def install_app():
    """
    Callback used in HubSpot App installation flow.

    Required to enable HubSpot App installation, which is needed to enable
    Webhooks in HubSpot.
    """
    query_args = request.args
    if "code" not in query_args:
        return "Error - code argument missing", 400

    code = query_args["code"]
    args = {
        "grant_type": "authorization_code",
        "client_id": HUBSPOT_CLIENT_ID,
        "client_secret": HUBSPOT_CLIENT_SECRET,
        "redirect_uri": get_install_url(),
        "code": code
    }
    response = requests.post("https://api.hubapi.com/oauth/v1/token", args)
    pprint(response)
    pprint(response.json())
    response.raise_for_status()
    return "10to8 HubSpot CRM Demo Connected Successfully!", 200

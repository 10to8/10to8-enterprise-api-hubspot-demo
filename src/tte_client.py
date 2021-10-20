"""
Manages API calls into the 10to8 Enterprise API.
"""
import time
from datetime import datetime
from pprint import pprint
from urllib.parse import urlencode
import requests
from validate_email import validate_email

from config import TTE_ENTERPRISE_API_KEY, TTE_HOST


def get_tte_headers():
    """
    Returns the HTTP headers for requests to 10to8's Enterprise API.

    Uses the 'TTE_ENTERPRISE_API_KEY' in config.py.
    """
    auth_headers = {
        "Authorization": f"token {TTE_ENTERPRISE_API_KEY}"
    }
    # Simple rate limiting to avoid triggering 429 throttling
    # - would be better to handle 429 error and wait for the time interval
    #  returned in the error payload/headers.
    time.sleep(1)
    return auth_headers


def join_names(firstname, lastname):
    """
    Combines names into a single name string.

    :param firstname: string for the Customer's firstname.
    :param lastname: string for the Customer's lastname.
    """
    if firstname is None:
        firstname = ""
    if lastname is None:
        lastname = ""
    spacer = " " if firstname and lastname else ""
    return f"{firstname}{spacer}{lastname}"


def convert_to_tte_customer_data(hubspot_contact_properties):
    """
    Converts a HubSpot Contact into data for a 10to8 Customer.

    :param hubspot_contact_properties: a single HubSpot Contact as
        a dictionary.

    :returns: a single 10to8 Customer as a dictionary.
    """
    firstname = hubspot_contact_properties["firstname"]
    lastname = hubspot_contact_properties["lastname"]
    email = hubspot_contact_properties.get("email", None)
    phone = hubspot_contact_properties.get("phone", None)
    hubspot_id = hubspot_contact_properties["hs_object_id"]
    resource_uri = hubspot_contact_properties.get("tte_customer_uri", None)
    secondary_emails = hubspot_contact_properties.get(
        "tte_customer_secondary_emails", None)
    secondary_phone = hubspot_contact_properties.get(
        "tte_customer_secondary_phone", None)

    tte_customer_data = {
        "name": join_names(firstname, lastname),
        "emails": [email] if email else [],
        "numbers": [phone] if phone else [],
        "external_id": hubspot_id,
        "status": get_status()
    }

    if secondary_emails is not None:
        tte_customer_data["emails"].extend([
            e for e in secondary_emails.split(",\n") if len(e) > 0
        ])

    if secondary_phone is not None:
        tte_customer_data["numbers"].extend([
            n for n in secondary_phone.split(",\n") if len(n) > 0
        ])

    if resource_uri is not None and resource_uri != "":
        tte_customer_data["tte_resource_uri"] = resource_uri

    return tte_customer_data


def block_inbound_sync_for_invalid_fields(hubspot_data, tte_customer_data):
    """
    Blocks inbound sync for fields in 10to8 which are in an invalid state
    for HubSpot (and thus cannot be synced.)

    Hubspot is stricter than 10to8 regarding email validation.

    We don't want to lose the invalid data in 10to8.
    So we block the inbound sync in this case,
    and show a sync error in the sync status field on the Customer.
    """
    if hubspot_data["email"] == "" or hubspot_data["email"] is None:
        print("Block inbound sync: new email is blank: checking tte field")
        current_tte_customer = tte_get_customer(
            tte_customer_data["tte_resource_uri"]
        )
        if len(current_tte_customer["emails"]) > 0:
            # Check if the email in 10to8 is invalid
            current_primary_email = current_tte_customer["emails"][0]
            if not validate_email(
                current_primary_email,
                check_format=True,
                check_dns=False,
                check_blacklist=False,
                check_smtp=False
            ):
                print("Block inbound sync: old email is invalid: block change")
                # Show a sync error in the customer record status field
                tte_customer_data["status"] = \
                    f"Error: Invalid email {current_primary_email}"
                # Keep the old value
                tte_customer_data["emails"].insert(0, current_primary_email)
    return tte_customer_data


def get_hubspot_ids(tte_customer):
    """
    Retrieves the External IDs from a 10to8 Customer.

    :param tte_customer: 10to8 Customer data as a dictionary.

    :returns: an array if External IDs. Most of the time this has a single
        element. Customers merged in 10to8 will have more than 1 element.
        Note: 10to8 Customers merged in 10to8 are not handled by this demo.
    """
    if "custom_fields" in tte_customer:
        if "External ID" in tte_customer["custom_fields"]:
            hubspot_id = tte_customer["custom_fields"]["External ID"]
            return hubspot_id.split(", ")
    return None


def tte_get_customer_page(url=None, limit=10, deleted=True):
    """
    Fetches a page of Customers from a 10to8 Organisation.

    :param url: URL for the page to fetch, or None to fetch the first page.
    :param limit: maximum number of customers to fetch per page.
    :param deleted: when true, include deleted records in this list.

    :returns: Customer data page as a dictionary.
    """
    print(f"Fetching page of customers from 10to8 {url} {limit}")

    auth_headers = get_tte_headers()
    if url is None:
        query_args = urlencode({"include_deleted": deleted, "limit": limit})
        url = f"{TTE_HOST}/api/enterprise/v2/customer/?{query_args}"

    response = requests.get(url, headers=auth_headers)
    pprint(response.json())
    response.raise_for_status()
    print(f"Fetched page of customers from 10to8 {url} {limit}")

    return response.json()


def tte_get_customer(url):
    """
    Fetches a Customer from a 10to8 Organisation.

    :param url: URI for the 10to8 Customer record.

    :returns: Customer data as a dictionary.
    """
    print(f"Fetching customer from 10to8 {url}")

    auth_headers = get_tte_headers()
    response = requests.get(url, headers=auth_headers)
    pprint(response.json())
    response.raise_for_status()
    print(f"Fetched customer from 10to8 {url}")

    return response.json()


def get_status():
    """
    Returns a string representing a successful sync with a timestamp.
    """
    return f"Last synced: {datetime.now().isoformat()}"


def tte_create_customer(
    name=None,
    emails=None,
    numbers=None,
    external_id=None,
    status=""
):
    """
    Creates a 10to8 Customer record.

    :param name: a string for the Customer's name.
    :param emails: an array of emails for the Customer.
    :param numbers: an array of phone numbers for the Customer.
    :param external_id: a string with the Customer's External ID.
    :param status: a string with the Customer's Sync Status.
    """
    print(f"Creating 10to8 customer with external_id {external_id}")

    auth_headers = get_tte_headers()

    customer_data = {
        "name": name,
        "emails": emails if emails is not None else [],
        "numbers": numbers if numbers is not None else [],
        "custom_fields": {
            "Sync Status": status
        }
    }

    if external_id is not None:
        customer_data["custom_fields"]["External ID"] = external_id

    response = requests.post(
        f"{TTE_HOST}/api/enterprise/v2/customer/",
        json=customer_data,
        headers=auth_headers
    )
    pprint(response.json())
    response.raise_for_status()
    tte_resource_uri = response.headers["location"]

    print(f"Created 10to8 customer: {external_id} as {tte_resource_uri}")

    return tte_resource_uri


def tte_update_customer(
    tte_resource_uri=None,
    name=None,
    emails=None,
    numbers=None,
    external_id=None,
    status=""
):
    """
    Updates a 10to8 Customer record.

    :param tte_resource_uri: URI for the 10to8 Customer to update.
    :param name: a string for the Customer's name.
    :param emails: an array of emails for the Customer.
    :param numbers: an array of phone numbers for the Customer.
    :param external_id: a string with the Customer's External ID.
    :param status: a string with the Customer's Sync Status.
    """
    print(f"Updating 10to8 customer {tte_resource_uri}")

    auth_headers = get_tte_headers()

    customer_data = {
        "custom_fields": {
            "Sync Status": status
        }
    }
    if name is not None:
        customer_data["name"] = name

    if emails is not None:
        customer_data["emails"] = emails

    if numbers is not None:
        customer_data["numbers"] = numbers

    if external_id is not None:
        customer_data["custom_fields"]["External ID"] = external_id

    response = requests.patch(
        tte_resource_uri,
        json=customer_data,
        headers=auth_headers
    )
    pprint(response.json())
    response.raise_for_status()

    print(f"Updated 10to8 customer {tte_resource_uri}")


def tte_delete_customer(
    tte_resource_uri=None,
    force=False
):
    """
    Deletes a 10to8 Customer.

    :param tte_resource_uri: URI for the 10to8 Customer to delete.
    :param force: when True, ignores any conflicts caused by pending events on
        the 10to8 Customer; when false, raises an exception with a 409
        conflict when there are pending events on the 10to8 Customer.
    """
    print(f"Deleting customer from 10to8 {tte_resource_uri}")
    auth_headers = get_tte_headers()

    response = requests.delete(
        tte_resource_uri,
        headers=auth_headers,
        params={
            "force": force
        }
    )
    response.raise_for_status()
    print(f"Deleted customer from 10to8 {tte_resource_uri}")


def get_subscriptions():
    """
    Fetches a list of 10to8 Subscriptions for our 10to8 Organisation.
    """
    auth_headers = get_tte_headers()
    endpoint_url = f"{TTE_HOST}/api/enterprise/v2/subscription/"

    response = requests.get(endpoint_url, headers=auth_headers)
    pprint(response.json())
    response.raise_for_status()

    return response.json()


def delete_subscription(tte_subscription_uri):
    """
    Deletes a 10to8 Subscription.

    :param tte_subscription_uri: URI for the 10to8 Subscription to delete.
    """
    auth_headers = get_tte_headers()

    response = requests.delete(tte_subscription_uri, headers=auth_headers)
    response.raise_for_status()


def delete_old_subscriptions():
    """
    Deletes all existing 10to8 Customer Subscriptions.
    """
    subscriptions = get_subscriptions()

    for subscription in subscriptions["results"]:
        if subscription["scope"] == "customer":
            delete_subscription(subscription["resource_uri"])


def register_subscription(callback_url):
    """
    Creates a 10to8 Subscription.

    :param callback_url: webhook URL to receive Subscription Notifications
        from 10to8 for Customers.

    :returns: body of the HTTP response to our regisitration request.
    """
    print(f"Registering 10to8 subscription {callback_url}")
    auth_headers = get_tte_headers()

    data = {
        "callback_url": callback_url,
        "scope": "customer"
    }
    endpoint_url = f"{TTE_HOST}/api/enterprise/v2/subscription/"
    response = requests.post(endpoint_url, json=data, headers=auth_headers)
    pprint(response.json())
    response.raise_for_status()
    print(f"Registered 10to8 subscription {callback_url}")
    return response.json()

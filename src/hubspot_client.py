"""Manages API calls into HubSpot"""
from datetime import datetime
from pprint import pprint

import hubspot
from hubspot.crm.contacts import PublicObjectSearchRequest, \
    SimplePublicObjectInput, ApiException
from validate_email import validate_email

from config import HUBSPOT_API_KEY

# List of properties to fetch when getting Contacts from HubSpot.
HUBSPOT_PROPERTIES = [
    "firstname",
    "lastname",
    "hs_object_id",
    "email",
    "phone",
    "tte_customer_uri",
    "tte_customer_secondary_emails",
    "tte_customer_secondary_phone",
    "tte_customer_sync_status"
]

# List of properties to check when comparing HubSpot Contacts.
HUBSPOT_COMPARISON_PROPERTIES = [
    "firstname",
    "lastname",
    "email",
    "phone",
    "tte_customer_secondary_emails",
    "tte_customer_secondary_phone"
]


client = hubspot.Client.create(api_key=HUBSPOT_API_KEY)


def get_hubspot_sync_status():
    """
    Returns a string representing a successful sync with a timestamp.
    """
    return f"Last synced: {datetime.now().isoformat()}"


def convert_to_hubspot_data(tte_customer_data):
    """
    Converts a 10to8 Customer into properties for a HubSpot Contact.

    :param tte_customer_data: a single 10to8 Customer as a dictionary.

    :returns: properties for a single HubSpot Contact.
    """
    data = {}
    names = tte_customer_data["name"].split(" ")
    numbers = tte_customer_data["numbers"]
    emails = tte_customer_data["emails"]
    data = {
        "firstname": names[0],
        "lastname": " ".join(names[1:]),
        "tte_customer_uri": tte_customer_data["resource_uri"],
        "tte_customer_sync_status": get_hubspot_sync_status()
    }
    if len(numbers) > 0:
        data["phone"] = numbers[0]
        data["tte_customer_secondary_phone"] = ",\n".join(numbers[1:])
    else:
        data["phone"] = ""
        data["tte_customer_secondary_phone"] = ""
    if len(emails) > 0:
        data["email"] = emails[0]
        data["tte_customer_secondary_emails"] = ",\n".join(emails[1:])
    else:
        data["email"] = ""
        data["tte_customer_secondary_emails"] = ""
    return data


def block_outbound_sync_for_invalid_fields(hubspot_data):
    """
    Blocks outbound sync for fields in 10to8 which are in an invalid state
    for HubSpot (and thus cannot be synced.)

    HubSpot's primary email address field only accepts valid emails,
    so we change it to blank instead, and show a sync error in the sync status
    field on the Contact.
    """
    if hubspot_data["email"] != "" and not validate_email(
        hubspot_data["email"],
        check_format=True,
        check_dns=False,
        check_blacklist=False,
        check_smtp=False
    ):
        print("Block outbound sync: first email in 10to8 is invalid")
        # Show a sync error in the customer record status field
        hubspot_data["tte_customer_sync_status"] = \
            f"Error: Invalid email {hubspot_data['email']}"
        # If the email address from 10to8 is not valid, we'll leave it blank.
        hubspot_data["email"] = ""
    else:
        # Clear sync errors in the customer record status field
        hubspot_data["tte_customer_sync_status"] = get_hubspot_sync_status()
    return hubspot_data


def data_has_changed(current, new, properties):
    """
    Compares two dictionaries, checking only the keys in list of properties.

    :param current: current version of the dictionary.
    :param new: new version of the dictionary.
    :param properties: list of dictionary keys of properties to compare.

    :returns: True if the dictionaries differ, False if they are identical
        (filtered by just the list of keys specified.)
    """
    for property_name in properties:
        if current[property_name] is None and new[property_name] == "":
            continue
        if current[property_name] != new[property_name]:
            return True
    return False


def has_error_status_changed(current_hubspot_data, new_hubspot_data):
    """
    Returns True when we change between an error state and a valid state.
    """
    print(f"has_error_status_changed(\n"
          f"{current_hubspot_data},\n{new_hubspot_data})\n")
    current_sync_status = current_hubspot_data.get(
        "tte_customer_sync_status",
        None
    )
    new_sync_status = new_hubspot_data.get(
        "tte_customer_sync_status",
        None
    )
    if current_sync_status is None:
        current_sync_status = ""

    if new_sync_status is None:
        new_sync_status = ""

    status_changed = current_sync_status != new_sync_status
    status_error = \
        "Error" in current_sync_status or \
        "Error" in new_sync_status
    return status_changed and status_error


def get_hubspot_contact_page(after=None, limit=10, sync_deletions=False):
    """
    Fetches a page of Contacts from HubSpot.

    :param after: cursor for page to fetch, or None to fetch the first page.
    :param limit: number of Contacts to fetch per page.
    :param sync_deletions: when True, fetches non-archived Contacts;
        when False, fetches archived Contacts.
    """
    print(f"Fetching a page of Contacts from HubSpot: {after}")
    try:
        api_response = client.crm.contacts.basic_api.get_page(
            after=after,
            limit=limit,
            properties=HUBSPOT_PROPERTIES,
            archived=sync_deletions
        )
        if api_response.paging and api_response.paging.next.after:
            after = api_response.paging.next.after
        else:
            after = None
        pprint(api_response)

        print(f"Fetched a page of Contacts from HubSpot: {after}")

        if api_response.results:
            return api_response.results, after

    except ApiException as exception:
        print(f"Exception - basic_api.get_page: {exception}\n")

    return [], None


def get_hubspot_contact(tte_resource_uri):
    """
    Fetches a HubSpot Contact linked to a 10to8 Customer.

    :param tte_resource_uri: URI of the linked 10to8 Customer.
    :returns: list of HubSpot Contacts linked to a 10to8 Customer. Usually
        only contains one result.
    """
    print(f"Fetching HubSpot Contacts with External ID {tte_resource_uri}")
    public_object_search_request = PublicObjectSearchRequest(
        filter_groups=[{
            "filters": [{
                "value": tte_resource_uri,
                "propertyName": "tte_customer_uri",
                "operator": "EQ"
            }]
        }],
        limit=20,
        after=0
    )
    try:
        # pragma pylint: disable=E1101
        api_response = client.crm.contacts.search_api.do_search(
            public_object_search_request=public_object_search_request
        )
        pprint(api_response)
        print(f"Fetched HubSpot Contacts with External ID {tte_resource_uri}")
        return api_response.results

    except ApiException as exception:
        print(f"Exception - search_api.do_search: {exception}\n")
    return None


def get_hubspot_contact_by_id(hubspot_id, deleted=False):
    """
    Fetches a HubSpot Contact.

    :param hubspot_id: ID of the HubSpot Contact to fetch.
    :param deleted: when True, fetches archived records too; when False,
        ignores archived customers in HubSpot.
    """
    print(f"Fetching HubSpot Contact with HubSpot id {hubspot_id}")

    try:
        api_response = client.crm.contacts.basic_api.get_by_id(
            contact_id=hubspot_id,
            archived=deleted,
            properties=HUBSPOT_PROPERTIES
        )
        pprint(api_response)
        return api_response.properties
    except ApiException as exception:
        print(f"Exception - basic_api.get_by_id: {exception}\n")
        raise
    return None


def create_hubspot_contact(properties=None):
    """
    Creates a HubSpot Contact.

    :param properties: the new Customer's data from 10to8.
    """
    print(f"Creating HubSpot Contact {properties}")

    simple_public_object_input = SimplePublicObjectInput(properties=properties)

    try:
        api_response = client.crm.contacts.basic_api.create(
            simple_public_object_input=simple_public_object_input
        )
        pprint(api_response)
        print(f"Created HubSpot Contact with id {api_response.id}")
        return api_response.id

    except ApiException as exception:
        print(f"Exception - basic_api.update: {exception}\n")
    return None


def update_hubspot_contact(hubspot_id, properties=None):
    """
    Updates a HubSpot Contact.

    :param hubspot_id: ID of the HubSpot Contact to update.
    :param properties: the new data from 10to8.
    """
    print(f"Updating HubSpot Contact {hubspot_id} with {properties}")

    simple_public_object_input = SimplePublicObjectInput(properties=properties)

    try:
        api_response = client.crm.contacts.basic_api.update(
            contact_id=hubspot_id,
            simple_public_object_input=simple_public_object_input
        )
        pprint(api_response)

        print(f"Updated HubSpot Contact {hubspot_id} with {properties}")

    except ApiException as exception:
        print(f"Exception - basic_api.update: {exception}\n")


def update_hubspot_contact_if_changed(
    hubspot_id,
    current_hubspot_data=None,
    new_hubspot_data=None
):
    """
    Updates a HubSpot Contact only if there is has been a change in the data.

    :param hubspot_id: ID of the HubSpot Contact to update.
    :param current_hubspot_data: the data currently in HubSpot.
    :param new_hubspot_data: the new data from 10to8.

    :returns: True if there has been a change (and thus we synced),
        False otherwise.
    """
    has_changed = data_has_changed(
        current_hubspot_data,
        new_hubspot_data,
        HUBSPOT_COMPARISON_PROPERTIES
    )
    error_status_changed = has_error_status_changed(
        current_hubspot_data,
        new_hubspot_data
    )
    if has_changed or error_status_changed:
        update_hubspot_contact(hubspot_id, new_hubspot_data)
    else:
        print("Skipped - no changes detected")
    return has_changed or error_status_changed


def delete_hubspot_contact(tte_resource_uri):
    """
    Archives Contacts in HubSpot linked to a 10to8 Customer.

    :param tte_resource_uri: URI for a 10to8 Customer.
    """
    print(f"Deleting HubSpot Contacts with External ID {tte_resource_uri}")

    results = get_hubspot_contact(tte_resource_uri)
    if results is None:
        print(f"HubSpot Contact {tte_resource_uri} not found: skipped")
        return

    for hubspot_contact in results:
        hubspot_id = hubspot_contact.id
        try:
            api_response = client.crm.contacts.basic_api.archive(
                contact_id=hubspot_id
            )
            pprint(api_response)

            print(f"Deleted HubSpot Contact {hubspot_id}"
                  f" for External ID {tte_resource_uri}")

        except ApiException as exception:
            print(f"Exception - basic_api.archive: {exception}\n")

"""
Setup Subscriptions and fields in HubSpot and Subscriptions in 10to8.
"""
from pprint import pprint
import hubspot
from hubspot.crm.properties import PropertyCreate, ApiException
from hubspot_register_subscription import setup_hubspot_subscriptions
from tte_register_subscription import setup_tte_subscriptions

from config import HUBSPOT_API_KEY

# pragma pylint: disable=E1120

client = hubspot.Client.create(api_key=HUBSPOT_API_KEY)


def setup_hubspot_contact_uri_field():
    """
    Creates a field on Contacts in HubSpot to store the 10to8 Customer URI.

    When a 10to8 Customer is synced with a HubSpot Contact, the field
    'tte_customer_uri' on the HubSpot Contact contains the
    10to8 Customer URI for the 10to8 Customer we have synced with.
    """
    print("Creating 10to8 Customer URI field in HubSpot")
    try:
        api_response = client.crm.properties.core_api.archive(
            object_type="Contacts",
            property_name="tte_customer_uri"
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - core_api.archive: {exception}\n")

    property_create = PropertyCreate(
        name="tte_customer_uri",
        label="10to8 Customer URI",
        type="string",
        field_type="text",
        group_name="contactinformation",
        options=[],
        hidden=False,
        form_field=True
    )
    try:
        api_response = client.crm.properties.core_api.create(
            object_type="Contacts",
            property_create=property_create
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - core_api.create: {exception}\n")
        raise

    print("Created 10to8 Customer URI field in HubSpot")


def setup_hubspot_secondary_emails_field():
    """
    Creates a field on Contacts in HubSpot to store secondary emails.

    A HubSpot field, 'tte_customer_secondary_emails' is created to store the
    secondary phone numbers for a 10to8 Customer record.

    Deletes any existing field before creating the field with the correct
    attributes.

    (Currently HubSpot's secondary emails are not accessible via HubSpot's
    API, so we are creating our own field instead.)
    """
    print("Creating 10to8 Customer Secondary Emails field in HubSpot")
    try:
        api_response = client.crm.properties.core_api.archive(
            object_type="Contacts",
            property_name="tte_customer_secondary_emails"
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - core_api.archive: {exception}\n")

    property_create = PropertyCreate(
        name="tte_customer_secondary_emails",
        label="10to8 Customer Secondary Emails",
        type="string",
        field_type="textarea",
        group_name="contactinformation",
        options=[],
        hidden=False,
        form_field=True
    )
    try:
        api_response = client.crm.properties.core_api.create(
            object_type="Contacts",
            property_create=property_create
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - core_api.create: {exception}\n")
        raise

    print("Creating 10to8 Customer Secondary Emails field in HubSpot")


def setup_hubspot_secondary_phone_numbers_field():
    """
    Creates a field on Contacts in HubSpot to store secondary phone numbers.

    A HubSpot field, 'tte_customer_secondary_phone' is created to store the
    secondary phone numbers for a 10to8 Customer record.

    Deletes any existing field before creating the field with the correct
    attributes.
    """
    print("Creating 10to8 Customer Secondary Phone Numbers field in HubSpot")
    try:
        api_response = client.crm.properties.core_api.archive(
            object_type="Contacts",
            property_name="tte_customer_secondary_phone"
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - core_api.archive: {exception}\n")

    property_create = PropertyCreate(
        name="tte_customer_secondary_phone",
        label="10to8 Customer Secondary Phone Numbers",
        type="string",
        field_type="textarea",
        group_name="contactinformation",
        options=[],
        hidden=False,
        form_field=True
    )
    try:
        api_response = client.crm.properties.core_api.create(
            object_type="Contacts",
            property_create=property_create
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - core_api.create: {exception}\n")
        raise

    print("Creating 10to8 Customer Secondary Emails field in HubSpot")


def setup_hubspot_sync_status_field():
    """
    Creates a field on Contacts in HubSpot to store the sync status.

    A HubSpot field, 'tte_customer_sync_status' is created to store the
    sync status for a 10to8 Customer record.

    Deletes any existing field before creating the field with the correct
    attributes.
    """
    print("Creating 10to8 Customer Sync Status field in HubSpot")
    try:
        api_response = client.crm.properties.core_api.archive(
            object_type="Contacts",
            property_name="tte_customer_sync_status"
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - core_api.archive: {exception}\n")

    property_create = PropertyCreate(
        name="tte_customer_sync_status",
        label="10to8 Customer Sync Status",
        type="string",
        field_type="text",
        group_name="contactinformation",
        options=[],
        hidden=False,
        form_field=True
    )
    try:
        api_response = client.crm.properties.core_api.create(
            object_type="Contacts",
            property_create=property_create
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - core_api.create: {exception}\n")
        raise

    print("Creating 10to8 Customer Sync Status field in HubSpot")


def setup():
    """
    Setup Subscriptions and fields in HubSpot and Subscriptions in 10to8.

    Removes old Subscriptions and fields from HubSpot before setting up
    new HubSpot Subscriptions and fields.
    Removes old 10to8 Subscription before setting up new Subscription.
    """
    setup_hubspot_contact_uri_field()
    setup_hubspot_secondary_emails_field()
    setup_hubspot_secondary_phone_numbers_field()
    setup_hubspot_sync_status_field()
    setup_tte_subscriptions()
    setup_hubspot_subscriptions()


if __name__ == '__main__':
    setup()

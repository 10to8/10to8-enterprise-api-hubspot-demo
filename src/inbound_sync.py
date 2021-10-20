"""
Manually sync all Contacts from HubSpot into 10to8.
"""
from requests.exceptions import RequestException
from tte_client import tte_create_customer, tte_update_customer, \
    tte_delete_customer, convert_to_tte_customer_data, \
    block_inbound_sync_for_invalid_fields
from hubspot_client import get_hubspot_contact_page, update_hubspot_contact
from config import TRACK_EXTERNAL_IDS


def inbound_sync_create_customer(tte_customer_data, track_external_ids):
    """
    Creates a new 10to8 Customer.

    :param tte_customer_data: new data from HubSpot converted into the form
        of a 10to8 Customer record. See convert_to_tte_customer_data().
    :param track_external_ids: when True, we write the 10to8 Customer URI
        into the HubSpot Contact in the tte_customer_uri field.
    """
    if "tte_resource_uri" in tte_customer_data:
        print("HubSpot Contact already created in 10to8 Customer - skipping")
        return

    tte_customer_uri = tte_create_customer(**tte_customer_data)
    hubspot_id = tte_customer_data["external_id"]
    if track_external_ids:
        update_hubspot_contact(
            hubspot_id,
            properties={
                "tte_customer_uri": tte_customer_uri,
                "tte_customer_sync_status": tte_customer_data["status"]
            }
        )


def inbound_sync_update_customer(hubspot_contact, tte_customer_data):
    """
    Updates an existing 10to8 Customer.

    :param hubspot_contact: raw HubSpot Contact data.
    :param tte_customer_data: new data from HubSpot converted into the form
        of a 10to8 Customer record. See convert_to_tte_customer_data().
    """
    hubspot_id = tte_customer_data["external_id"]
    tte_customer_data = block_inbound_sync_for_invalid_fields(
        hubspot_contact,
        tte_customer_data
    )
    tte_update_customer(**tte_customer_data)
    update_hubspot_contact(
        hubspot_id,
        properties={"tte_customer_sync_status": tte_customer_data["status"]}
    )


def inbound_sync_page(
    after=None,
    track_external_ids=False,
    sync_deletions=False
):
    """
    Syncs a page Contacts from a HubSpot account into a 10to8 Organisation.

    When sync_deletions is False:
    * Creates new Customers in 10to8 for previously untracked Contacts.
    * Updates existing Customers in 10to8 for previously tracked Contacts.

    When sync_deletions is True:
    * Archived HubSpot Contacts are deleted from 10to8 if tracked before.

    :param after: the cursor into the HubSpot Contact list.
    :param track_external_ids: enables tracking of identity in external system.
    :param sync_deletions: when True, loads list of archived Contacts to sync
        deletions into 10to8; when False, loads list of Contacts to sync
        non-archived Contacts into 10to8.

    :returns: the cursor to the next page of HubSpot Contacts;
        None when there are no futher pages.
    """
    print("Syncing a page of Contacts from HubSpot:")
    page, after = get_hubspot_contact_page(
        after=after,
        sync_deletions=sync_deletions
    )

    for hubspot_contact in page:
        try:
            tte_customer_data = convert_to_tte_customer_data(
                hubspot_contact.properties
            )
            hubspot_id = tte_customer_data["external_id"]
            if hubspot_contact.archived:
                if "tte_resource_uri" in tte_customer_data:
                    # Note: we're forcing deletions even if the Customer has
                    # future Events booked in 10to8.

                    # To build a system that allows the user to intervene
                    # when a Customer has future Events, set force=False
                    # and handle the 409 conflict error.

                    # See https://10to8.com/api/enterprise/v2/#operation/delete-api-enterprise-v2-customer-id
                    # for more about deletion and conflicts.
                    tte_delete_customer(
                        tte_customer_data["tte_resource_uri"],
                        force=True
                    )
                else:
                    # HubSpot Contact with no connection to 10to8 is deleted:
                    # - can safely ignore this.
                    print("Skipped archived HubSpot Contact {}, no 10to8 URI")
            else:
                if "tte_resource_uri" not in tte_customer_data:
                    inbound_sync_create_customer(
                        tte_customer_data,
                        track_external_ids
                    )
                else:
                    inbound_sync_update_customer(
                        hubspot_contact.properties,
                        tte_customer_data
                    )

        except RequestException as exception:
            print(f"Skipping HubSpot Contact id {hubspot_id}:"
                  f" Exception: {exception}")
    return after


def inbound_sync(track_external_ids, sync_deletions):
    """
    Syncs all Contacts from a HubSpot account into a 10to8 Organisation.

    :param track_external_ids: when True, enables logging of the external id
        on the Customer record in 10to8 and the 10to8 Customer URI on the
        HubSpot Contact.
    :param sync_deletions: when True, loads the list of archived Contacts
        from HubSpot and deletes them from 10to8 if previously tracked.
        When False, loads the list of new and existing Contacts from Hubspot,
        and performs a sync into 10to8.
    """
    after = inbound_sync_page(
        track_external_ids=track_external_ids,
        sync_deletions=sync_deletions
    )

    while after:
        after = inbound_sync_page(
            after=after,
            track_external_ids=track_external_ids,
            sync_deletions=sync_deletions
        )


def inbound_sync_all(track_external_ids=True):
    """
    Syncs all Contacts from a HubSpot account into a 10to8 Organisation.

    * Creates new Customers in 10to8 for previously untracked Contacts.
    * Updates existing Customers in 10to8 for previously tracked Contacts.
    * Archived HubSpot Contacts are deleted from 10to8 if tracked before.

    :param track_external_ids: When True, tracks the HubSpot Contact ID on
        the 10to8 Customer record and the 10to8 Customer Resource URI on
        the Contact in HubSpot. When False, no tracking of external ids
        is performed.

    To sync Contacts from HubSpot into 10to8, set track_external_ids to True.
    For a one-off import without tracking, set track_external_ids to False.
    """
    inbound_sync(track_external_ids, sync_deletions=False)
    inbound_sync(track_external_ids, sync_deletions=True)


if __name__ == '__main__':
    inbound_sync_all(track_external_ids=TRACK_EXTERNAL_IDS)

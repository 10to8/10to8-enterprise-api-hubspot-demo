"""
Manually sync all Customers from 10to8 into HubSpot.
"""
from tte_client import tte_get_customer_page, tte_update_customer, \
    get_hubspot_ids
from hubspot_client import convert_to_hubspot_data, \
    create_hubspot_contact, update_hubspot_contact, \
    delete_hubspot_contact, block_outbound_sync_for_invalid_fields
from config import TRACK_EXTERNAL_IDS


def outbound_sync_page(
    page_url=None,
    track_external_ids=False,
    include_deletions=False
):
    """
    Syncs a page of Customers from a 10to8 Organisation into a HubSpot account.

    :param page_url: URL for the page of 10to8 Customers to sync, or None to
        start syncing the first page.
    :param track_external_ids: when True, enables logging of the external id
        on the 10to8 Customer record.
    :param include_deletions: when True, performs deletions in the sync;

    :returns: URL for the next page of 10to8 Customers to sync,
        or None if there are no further pages to sync.
    """
    page = tte_get_customer_page(page_url, deleted=include_deletions)
    tte_customer_data = page["results"]
    next_page = page["next"]

    if page["results"] is None or len(page["results"]) == 0:
        return None

    for tte_customer in tte_customer_data:
        if "deleted" in tte_customer and tte_customer["deleted"]:
            delete_hubspot_contact(tte_customer["resource_uri"])
        else:
            hubspot_contact_data = convert_to_hubspot_data(tte_customer)
            hubspot_ids = get_hubspot_ids(tte_customer)

            if hubspot_ids is None or len(hubspot_ids) != 1:
                hubspot_contact_data = block_outbound_sync_for_invalid_fields(
                    hubspot_contact_data
                )
                hubspot_id = create_hubspot_contact(
                    properties=hubspot_contact_data
                )
                tte_update_customer(
                    tte_resource_uri=tte_customer["resource_uri"],
                    external_id=hubspot_id if track_external_ids else None,
                    status=hubspot_contact_data["tte_customer_sync_status"]
                )
            else:
                hubspot_contact_data = block_outbound_sync_for_invalid_fields(
                    hubspot_contact_data
                )
                update_hubspot_contact(
                    hubspot_ids[0],
                    properties=hubspot_contact_data
                )
                tte_update_customer(
                    tte_resource_uri=tte_customer["resource_uri"],
                    status=hubspot_contact_data["tte_customer_sync_status"]
                )
    return next_page


def outbound_sync(track_external_ids, include_deletions):
    """
    Syncs all Customers from a 10to8 Organisation into a HubSpot account.

    :param track_external_ids: when True, enables logging of the external id
        on the 10to8 Customer record.
    :param include_deletions: when True, performs deletions in the sync
    """
    next_page = outbound_sync_page(
        track_external_ids=track_external_ids,
        include_deletions=include_deletions
    )

    while next_page:
        next_page = outbound_sync_page(
            page_url=next_page,
            track_external_ids=track_external_ids,
            include_deletions=include_deletions
        )


def outbound_sync_all(track_external_ids=True):
    """
    Syncs all Customers from a 10to8 Organisation into a HubSpot account.

    * Creates new Contacts in HubSpot for previously untracked Customers.
    * Updates existing Contacts in HubSpot for previously tracked Customers.
    * Archives HubSpot Contacts deleted from 10to8 if tracked before.

    :param track_external_ids: when True, write the HubSpot Contact ID on
        the 10to8 Customer record.

    To maintain a sync of Customers from 10to8 into HubSpot,
    set track_external_ids to True.

    For a one-off import without tracking, set track_external_ids to False.
    """
    outbound_sync(track_external_ids, include_deletions=True)


if __name__ == '__main__':
    outbound_sync_all(track_external_ids=TRACK_EXTERNAL_IDS)

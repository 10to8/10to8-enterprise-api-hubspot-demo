"""
Registers to receive callbacks when Contacts are updated in HubSpot.
"""
from pprint import pprint

import hubspot
from hubspot.webhooks import SubscriptionCreateRequest, \
    SettingsChangeRequest, ApiException

from hubspot_subscriptions import get_subscription_url
from config import HUBSPOT_DEVELOPER_API_KEY, HUBSPOT_APP_ID, \
    HUBSPOT_SUBSCRIPTIONS


dev_client = hubspot.Client.create(api_key=HUBSPOT_DEVELOPER_API_KEY)


def configure_webhooks(callback_url):
    """
    Set the target URL and concurrency limit for Webhooks from HubSpot.

    Clears the old target URL from the HubSpot App's settings, and sets up
    this new callback.

    :param callback_url: URL for our HubSpot App's Webhook callback.
    """
    throttling = {
        "period": "SECONDLY",
        "maxConcurrentRequests": 10
    }
    settings_change_request = SettingsChangeRequest(
        target_url=callback_url,
        throttling=throttling
    )
    try:
        # pragma pylint: disable=E1101
        api_response = dev_client.webhooks.settings_api.clear(
            app_id=HUBSPOT_APP_ID
        )
        pprint(api_response)
        api_response = dev_client.webhooks.settings_api.configure(
            app_id=HUBSPOT_APP_ID,
            settings_change_request=settings_change_request
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - settings_api.configure: {exception}\n")


def register_hubspot_subscription(
    event_type,
    property_name=None
):
    """
    Registers to receive a Webhook for from HubSpot.

    :param event_type: HubSpot Webhook event type.
    :param property_name: Name of property on HubSpot Contact.
    """
    print(f"Registering HubSpot subscriptions"
          f"for {event_type}, {property_name}")
    try:
        contact_creation_request = SubscriptionCreateRequest(
            event_type=event_type,
            property_name=property_name,
            active=True
        )
        # pragma pylint: disable=E1101,E1120
        api_response = dev_client.webhooks.subscriptions_api.create(
            app_id=HUBSPOT_APP_ID,
            subscription_create_request=contact_creation_request
        )
        pprint(api_response)
    except ApiException as exception:
        print(f"Exception - subscriptions_api.create: {exception}\n")

    print(f"Registered HubSpot subscriptions"
          f"for {event_type}, {property_name}")


def register_hubspot_subscriptions(callback_url):
    """
    Registers to receive callbacks from HubSpot specified in config.py.

    Subscriptions are defined in HUBSPOT_SUBSCRIPTIONS in config.py.
    """
    print(f"Registering HubSpot subscriptions with url: {callback_url}")
    configure_webhooks(callback_url)

    for event_type, property_names in HUBSPOT_SUBSCRIPTIONS.items():
        if len(property_names) > 0:
            for property_name in property_names:
                register_hubspot_subscription(
                    event_type,
                    property_name=property_name
                )
        else:
            register_hubspot_subscription(
                event_type
            )

    print(f"Registered HubSpot subscriptions with url: {callback_url}")


def get_subscription_ids():
    """
    Returns a list of all the HubSpot subscription ids on our HubSpot App.
    """
    try:
        # pragma pylint: disable=E1101
        api_response = dev_client.webhooks.subscriptions_api.get_all(
            app_id=HUBSPOT_APP_ID
        )
        pprint(api_response)
        return [result.id for result in api_response.results]
    except ApiException as exception:
        print(f"Exception - subscriptions_api.get_all: {exception}\n")
        raise


def remove_old_subscriptions():
    """
    Removes all existing HubSpot subscriptions from our HubSpot App.

    Our HubSpot App is identified by the HUBSPOT_APP_ID in config.py.
    """
    for subscription_id in get_subscription_ids():
        try:
            # pragma pylint: disable=E1101,E1120
            api_response = dev_client.webhooks.subscriptions_api.archive(
                subscription_id=subscription_id,
                app_id=HUBSPOT_APP_ID
            )
            pprint(api_response)
        except ApiException as exception:
            print(f"Exception - subscriptions_api.archive: {exception}\n")
            raise


def setup_hubspot_subscriptions():
    """
    Configures Webhooks for Contact updates on our HubSpot App.

    Removes all existing subscriptions, and registers a subscription for
    Contact updates to be sent to our integration from HubSpot.
    """
    remove_old_subscriptions()
    register_hubspot_subscriptions(get_subscription_url())


if __name__ == '__main__':
    setup_hubspot_subscriptions()

"""
Registers to receive callbacks when customers are updated in 10to8.
"""
from tte_client import register_subscription, delete_old_subscriptions
from tte_subscriptions import get_subscription_url


def setup_tte_subscriptions():
    """
    Prepares a 10to8 Organisation to send Subscription Notifications.

    Removes all existing Subscriptions, and registers a Subscription for
    Customer updates to be sent to our integration from 10to8.
    """
    delete_old_subscriptions()
    webhook_url = get_subscription_url()
    register_subscription(webhook_url)


if __name__ == '__main__':
    setup_tte_subscriptions()

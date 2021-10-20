"""
Flask server enabling live sync and HubSpot App Installation.

Launch this server to enable live bi-directional syncing between
10to8 and HubSpot, and to facilitate the HubSpot App Installation.
"""
from flask import Flask
import hubspot_subscriptions
import tte_subscriptions

app = Flask(__name__)


app.add_url_rule(
    hubspot_subscriptions.SUBSCRIPTION_ROUTE,
    view_func=hubspot_subscriptions.hubspot_webhook,
    methods=["POST"]
)

app.add_url_rule(
    hubspot_subscriptions.START_INSTALL_ROUTE,
    view_func=hubspot_subscriptions.start_install
)

app.add_url_rule(
    hubspot_subscriptions.INSTALL_ROUTE,
    view_func=hubspot_subscriptions.install_app
)

app.add_url_rule(
    tte_subscriptions.SUBSCRIPTION_ROUTE,
    view_func=tte_subscriptions.customer_webhook,
    methods=["POST"]
)

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)

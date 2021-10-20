"""
Config settings used to connect to 10to8 and HubSpot.
"""

# WEBHOOK HOST - use https URL from ngrok using: ngrok http 5000
WEBHOOK_HOST = ""

# To obtain your enterprise API key, see:
#  https://10to8.com/api/enterprise/v2/#section/Authentication
TTE_ENTERPRISE_API_KEY = ""

# HubSpot API key - open the following from your hubspot test account:
#  Settings > Integrations > API Key
# https://knowledge.hubspot.com/integrations/how-do-i-get-my-hubspot-api-key
HUBSPOT_API_KEY = ""

# HubSpot App details - from your hubspot developer account:
#  Manage apps > "your app" > Basic Info > Auth
# https://legacydocs.hubspot.com/docs/faq/how-do-i-create-an-app-in-hubspot
HUBSPOT_APP_ID = ""
HUBSPOT_CLIENT_ID = ""
HUBSPOT_CLIENT_SECRET = ""
HUBSPOT_SCOPES = "crm.objects.contacts.write crm.objects.contacts.read oauth"
# HUBSPOT_SCOPES = "contacts" # Use this if the scopes above do not work

# HubSpot developer API Key - from your hubspot developer account:
# Manage apps > Get HubSpot API key
#  https://legacydocs.hubspot.com/docs/faq/developer-api-keys
HUBSPOT_DEVELOPER_API_KEY = ""

# Default settings - leave these alone
TTE_HOST = "https://10to8.com"

# List of HubSpot Subscriptions to register.
#  A dictionary of HubSpot events -> HubSpot properties.
HUBSPOT_SUBSCRIPTIONS = {
    "contact.creation": [],
    "contact.deletion": [],
    "contact.propertyChange": [
        "firstname",
        "lastname",
        "email",
        "phone",
        "tte_customer_secondary_emails",
        "tte_customer_secondary_phone"
    ]
}

# Track Existing Ids:
#  - log the external id against the record in the other system
TRACK_EXTERNAL_IDS = True

# Import all common settings.
from biostar.settings import *

# Additional apps enabled.
INSTALLED_APPS += [
    'biostar.accounts.apps.MessageConfig'
]

# The url specification.
ROOT_URLCONF = 'biostar.message.urls'



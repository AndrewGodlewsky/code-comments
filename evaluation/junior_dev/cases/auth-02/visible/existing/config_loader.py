# app/config_loader.py
# Loads config/app.yaml once, the first time this module is imported.
# Every other module does `from app.config_loader import settings`.
# Nothing re-reads the file: changing a value means a new image and a redeploy.
import os

import yaml

_CONFIG_PATH = os.environ.get('APP_CONFIG', 'config/app.yaml')


def _load(path):
    with open(path) as f:
        return yaml.safe_load(f)


settings = _load(_CONFIG_PATH)


# --- How a provider client uses it today (app/clients/payments.py) ---
#
# from app.config_loader import settings
#
# class PaymentsClient:
#     def __init__(self):
#         # the key is copied into the client once, at construction
#         self._key = settings['payments']['api_key']
#         self._base = settings['payments']['base_url']
#
#     def charge(self, order):
#         return http.post(self._base + '/charges',
#                          headers={'Authorization': 'Bearer ' + self._key},
#                          json=order.to_charge())
#
# payments = PaymentsClient()   # module-level singleton, built at import
#
# app/clients/email.py (EmailClient) and app/clients/geocoding.py
# (GeocodingClient) follow the same pattern.

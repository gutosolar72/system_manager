# app/integrations/asaas/client.py

import requests
from app.integrations.asaas.config import get_asaas_config


class AsaasClient:
    """
    Cliente HTTP para comunicação com a API do Asaas
    """

    def __init__(self):
        config = get_asaas_config()
        self.base_url = config['base_url']
        self.api_key = config['api_key']

        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_key
        }

    def get(self, endpoint, params=None):
        response = requests.get(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            params=params
        )
        self._handle_response(response)
        return response.json()

    def post(self, endpoint, payload):
        response = requests.post(
            f"{self.base_url}{endpoint}",
            headers=self.headers,
            json=payload,
            timeout=10
        )
        self._handle_response(response)
        return response.json()

    def _handle_response(self, response):
        if response.status_code >= 400:
            raise Exception(
                f"Asaas API Error {response.status_code}: {response.text}"
            )


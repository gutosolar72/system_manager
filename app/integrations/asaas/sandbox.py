# app/integrations/asaas/sandbox.py

"""
Asaas Sandbox Utilities
======================

Ferramentas EXCLUSIVAS para ambiente sandbox.
Nunca usar em produção.
"""

from app.integrations.asaas.client import AsaasClient
from app.integrations.asaas.config import ASAAS_ENV


class AsaasSandboxService:

    def __init__(self):
        if ASAAS_ENV != 'sandbox':
            raise RuntimeError(
                'AsaasSandboxService só pode ser usado em sandbox'
            )

        self.client = AsaasClient()

    def simulate_payment(self, gateway_payment_id, value=None):
        """
        Simula o pagamento de um boleto no Asaas (sandbox)

        gateway_payment_id: ID do payment no Asaas
        value: opcional (se não enviar, usa o valor original)
        """

        payload = {}
        if value:
            payload['value'] = float(value)

        return self.client.post(
            f'/payments/{gateway_payment_id}/receive',
            payload
        )


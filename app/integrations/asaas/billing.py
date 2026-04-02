# app/integrations/asaas/billing.py

"""
Asaas Billing Service
====================

Responsável por:
- Criar cobranças no Asaas (boleto)
- Trabalhar APENAS com dados já normalizados
- NÃO acessar banco
- NÃO conter regras de negócio do sistema

Entrada: dados do domínio
Saída: resposta bruta do Asaas
"""

from app.integrations.asaas.client import AsaasClient
from app.integrations.asaas.mapper import map_boleto_payload

class AsaasBillingService:

    def __init__(self):
        self.client = AsaasClient()

    def create_boleto(self, cliente, contrato, historico_pagamento):
        """
        Cria uma cobrança por boleto no Asaas

        Pré-requisitos (responsabilidade de quem chama):
        - cliente já possui gateway_customer_id
        - historico_pagamento já possui data_vencimento e valor

        Retorna:
        - payload bruto da API do Asaas
        """

        payload = map_boleto_payload(
            cliente=cliente,
            contrato=contrato,
            historico_pagamento=historico_pagamento
        )

        return self.client.post('/payments', payload)


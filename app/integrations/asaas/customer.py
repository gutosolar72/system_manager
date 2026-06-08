# app/integrations/asaas/customer.py

"""
Asaas Customer Service
=====================

Responsável por criar e buscar clientes (customers)
no Asaas.
"""

from app.integrations.asaas.client import AsaasClient
import re


class AsaasCustomerService:

    def __init__(self):
        self.client = AsaasClient()

    def create_customer(self, cliente):
        """
        Cria um customer no Asaas a partir do cliente interno
        """
        telefone_completo = re.sub(r'\D', '', f"{cliente.ddd}{cliente.telefone}")

        payload = {
            "name": cliente.nome_empresa,
            "email": re.split(r'[;,\s]+', cliente.email.strip())[0] if cliente.email else None,
            "cpfCnpj": cliente.cnpj,
            "phone": telefone_completo,
            "mobilePhone": telefone_completo,
            "address": cliente.logradouro,
            "addressNumber": cliente.numero,
            "complement": cliente.complemento,
            "province": cliente.bairro,
            "postalCode": cliente.cep,
            "city": cliente.cidade,
            "state": cliente.estado,
            "notificationDisabled": True
        }

        return self.client.post('/customers', payload)

    def find_customer_by_cpf_cnpj(self, cpf_cnpj):
        """
        Busca customer no Asaas pelo CPF/CNPJ
        """

        response = self.client.get(
            '/customers',
            params={'cpfCnpj': cpf_cnpj}
        )

        data = response.get('data', [])
        return data[0] if data else None


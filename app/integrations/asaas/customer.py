# app/integrations/asaas/customer.py

"""
Asaas Customer Service
=====================

Responsável por criar e buscar clientes (customers)
no Asaas.
"""

from app.integrations.asaas.client import AsaasClient


class AsaasCustomerService:

    def __init__(self):
        self.client = AsaasClient()

    def create_customer(self, cliente):
        """
        Cria um customer no Asaas a partir do cliente interno
        """

        payload = {
            "name": cliente.nome_empresa,
            "email": cliente.email,
            "cpfCnpj": cliente.cnpj,
            "phone": cliente.telefone,
            "mobilePhone": cliente.telefone,
            "address": cliente.logradouro,
            "addressNumber": cliente.numero,
            "complement": cliente.complemento,
            "province": cliente.bairro,
            "postalCode": cliente.cep,
            "city": cliente.cidade,
            "state": cliente.estado
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


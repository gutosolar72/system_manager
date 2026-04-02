import sys
import os
from datetime import date

# Ajuste de path (necessário para seus imports atuais)
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'integrations'))

from app import create_app
from app.integrations.asaas.billing import AsaasBillingService
from app.integrations.asaas.customer import AsaasCustomerService
from app.models import ClienteGateway, HistoricoPagamentos
from app.integrations.asaas.mapper import map_payment_response_to_historico
from app.extensions import db


# Inicializa app Flask
app = create_app()

with app.app_context():
    registro = ClienteGateway.query.filter_by(
        cliente_id=11,
        gateway='asaas',
        ambiente='sandbox'
    ).first()

    print("\n=== CUSTOMER NO BANCO ===")
    print(registro.gateway_customer_id if registro else "NÃO ENCONTRADO")


# Service
service = AsaasCustomerService()

# Cliente fake
cliente_fake = type('obj', (object,), {
    "nome_empresa": "Teste LTDA",
    "email": "teste@email.com",
    "cnpj": "26172693000193",
    "telefone": "14997540671",
    "logradouro": "Rua Teste",
    "numero": "123",
    "complemento": "",
    "bairro": "Centro",
    "cep": "19900000",
    "cidade": "Ourinhos",
    "estado": "SP"
})()


# Histórico fake
historico_fake = type('obj', (object,), {
    "valor_pago": 100.00,
    "data_vencimento": date(2026, 4, 10),
    "periodo_referencia_inicio": date(2026, 4, 1),
    "licenca_id": 1
})()


# Regra correta: usar ou criar customer
if registro:
    print("\n=== USANDO CUSTOMER EXISTENTE ===")
    print(registro.gateway_customer_id)

    cliente_fake.asaas_customer_id = registro.gateway_customer_id

else:
    print("\n=== CRIANDO NOVO CUSTOMER ===")
    response = service.create_customer(cliente_fake)
    print(response)

    # Injeta o ID retornado (caso crie novo)
    cliente_fake.asaas_customer_id = response.get("id")


# Criar boleto
billing = AsaasBillingService()

response = billing.create_boleto(
    cliente=cliente_fake,
    contrato=type('obj', (object,), {"id": 1})(),
    historico_pagamento=historico_fake
)

print("\n=== BOLETO CRIADO ===")
print(response)

with app.app_context():
    dados = map_payment_response_to_historico(response)

    historico = HistoricoPagamentos(
        gateway='asaas',
        gateway_payment_id=dados.get("gateway_payment_id"),
        linha_digitavel=dados.get("linha_digitavel"),
        nosso_numero=dados.get("nosso_numero"),
        codigo_banco=dados.get("codigo_banco"),
        status_boleto=dados.get("status_boleto"),
        data_emissao=dados.get("data_emissao"),
        data_vencimento=dados.get("data_vencimento"),

        # dados obrigatórios mínimos
        licenca_id=73,
        contrato_id=65,
        valor_pago=historico_fake.valor_pago,
        periodo_referencia_inicio=historico_fake.periodo_referencia_inicio,
        periodo_referencia_fim=historico_fake.periodo_referencia_inicio
    )

    db.session.add(historico)
    db.session.commit()

    print("\n=== SALVO NO BANCO ===")
    print(f"ID: {historico.id} | Payment: {historico.gateway_payment_id}")

from app.integrations.asaas.customer import AsaasCustomerService
from app.integrations.asaas.billing import AsaasBillingService
from app.integrations.asaas.mapper import map_payment_response_to_historico
from app.models import ClienteGateway
from app.extensions import db


def gerar_cobranca_asaas(pagamento):
    contrato = pagamento.contrato
    cliente = contrato.cliente

    # --- 1. Verifica ou cria customer
    registro = ClienteGateway.query.filter_by(
        cliente_id=cliente.id,
        gateway='asaas',
        ambiente='sandbox'
    ).first()

    if registro:
        cliente.asaas_customer_id = registro.gateway_customer_id
    else:
        customer_service = AsaasCustomerService()
        response = customer_service.create_customer(cliente)

        gateway_id = response.get("id")

        novo = ClienteGateway(
            cliente_id=cliente.id,
            gateway='asaas',
            ambiente='sandbox',
            gateway_customer_id=gateway_id,
            gateway_payload=response
        )

        db.session.add(novo)
        db.session.commit()

        cliente.asaas_customer_id = gateway_id

    # --- 2. Criar cobrança
    billing_service = AsaasBillingService()

    response = billing_service.create_boleto(
        cliente=cliente,
        contrato=contrato,
        historico_pagamento=pagamento
    )

    # --- 3. Mapear retorno
    dados = map_payment_response_to_historico(response)

    pagamento.gateway = 'asaas'
    pagamento.gateway_payment_id = dados.get("gateway_payment_id")
    pagamento.linha_digitavel = dados.get("linha_digitavel")
    pagamento.nosso_numero = dados.get("nosso_numero")
    pagamento.codigo_banco = dados.get("codigo_banco")
    pagamento.status_boleto = dados.get("status_boleto")
    pagamento.data_emissao = dados.get("data_emissao")
    pagamento.data_vencimento = dados.get("data_vencimento")
    pagamento.gateway_payload = response

    db.session.commit()

    return pagamento

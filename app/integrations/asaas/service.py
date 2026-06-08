from datetime import date, datetime
from app.integrations.asaas.customer import AsaasCustomerService
from app.integrations.asaas.billing import AsaasBillingService
from app.integrations.asaas.mapper import map_payment_response_to_historico
from app.integrations.asaas.config import ASAAS_ENV
from app.models import ClienteGateway
from app.extensions import db

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def criar_nf_asaas(pagamento, descricao=None, data_emissao=None):
    """
    Agenda e autoriza NFS-e no Asaas para um HistoricoPagamentos que já tem gateway_payment_id.
    Preenche os campos nf_* do objeto pagamento, mas NÃO faz commit.
    """
    from app.integrations.asaas.client import AsaasClient

    if not pagamento.gateway_payment_id:
        raise ValueError(
            "pagamento.gateway_payment_id não definido — "
            "a cobrança Asaas precisa existir antes de emitir a NF."
        )

    # Descrição automática pelo período de referência
    if not descricao:
        if pagamento.periodo_referencia_inicio:
            mes = f"{MESES_PT[pagamento.periodo_referencia_inicio.month]}/{pagamento.periodo_referencia_inicio.year}"
            descricao = f"Serviços de suporte técnico referente ao mês de {mes}."
        else:
            descricao = "Prestação de serviços de suporte técnico."

    effective_date = data_emissao or date.today().isoformat()

    payload = {
        "payment": pagamento.gateway_payment_id,
        "serviceDescription": descricao,
        "value": float(pagamento.valor_pago),
        "effectiveDate": effective_date,
        "municipalServiceCode": "14.02.01",
        "municipalServiceName": "Assistência técnica",
        "observations": f"Manutenção e suporte técnico referente ao mês de {mes}.",
        "taxes": {
            "retainIss": False,
            "iss": 0,
            "pis": 0,
            "cofins": 0,
            "csll": 0,
            "inss": 0,
            "ir": 0
        }
    }

    client = AsaasClient()
    response = client.post("/invoices", payload)

    if response.get("id"):
        pagamento.nf_id          = response.get("id")
        pagamento.nf_status      = response.get("status")
        pagamento.nf_pdf_url     = response.get("pdfUrl")
        pagamento.nf_xml_url     = response.get("xmlUrl")
        pagamento.nf_emitida_em  = datetime.utcnow()
        pagamento.gateway_invoice_id = response.get("id")
        print(f"📄 NF agendada: {pagamento.nf_id} | status: {pagamento.nf_status}")

        # --- Autoriza (emite) imediatamente
        nf_id = response.get("id")
        authorize_response = client.post(f"/invoices/{nf_id}/authorize", {})

        pagamento.nf_status = authorize_response.get("status", pagamento.nf_status)

        if authorize_response.get("status") in ("AUTHORIZED", "SCHEDULED"):
            print(f"✅ NF autorizada: {nf_id} | status: {pagamento.nf_status}")
        else:
            erros = authorize_response.get("errors", [])
            print(f"⚠️  Autorização pendente para {nf_id}: {erros}")
    else:
        erros = response.get("errors", [])
        print(f"⚠️  NF não agendada para {pagamento.gateway_payment_id}: {erros}")

    return response


def gerar_cobranca_asaas(pagamento):
    contrato = pagamento.contrato
    cliente = contrato.cliente

    # --- 1. Verifica ou cria customer no Asaas
    registro = ClienteGateway.query.filter_by(
        cliente_id=cliente.id,
        gateway='asaas',
        ambiente=ASAAS_ENV
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
            ambiente=ASAAS_ENV,
            gateway_customer_id=gateway_id,
            gateway_payload=response
        )
        db.session.add(novo)
        db.session.commit()
        cliente.asaas_customer_id = gateway_id

    # --- 2. Criar boleto
    billing_service = AsaasBillingService()
    response = billing_service.create_boleto(
        cliente=cliente,
        contrato=contrato,
        historico_pagamento=pagamento
    )

    # --- 3. Mapear retorno nos campos do pagamento
    dados = map_payment_response_to_historico(response)
    pagamento.gateway            = 'asaas'
    pagamento.gateway_payment_id = dados.get("gateway_payment_id")
    pagamento.linha_digitavel    = dados.get("linha_digitavel")
    pagamento.nosso_numero       = dados.get("nosso_numero")
    pagamento.codigo_banco       = dados.get("codigo_banco")
    pagamento.status_boleto      = dados.get("status_boleto")
    pagamento.data_emissao       = dados.get("data_emissao")
    pagamento.data_vencimento    = dados.get("data_vencimento")
    pagamento.gateway_payload    = response

    return pagamento

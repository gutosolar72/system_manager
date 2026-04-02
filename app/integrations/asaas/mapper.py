# app/services/asaas_mapper.py

"""
Asaas Mapper
============

Responsável por traduzir dados entre:
- API do Asaas
- Domínio interno do System Manager

Este arquivo NÃO:
- faz chamadas HTTP
- acessa banco
- executa regras de negócio

Ele apenas converte estruturas e normaliza dados.
"""

from datetime import datetime


# ======================================================
# STATUS
# ======================================================

# Status vindos do Asaas → status interno
ASAAS_TO_LOCAL_STATUS = {
    'PENDING': 'pendente',
    'RECEIVED': 'pago',
    'CONFIRMED': 'pago',
    'OVERDUE': 'pendente',
    'CANCELED': 'cancelado',
    'REFUNDED': 'cancelado'
}

# Status interno → status esperado pelo Asaas (uso futuro)
LOCAL_TO_ASAAS_STATUS = {
    'pendente': 'PENDING',
    'emitido': 'PENDING',
    'pago': 'CONFIRMED',
    'cancelado': 'CANCELED'
}


def map_asaas_status(asaas_status):
    """
    Converte status do Asaas para status interno do System Manager
    """
    return ASAAS_TO_LOCAL_STATUS.get(asaas_status, 'erro')


# ======================================================
# PAYLOAD: SYSTEM MANAGER → ASAAS
# ======================================================

def map_boleto_payload(cliente, contrato, historico_pagamento):
    """
    Constrói payload para criação de boleto no Asaas

    Campos do Asaas mapeados:
    - customer        → cliente.asaas_customer_id
    - billingType     → BOLETO
    - value           → valor da cobrança
    - dueDate         → data de vencimento
    - description     → contrato / licença / período
    """

    return {
        "customer": cliente.asaas_customer_id,
        "billingType": "BOLETO",
        "value": float(historico_pagamento.valor_pago),
        "dueDate": historico_pagamento.data_vencimento.strftime('%Y-%m-%d'),
        "description": (
            f"Contrato #{contrato.id} | "
            f"Licença #{historico_pagamento.licenca_id} | "
            f"Período {historico_pagamento.periodo_referencia_inicio:%m/%Y}"
        )
    }


# ======================================================
# RESPONSE: ASAAS → HISTORICO_PAGAMENTOS
# ======================================================

def map_payment_response_to_historico(asaas_payment):
    """
    Converte resposta da API do Asaas em dados compatíveis
    com a tabela historico_pagamentos (agnóstica de gateway)

    Mapeamento:
    Asaas                    → System Manager
    ------------------------------------------------
    id                        → gateway_payment_id
    payload bruto             → gateway_payload
    lineBarcode               → linha_digitavel
    nossoNumero               → nosso_numero
    bankSlip.bankCode         → codigo_banco
    status                    → status_boleto
    dateCreated               → data_emissao
    dueDate                   → data_vencimento
    """

    bank_slip = asaas_payment.get("bankSlip", {})

    return {
        "gateway": "asaas",
        "gateway_payment_id": asaas_payment.get("id"),
        "gateway_payload": asaas_payment,

        "linha_digitavel": asaas_payment.get("lineBarcode"),
        "nosso_numero": asaas_payment.get("nossoNumero"),
        "codigo_banco": bank_slip.get("bankCode"),

        "status_boleto": map_asaas_status(asaas_payment.get("status")),
        "data_emissao": parse_date(asaas_payment.get("dateCreated")),
        "data_vencimento": parse_date(asaas_payment.get("dueDate"))
    }


# ======================================================
# WEBHOOK: ASAAS → SYSTEM MANAGER
# ======================================================

def map_webhook_event(payload):
    """
    Normaliza payload de webhook do Asaas

    Retorna apenas os dados relevantes para atualização
    do histórico de pagamentos
    """

    payment = payload.get("payment", {})

    return {
        "gateway": "asaas",
        "gateway_payment_id": payment.get("id"),
        "gateway_payload": payload,

        "status_boleto": map_asaas_status(payment.get("status")),
        "data_pagamento": parse_date(
            payment.get("paymentDate") or payment.get("confirmedDate")
        ),
        "data_credito": parse_date(payment.get("creditDate"))
    }


# ======================================================
# HELPERS
# ======================================================

def parse_date(date_str):
    """
    Converte datas do Asaas (YYYY-MM-DD ou ISO)
    para objeto date do Python
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return None


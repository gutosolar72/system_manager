# app/services/gerar_boletos_pagbank.py
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models import HistoricoPagamentos, Contrato, Licenca
from app.extensions import db

# --- Carrega credenciais
cred_path = Path(__file__).parent / "credentials" / "pagseguro.json"
with open(cred_path, "r") as f:
    creds = json.load(f)

PAGBANK_ORDER_URL = creds["PAGBANK_ORDER_URL"]
TOKEN = creds["PAGBANK_TOKEN"]

status_map = {
    "WAITING": "pendente",
    "PAID": "pago",
    "CANCELED": "cancelado",
    "AUTHORIZED": "pago",
    "DECLINED": "cancelado",
    "EXPIRED": "cancelado",
    "FAILED": "cancelado"
}


def gerar_boleto_pagbank(pagamento_id):
    """Gera boleto no PagBank usando dados do pagamento no banco"""
    pagamento = HistoricoPagamentos.query.get(pagamento_id)
    if not pagamento:
        print(f"Pagamento {pagamento_id} não encontrado")
        return None

    contrato = Contrato.query.get(pagamento.contrato_id)
    if not contrato:
        print(f"Contrato {pagamento.contrato_id} não encontrado")
        return None

    licenca = Licenca.query.get(pagamento.licenca_id)
    if not licenca:
        print(f"Licença {pagamento.licenca_id} não encontrada")
        return None

    cliente = contrato.cliente
    if not cliente:
        print(f"Cliente não encontrado para o contrato {contrato.id}")
        return None

    # --- Calcula data de vencimento ---
    hoje = datetime.today().date()
    dia_cobranca = getattr(contrato, "dia_cobranca", None) or 5

    try:
        vencimento = hoje.replace(day=dia_cobranca)
        if vencimento <= hoje:
            vencimento += relativedelta(months=1)
    except ValueError:
        # Ex: mês com menos dias que o dia_cobranca definido
        proximo_mes = hoje + relativedelta(months=1)
        ultimo_dia_mes = (proximo_mes.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
        vencimento = ultimo_dia_mes

    vencimento_str = vencimento.strftime("%Y-%m-%d")

    # --- Dados do cliente ---
    cliente_json = {
        "name": cliente.nome_empresa,
        "email": cliente.email or "",
        "tax_id": (cliente.cnpj or "").replace(".", "").replace("/", "").replace("-", ""),
        "phones": [
            {
                "type": "BUSINESS",
                "country": "55",
                "area": (cliente.ddd or "").replace("-", ""),
                "number": (cliente.telefone or "").replace("-", "").replace(" ", ""),
            }
        ]
    }

    # --- Item ---
    item_json = {
        "reference_id": f"licenca-{licenca.id}",
        "name": f"Assinatura {licenca.produto.nome_produto}",
        "quantity": 1,
        "unit_amount": int(pagamento.valor_pago * 100)
    }

    # --- Payload final ---
    payload = {
        "reference_id": f"fatura-{pagamento.id}-{int(datetime.now().timestamp())}",
        "customer": cliente_json,
        "items": [item_json],
        "shipping": {
            "address": {
                "street": cliente.logradouro or "",
                "number": cliente.numero or "",
                "complement": cliente.complemento or "",
                "locality": cliente.bairro or "",
                "city": cliente.cidade or "",
                "region_code": cliente.estado or "",
                "country": "BRA",
                "postal_code": (cliente.cep or "").replace("-", "")
            }
        },
        "notification_urls": [
            "https://meusite.com/notificacoes"
        ],
        "charges": [
            {
                "reference_id": f"charge-{pagamento.id}-{int(datetime.now().timestamp())}",
                "description": f"Boleto - {item_json['name']}",
                "amount": {
                    "value": item_json["unit_amount"],
                    "currency": "BRL"
                },
                "payment_method": {
                    "type": "BOLETO",
                    "boleto": {
                        "due_date": vencimento_str,
                        "instruction_lines": {
                            "line_1": "Pague até a data de vencimento.",
                            "line_2": "Após vencimento, cobrar multa e juros."
                        },
                        "holder": {
                            "name": cliente.nome_empresa,
                            "tax_id": (cliente.cnpj or "").replace(".", "").replace("/", "").replace("-", ""),
                            "email": cliente.email or "",
                            "address": {
                                "country": "BRA",
                                "region": cliente.cidade,
                                "region_code": cliente.estado,
                                "city": cliente.cidade or "",
                                "postal_code": (cliente.cep or "").replace("-", ""),
                                "street": cliente.logradouro or "",
                                "number": cliente.numero or "",
                                "locality": cliente.bairro or ""
                            }
                        }
                    }
                }
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }

    print(f"\n=== GERANDO BOLETO PARA CONTRATO {contrato.id} ===")
    print(f"➡️  Data de vencimento: {vencimento_str}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        resp = requests.post(PAGBANK_ORDER_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print("❌ Erro ao chamar PagBank:", e)
        if getattr(e, "response", None) is not None:
            print("Resposta:", e.response.text)
        return None

    resultado = resp.json()

    # --- Atualiza pagamento no banco ---
    if resultado.get("charges"):
        charge = resultado["charges"][0]
        status_boleto = status_map.get(charge.get("status", "").upper(), "pendente")
        pagamento.status_boleto = status_boleto
        pagamento.boleto_id = charge.get("id")
        pagamento.data_vencimento = vencimento  # salva vencimento real
        db.session.commit()

    print(f"✅ Boleto gerado com vencimento em {vencimento_str}")
    return resultado


import sys
import os
from datetime import date, datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.extensions import db
from app.models import Contrato, HistoricoPagamentos, ClienteGateway
from app.integrations.asaas.billing import AsaasBillingService
from app.integrations.asaas.mapper import map_payment_response_to_historico


app = create_app()


def primeiro_dia_mes_anterior():
    hoje = date.today()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
    return ultimo_dia_mes_anterior.replace(day=1), ultimo_dia_mes_anterior


def ja_existe_cobranca(contrato_id, inicio, fim):
    return HistoricoPagamentos.query.filter(
        HistoricoPagamentos.contrato_id == contrato_id,
        HistoricoPagamentos.periodo_referencia_inicio == inicio,
        HistoricoPagamentos.periodo_referencia_fim == fim
    ).first() is not None


with app.app_context():

    billing = AsaasBillingService()

    hoje = date.today()

    inicio, fim = primeiro_dia_mes_anterior()

    contratos = Contrato.query.filter_by(status='ativo').all()

    print(f"\nProcessando {len(contratos)} contratos...")

    for contrato in contratos:

        if ja_existe_cobranca(contrato.id, inicio, fim):
            print(f"[SKIP] Contrato {contrato.id} já faturado")
            continue

        try:
            historico = HistoricoPagamentos(
                gateway='asaas',
                licenca_id=contrato.licenca_id,
                contrato_id=contrato.id,
                valor_pago=contrato.valor_mensal,
                periodo_referencia_inicio=inicio,
                periodo_referencia_fim=fim,
                data_vencimento=date(hoje.year, hoje.month, contrato.dia_vencimento_boleto),
                status_boleto='pendente'
            )

            db.session.add(historico)
            db.session.flush()  # gera ID sem commit

            cliente = contrato.cliente

            registro_gateway = ClienteGateway.query.filter_by(
                cliente_id=cliente.id,
                gateway='asaas',
                ambiente='sandbox'
            ).first()

            if not registro_gateway:
                raise Exception(f"Cliente {cliente.id} sem cadastro no Asaas")

            cliente.asaas_customer_id = registro_gateway.gateway_customer_id

            response = billing.create_boleto(
                cliente=cliente,
                contrato=contrato,
                historico_pagamento=historico
            )

            dados = map_payment_response_to_historico(response)

            historico.gateway_payment_id = dados.get("gateway_payment_id")
            historico.linha_digitavel = dados.get("linha_digitavel")
            historico.nosso_numero = dados.get("nosso_numero")
            historico.codigo_banco = dados.get("codigo_banco")
            historico.status_boleto = dados.get("status_boleto")
            historico.data_emissao = dados.get("data_emissao")

            db.session.commit()

            print(f"[OK] Contrato {contrato.id} faturado")

        except Exception as e:
            db.session.rollback()
            print(f"[ERRO] Contrato {contrato.id}: {str(e)}")

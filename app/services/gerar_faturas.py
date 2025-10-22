#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Ajusta path para importar o app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Contrato, Licenca, HistoricoPagamentos
from app.services.gerar_boletos_pagbank import gerar_boleto_pagbank


app = create_app()
app.app_context().push()

def gerar_faturas():
    hoje = datetime.today().date()
    ontem = hoje - timedelta(days=1)
    faturas_criadas = 0

    # --- 1️⃣ Atualiza licenças vencidas ontem para "pendente"
    licencas_vencidas = Licenca.query.filter_by(data_expiracao=ontem).all()
    for licenca in licencas_vencidas:
        licenca.status = "pendente"
    if licencas_vencidas:
        print(f"Licenças pendentes atualizadas: {len(licencas_vencidas)}")

    # --- 2️⃣ Gera faturas para todos os contratos ativos
    contratos = Contrato.query.filter_by(status='ativo').all()

    for contrato in contratos:
        if not contrato.licenca:
            continue

        # Calcula o período de referência (25 até 24 do mês seguinte)
        periodo_inicio = hoje
        periodo_fim = (periodo_inicio + relativedelta(months=1)) - timedelta(days=1)

        # Evita duplicidade de fatura
        existente = HistoricoPagamentos.query.filter_by(
            contrato_id=contrato.id,
            periodo_referencia_inicio=periodo_inicio,
            periodo_referencia_fim=periodo_fim
        ).first()

        if existente:
            print(f"⚠️ Fatura já existente para contrato {contrato.id}")
            continue

        # Cria nova fatura pendente
        pagamento = HistoricoPagamentos(
            licenca_id=contrato.licenca.id,
            contrato_id=contrato.id,
            valor_pago=contrato.valor_mensal,
            data_pagamento=None,
            periodo_referencia_inicio=periodo_inicio,
            periodo_referencia_fim=periodo_fim,
            observacao=f'Fatura gerada automaticamente em {datetime.now()}',
            status_boleto='pendente'
        )

        db.session.add(pagamento)
        db.session.commit()  # precisa do ID antes de gerar o boleto

        # Gera boleto usando o serviço externo
        try:
            #gerar_boleto_pagbank(pagamento.id)
            print(f"✅ Fatura e boleto gerados para contrato {contrato.id}")
        except Exception as e:
            print(f"❌ Erro ao gerar boleto para contrato {contrato.id}: {e}")

        faturas_criadas += 1

    print(f"\n📄 Total de faturas criadas: {faturas_criadas}\n")


if __name__ == '__main__':
    gerar_faturas()


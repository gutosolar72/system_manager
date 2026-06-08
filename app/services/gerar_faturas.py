#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.integrations.asaas.service import gerar_cobranca_asaas, criar_nf_asaas

# Ajusta path para importar o app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Contrato, Licenca, HistoricoPagamentos

app = create_app()
app.app_context().push()


def gerar_faturas():
    hoje = datetime.today().date()
    ontem = hoje - timedelta(days=1)

    faturas_criadas = 0

    # --- 1️⃣ Atualiza licenças vencidas ontem para "pendente" (apenas faturaveis)
    licencas_vencidas = Licenca.query.join(Contrato).filter(
        Licenca.data_expiracao == ontem,
        Contrato.faturavel == True
    ).all()

    for licenca in licencas_vencidas:
        licenca.status = "pendente"

    if licencas_vencidas:
        db.session.commit()
        print(f"Licenças pendentes atualizadas: {len(licencas_vencidas)}")

    # --- 2️⃣ Renova licenças de contratos não faturaveis (homologação)
    contratos_homologacao = Contrato.query.filter_by(status='ativo', faturavel=False).all()
    
    for contrato in contratos_homologacao:
        if not contrato.licenca:
            continue
    
        inicio_proximo_mes = hoje.replace(day=1) + relativedelta(months=1)
        if contrato.licenca.data_expiracao >= inicio_proximo_mes:
            print(f"⏭️  Licença já renovada contrato {contrato.id} → {contrato.licenca.data_expiracao}")
            continue
    
        vencimento = hoje.replace(day=contrato.dia_vencimento_boleto)
        if vencimento <= hoje:
            vencimento += relativedelta(months=1)
        
        contrato.licenca.data_expiracao = vencimento + relativedelta(months=1)
        contrato.licenca.status = 'Ativo'
        db.session.commit()
        print(f"🔄 Licença renovada (homologação) contrato {contrato.id} → {contrato.licenca.data_expiracao}")


    # --- 3️⃣ Gera faturas para contratos faturaveis
    contratos = Contrato.query.filter_by(status='ativo', faturavel=True).all()

    for contrato in contratos:
        if not contrato.licenca:
            continue

        if contrato.licenca.data_ativacao:
            ativacao = contrato.licenca.data_ativacao
            if ativacao.day > 25:
                if hoje.month == ativacao.month + 1:
                    continue

        # Período = mês anterior
        periodo_inicio = hoje.replace(day=1)
        periodo_fim    = (hoje.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)

        existente = HistoricoPagamentos.query.filter_by(
            contrato_id=contrato.id,
            periodo_referencia_inicio=periodo_inicio,
            periodo_referencia_fim=periodo_fim
        ).first()

        if existente:
            print(f"⚠️ Fatura já existente para contrato {contrato.id}")
            continue

        vencimento = hoje.replace(day=contrato.dia_vencimento_boleto)
        if vencimento <= hoje:
            vencimento += relativedelta(months=1)

        try:
            pagamento = HistoricoPagamentos(
                licenca_id=contrato.licenca.id,
                contrato_id=contrato.id,
                valor_pago=contrato.valor_mensal,
                data_pagamento=None,
                data_vencimento=vencimento,
                periodo_referencia_inicio=periodo_inicio,
                periodo_referencia_fim=periodo_fim,
                observacao=f'Fatura gerada automaticamente em {datetime.now()}',
                status_boleto='pendente',
                gateway='asaas'
            )

            db.session.add(pagamento)
            db.session.flush()

            gerar_cobranca_asaas(pagamento)
            criar_nf_asaas(pagamento)

            db.session.commit()
            print(f"✅ Fatura e cobrança Asaas geradas para contrato {contrato.id}")
            faturas_criadas += 1

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao gerar cobrança Asaas para contrato {contrato.id}: {e}")
            continue

    print(f"\n📄 Total de faturas criadas: {faturas_criadas}\n")


if __name__ == '__main__':
    gerar_faturas()

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models import Licenca, Contrato, HistoricoPagamentos
from app.extensions import db

def gerar_primeira_fatura(contrato):
    """Gera automaticamente uma fatura assim que a licença é vinculada ao contrato."""
    hoje = datetime.today().date()

    if not contrato or not contrato.licenca:
        return None  # não gera se não houver licença vinculada

    # Calcula o período de vigência (ex: 1 mês)
    periodo_inicio = hoje
    periodo_fim = (periodo_inicio + relativedelta(months=1)) - timedelta(days=1)

    # Evita duplicidade (caso já tenha sido gerada)
    existente = HistoricoPagamentos.query.filter_by(
        contrato_id=contrato.id,
        periodo_referencia_inicio=periodo_inicio,
        periodo_referencia_fim=periodo_fim
    ).first()

    if existente:
        print(f"Fatura já existente para o contrato {contrato.id}")
        return existente

    # Cria fatura pendente
    pagamento = HistoricoPagamentos(
        licenca_id=contrato.licenca.id,
        contrato_id=contrato.id,
        valor_pago=contrato.valor_mensal,
        data_pagamento=None,
        periodo_referencia_inicio=periodo_inicio,
        periodo_referencia_fim=periodo_fim,
        observacao=f'Fatura inicial gerada automaticamente em {datetime.now()}',
        status_boleto='pendente'
    )

    db.session.add(pagamento)
    
    contrato.status = "pendente"
    if contrato.licenca:
        contrato.licenca.data_ativacao = datetime.now()
        contrato.licenca.data_expiracao = datetime.now()  # <── expiração = agora
        contrato.licenca.ultima_verificacao = datetime.now()

    db.session.commit()
    db.session.commit()
    print(f"✅ Fatura inicial criada para contrato {contrato.id}")
    return pagamento

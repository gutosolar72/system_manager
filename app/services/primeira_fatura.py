# app/services/primeira_fatura.py

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from app.models import Licenca, Contrato, HistoricoPagamentos
from app.extensions import db
from app.services.gerar_boletos_pagbank import gerar_boleto_pagbank

def gerar_primeira_fatura(contrato):
    """Gera automaticamente a primeira fatura se a licença for vinculada entre os dias 25 e o último dia do mês."""

    hoje = datetime.today().date()

    # Verifica se existe contrato e licença
    if not contrato or not contrato.licenca:
        return None

    # Só gera fatura se estivermos entre o dia 25 e o último dia do mês
    ultimo_dia = monthrange(hoje.year, hoje.month)[1]
    if hoje.day < 24:
        print(f"Hoje é dia {hoje.day}, fora do período de geração automática da primeira fatura.")
        return None

    # Período da fatura: começa hoje e vai até o último dia do mês
    periodo_inicio = hoje
    periodo_fim = date(hoje.year, hoje.month, ultimo_dia)

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

    # Ajusta status do contrato e datas da licença
    contrato.status = "pendente"
    contrato.licenca.data_ativacao = datetime.now()
    # Expiração da licença = dia 5 do próximo mês
    proximo_mes = hoje + relativedelta(months=1)
    contrato.licenca.data_expiracao = date(proximo_mes.year, proximo_mes.month, 5)
    contrato.licenca.ultima_verificacao = datetime.now()

    db.session.commit()

    # Gera boleto usando o serviço externo
    #gerar_boleto_pagbank(pagamento.id)

    print(f"✅ Fatura inicial criada para contrato {contrato.id}")
    return pagamento


# app/integrations/asaas/config.py

"""
Configuração do Asaas
=====================

Ambiente hardcoded conforme decisão do projeto.
Quando entrar em produção, este arquivo NÃO deve mudar com frequência.
"""

ASAAS_ENV = 'sandbox'  # 'sandbox' ou 'producao'

ASAAS_CONFIG = {
    'sandbox': {
        'base_url': 'https://sandbox.asaas.com/api/v3',
        'api_key': '$aact_hmlg_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OjQwMWZkNGNhLTRiZTgtNDcwNC04NmFhLTUzOTQwYmIyOGQ3Yzo6JGFhY2hfMjI1NTIxOTctNWQxMi00OTViLTg4NjItMTgxYWI1ZGM5Zjg5'
    },
    'producao': {
        'base_url': 'https://www.asaas.com/api/v3',
        'api_key': 'SUA_API_KEY_PRODUCAO_AQUI'
    }
}


def get_asaas_config():
    return ASAAS_CONFIG[ASAAS_ENV]


# NanoSIP System Manager

Sistema de gerenciamento de licenças do NanoSIP, com emissão automatizada de boletos e notas fiscais eletrônicas por meio de integração com a plataforma Asaas.

## Sobre o projeto

O System Manager centraliza a administração comercial das instalações do NanoSIP (padrão, VM e Raspberry Pi), permitindo o cadastro de clientes, o controle de licenças ativas e a automação do ciclo de cobrança recorrente — desde a geração do boleto até a emissão da nota fiscal correspondente.

## Funcionalidades

- Cadastro e gerenciamento de clientes e licenças;
- Classificação das instalações por tipo (padrão, VM ou embarcado/Raspberry Pi);
- Emissão automatizada de boletos via integração com a API do Asaas;
- Emissão de Nota Fiscal Eletrônica (NF-e) vinculada ao pagamento;
- Controle de validade e status das licenças recorrentes.

## Arquitetura e tecnologias

- **Backend:** Python (Flask)
- **Integração de pagamentos e faturamento:** API Asaas (boletos e NF-e)
- **Configuração:** `config.py`
- **Ponto de entrada da aplicação:** `run.py`
- **Dependências:** listadas em `requirements.txt`

## Estrutura do projeto
``
system_manager/
├── run.py                     # Ponto de entrada da aplicação
├── config.py                   # Configurações do sistema (ambiente, credenciais de integração)
├── customer_teste.py           # Rotina de testes de cadastro/consulta de clientes
├── requirements.txt            # Dependências do projeto
├── app/                         # Aplicação principal (Flask)
└── scripts/                     # Scripts auxiliares de automação
```

## Licenciamento

Projeto de uso comercial interno, integrado ao ecossistema NanoSIP. Distribuição e uso sujeitos a licença do autor.

## Autor

**Luis Augusto de Campos Alves**
Professor de Ensino Superior — Fatec Ourinhos
[github.com/gutosolar72](https://github.com/gutosolar72)

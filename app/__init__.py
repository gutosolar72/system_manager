# /deploy/system_manager/app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# 1. Inicialização das Extensões
# Criamos as instâncias das extensões aqui, mas sem associá-las a nenhuma aplicação ainda.
# Isso evita um problema chamado "dependência circular".
db = SQLAlchemy()

# 2. Application Factory Function
def create_app(config_class=Config):
    """
    Cria e configura uma instância da aplicação Flask.
    Este é o padrão "Application Factory", que torna a aplicação mais modular.
    """
    # Cria a instância principal da aplicação Flask.
    app = Flask(__name__)

    # Carrega as configurações a partir do objeto importado do arquivo config.py.
    app.config.from_object(config_class)

    # 3. Vincula as Extensões à Aplicação
    # Agora que a aplicação 'app' existe, podemos vincular nossas extensões a ela.
    db.init_app(app)

    # 4. Registrar Blueprints (as rotas/endpoints da nossa API)
    # Um Blueprint é um conjunto de rotas que pode ser registrado em uma aplicação.
    # Isso nos ajuda a organizar nosso código.
    from .api import bp as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    # Retorna a instância da aplicação configurada.
    return app



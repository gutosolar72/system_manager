# /deploy/system_manager/app/__init__.py

from flask import Flask
from config import Config
from .extensions import db, login

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)
    login.login_view = 'main.login'

    from .main import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    from . import models

    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'Usuario': models.Usuario,
            'Cliente': models.Cliente,
            'Equipamento': models.Equipamento,
            'Integrador': models.Integrador,
            'Produto': models.Produto,
            'Contato': models.Contato,
            'HistoricoPagamento': models.HistoricoPagamento,
            'AuditoriaLog': models.AuditoriaLog
        }

    return app


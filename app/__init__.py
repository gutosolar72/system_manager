from flask import Flask
from config import Config
from app.extensions import db, login # Importa db e login de app.extensions

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)
    login.login_view = 'main.login'
    login.login_message = 'Por favor, faça login para acessar esta página.'
    login.login_message_category = 'info'

    from .main import bp as main_blueprint # Importa o blueprint corretamente
    app.register_blueprint(main_blueprint)

    # Removido: from . import models para evitar importação circular

    @app.shell_context_processor
    def make_shell_context():
        from app import models # Importa models aqui para o shell context
        return {
            'db': db,
            'Usuario': models.Usuario,
            'Cliente': models.Cliente,
            'Licencas': models.Licencas,
            'Integrador': models.Integrador,
            'Produto': models.Produto,
            'Contato': models.Contato,
            'HistoricoPagamento': models.HistoricoPagamento,
            'AuditoriaLog': models.AuditoriaLog
        }

    return app


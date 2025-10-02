# /deploy/system_manager/app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # --- MUDANÇA PRINCIPAL AQUI ---
    # Agora estamos registrando o blueprint 'main' na raiz da URL.
    from .main import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    return app


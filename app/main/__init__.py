# /deploy/system_manager/app/main/__init__.py
from flask import Blueprint

# 'main' será o nome do nosso blueprint para a aplicação web.
bp = Blueprint('main', __name__)

# Importa as rotas da aplicação principal.
from app.main import routes


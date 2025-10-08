# app/api/__init__.py
from flask import Blueprint

# Blueprint único para a API
bp_api = Blueprint('api', __name__)

# Importa as rotas (evita importação circular)
from app.api import routes


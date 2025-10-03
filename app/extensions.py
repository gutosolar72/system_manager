# /deploy/system_manager/app/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Cria as instâncias das extensões aqui.
# Elas não estão ligadas a nenhuma aplicação ainda.
db = SQLAlchemy()
login = LoginManager()


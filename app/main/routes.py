# /deploy/system_manager/app/main/routes.py
from app.main import bp

# Esta será a rota raiz do nosso sistema.
# Ex: http://IP_DO_SEU_SERVIDOR:5000/
@bp.route('/' )
def index():
    return "<h1>Bem-vindo ao System Manager!</h1>"


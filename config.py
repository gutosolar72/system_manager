# /deploy/system_manager/config.py

import os

# Encontra o caminho absoluto da pasta onde este arquivo está.
# Isso ajuda a evitar problemas com caminhos relativos.
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Classe de configuração principal da aplicação.
    As configurações são definidas como atributos de classe.
    """

    # Chave secreta para proteger formulários e sessões contra ataques (CSRF).
    # É crucial para a segurança do painel administrativo que construiremos.
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)

    # --- Configuração do Banco de Dados (MariaDB/MySQL) ---

    # URI de conexão para o SQLAlchemy.
    # Formato: mysql+pymysql://<usuario>:<senha>@<host>/<banco_de_dados>
    # Substitua 'sua_senha_para_o_app_aqui' pela senha correta.
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        f"mysql+pymysql://sys_manager_user:123mudar@localhost/system_manager"
    )

    # Desativa uma funcionalidade do Flask-SQLAlchemy que não usaremos e que consome recursos.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # (Opcional) Se definido como True, o SQLAlchemy imprimirá no terminal
    # todos os comandos SQL que ele executa. Ótimo para depuração.
    # Deixe como False em produção.
    SQLALCHEMY_ECHO = False



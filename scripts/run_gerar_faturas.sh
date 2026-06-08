#!/bin/bash
PROJECT_DIR="/deploy/system_manager"

export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Carrega variáveis de ambiente
set -a
source "$PROJECT_DIR/.env"
set +a

source "$PROJECT_DIR/venv/bin/activate"

python "$PROJECT_DIR/app/services/gerar_faturas.py"

deactivate

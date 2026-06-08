#!/bin/bash
# Caminho do projeto
PROJECT_DIR="/deploy/system_manager"

# Define o PYTHONPATH para que o Python encontre o módulo 'app'
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

set -a
source "$PROJECT_DIR/.env"
set +a

# Ativa virtualenv
source "$PROJECT_DIR/venv/bin/activate"

# Roda o script Python
python "$PROJECT_DIR/app/services/enviar_nfs_cliente.py"

# Desativa virtualenv
deactivate

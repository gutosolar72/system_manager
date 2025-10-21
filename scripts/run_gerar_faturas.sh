#!/bin/bash
# Caminho do projeto
PROJECT_DIR="/deploy/system_manager"

# Define o PYTHONPATH para que o Python encontre o módulo 'app'
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Ativa virtualenv
source "$PROJECT_DIR/venv/bin/activate"

# Roda o script Python
python "$PROJECT_DIR/app/services/gerar_faturas.py"

# Desativa virtualenv
deactivate

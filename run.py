# /deploy/system_manager/run.py

from app import create_app

# Cria a instância da aplicação Flask usando a factory function que definiremos.
app = create_app()

if __name__ == '__main__':
    # Inicia o servidor de desenvolvimento do Flask.
    # host='0.0.0.0' faz o servidor ser acessível de fora do container/máquina,
    # o que é essencial para testarmos a partir da nossa máquina.
    # debug=True ativa o modo de depuração, que reinicia o servidor
    # automaticamente a cada mudança no código e mostra erros detalhados.
    # ATENÇÃO: Nunca use debug=True em um ambiente de produção!
    app.run(host='0.0.0.0', port=5000, debug=True)


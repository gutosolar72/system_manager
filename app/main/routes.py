# /deploy/system_manager/app/main/routes.py

from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from app.main import bp
from app.main.forms import LoginForm, ClienteForm, IntegradorForm
from app.models import Usuario, Cliente, Integrador, Contato
from werkzeug.security import check_password_hash
from sqlalchemy import or_


# --- LINHA FALTANDO ---
# Precisamos importar o 'db' do nosso arquivo de extensões.
from app.extensions import db

@bp.route('/')
@login_required  # Adiciona proteção a esta rota!
def index():
    # Agora esta página só pode ser acessada por usuários logados.
    return render_template('index.html', title='Dashboard')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Se o usuário já estiver logado, redireciona para a página inicial.
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Busca o usuário no banco pelo email.
        user = db.session.scalar(db.select(Usuario).where(Usuario.email == form.email.data))

        # Verifica se o usuário existe e se a senha está correta.
        if user is None or not check_password_hash(user.hash_senha, form.password.data):
            flash('Email ou senha inválidos')
            return redirect(url_for('main.login'))
        
        # Se tudo estiver correto, registra o usuário como logado.
        login_user(user, remember=form.remember_me.data)
        flash('Login bem-sucedido!')
        return redirect(url_for('main.index'))

    return render_template('login.html', title='Entrar', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/clientes')
@login_required
def listar_clientes():
    # Pega o termo de busca da URL (?busca=...). Se não houver, o valor é None.
    termo_busca = request.args.get('busca')
    
    # Inicia a consulta base
    query = db.select(Cliente)
    
    # Se um termo de busca foi fornecido, adiciona a condição de filtro
    if termo_busca:
        # Filtra onde o nome da empresa OU o CNPJ contém o termo de busca.
        # O 'ilike' faz uma busca "case-insensitive" (não diferencia maiúsculas/minúsculas).
        query = query.where(
            or_(
                Cliente.nome_empresa.ilike(f'%{termo_busca}%'),
                Cliente.cnpj.ilike(f'%{termo_busca}%')
            )
        )
    
    # Ordena os resultados e executa a consulta
    clientes = db.session.scalars(query.order_by(Cliente.nome_empresa)).all()
    
    # Renderiza o template, passando a lista (filtrada ou não) e o termo de busca
    return render_template(
        'clientes/lista_clientes.html', 
        clientes=clientes, 
        title="Clientes",
        termo_busca=termo_busca # Passa o termo de volta para o template
    )

@bp.route('/cliente/novo', methods=['GET', 'POST'])
@login_required
def cadastrar_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        novo_cliente = Cliente(
            integrador_id=1,  # Provisório
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            telefone=form.telefone.data,
            endereco=form.endereco.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            uf=form.uf.data.upper(), # Salva o UF em maiúsculas
            dia_faturamento=form.dia_faturamento.data
        )
        db.session.add(novo_cliente)
        db.session.commit()
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect(url_for('main.listar_clientes'))
    
    return render_template('clientes/cadastrar_cliente.html', title='Cadastrar Cliente', form=form)

@bp.route('/cliente/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    # Busca o cliente pelo ID ou retorna um erro 404 (Não Encontrado) se não existir.
    cliente = db.get_or_404(Cliente, id)
    
    # Reutilizamos o mesmo ClienteForm que usamos para criar.
    form = ClienteForm(obj=cliente)
    
    if form.validate_on_submit():
        # Se o formulário for submetido e válido, atualiza os dados do objeto cliente.
        cliente.nome_empresa = form.nome_empresa.data
        cliente.cnpj = form.cnpj.data
        cliente.telefone = form.telefone.data
        cliente.endereco = form.endereco.data
        cliente.bairro = form.bairro.data
        cliente.cidade = form.cidade.data
        cliente.uf = form.uf.data.upper()
        cliente.dia_faturamento = form.dia_faturamento.data
        
        # Salva as alterações no banco de dados.
        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('main.listar_clientes'))
    
    # Se for uma requisição GET, apenas renderiza o template com o formulário pré-preenchido.
    return render_template('clientes/editar_cliente.html', title='Editar Cliente', form=form, cliente=cliente)

@bp.route('/cliente/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_cliente(id):
    # Busca o cliente ou retorna erro 404
    cliente = db.get_or_404(Cliente, id)
    
    # Remove o cliente da sessão do banco de dados
    db.session.delete(cliente)
    
    # Confirma a remoção no banco
    db.session.commit()
    
    flash(f'Cliente "{cliente.nome_empresa}" foi excluído com sucesso.', 'success')
    return redirect(url_for('main.listar_clientes'))

@bp.route('/integradores')
@login_required
def listar_integradores():
    termo_busca = request.args.get('busca')
    query = db.select(Integrador)
    if termo_busca:
        query = query.where(
            or_(
                Integrador.nome_empresa.ilike(f'%{termo_busca}%'),
                Integrador.cnpj.ilike(f'%{termo_busca}%'),
                Integrador.contato_nome.ilike(f'%{termo_busca}%')
            )
        )
    integradores = db.session.scalars(query.order_by(Integrador.nome_empresa)).all()
    return render_template(
        'integradores/lista_integradores.html',
        integradores=integradores,
        title="Integradores",
        termo_busca=termo_busca
    )

@bp.route('/integrador/novo', methods=['GET', 'POST'])
@login_required
def cadastrar_integrador():
    form = IntegradorForm()
    if form.validate_on_submit():
        # Passo 1: Criar e salvar o Integrador para obter um ID
        novo_integrador = Integrador(
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            telefone=form.telefone.data,
            endereco=form.endereco.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            uf=form.uf.data.upper()
        )
        db.session.add(novo_integrador)
        # O flush envia as alterações para o banco e preenche o ID, mas não finaliza a transação
        db.session.flush() 

        # Passo 2: Criar o Contato, vinculando-o ao ID do novo integrador
        novo_contato = Contato(
            nome=form.contato_nome.data,
            email=form.contato_email.data,
            telefone=form.contato_telefone.data,
            integrador_id=novo_integrador.id, # Vincula ao integrador
            is_principal=True
        )
        db.session.add(novo_contato)

        # Passo 3: Agora sim, finalizar a transação salvando tudo
        db.session.commit()
        
        flash('Integrador e contato principal cadastrados com sucesso!', 'success')
        return redirect(url_for('main.listar_integradores'))
    
    elif request.method == 'POST':
        flash(f'Erro de validação: {form.errors}', 'danger')
        
    return render_template('integradores/form_integrador.html', title='Novo Integrador', form=form)

@bp.route('/integrador/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_integrador(id):
    integrador = db.get_or_404(Integrador, id)
    form = IntegradorForm(obj=integrador)
    if form.validate_on_submit():
        form.populate_obj(integrador) # Atualiza o objeto com os dados do formulário
        db.session.commit()
        flash('Integrador atualizado com sucesso!', 'success')
        return redirect(url_for('main.listar_integradores'))
    return render_template('integradores/form_integrador.html', title='Editar Integrador', form=form, integrador=integrador)

@bp.route('/integrador/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_integrador(id):
    integrador = db.get_or_404(Integrador, id)
    db.session.delete(integrador)
    db.session.commit()
    flash(f'Integrador "{integrador.nome_empresa}" foi excluído com sucesso.', 'success')
    return redirect(url_for('main.listar_integradores'))

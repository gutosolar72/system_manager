from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import Usuario, Cliente, Integrador, Contato, AuditoriaLog
from .forms import LoginForm, ClienteForm, IntegradorForm
import json

main = Blueprint('main', __name__)

# =============================================================================
# FUNÇÃO DE AUDITORIA
# =============================================================================
def log_auditoria(tipo_acao, tabela_afetada=None, registro_id=None, detalhes=None):
    """
    Registra uma ação no log de auditoria.
    """
    try:
        # Limpeza de dados para evitar armazenar objetos complexos no log
        if detalhes and 'dados_novos' in detalhes and '_sa_instance_state' in detalhes['dados_novos']:
            del detalhes['dados_novos']['_sa_instance_state']
        if detalhes and 'dados_antigos' in detalhes and '_sa_instance_state' in detalhes['dados_antigos']:
            del detalhes['dados_antigos']['_sa_instance_state']
        if detalhes and 'dados_excluidos' in detalhes and '_sa_instance_state' in detalhes['dados_excluidos']:
            del detalhes['dados_excluidos']['_sa_instance_state']

        log = AuditoriaLog(
            usuario_id=current_user.id if current_user.is_authenticated else None,
            tipo_acao=tipo_acao,
            tabela_afetada=tabela_afetada,
            registro_id=registro_id,
            detalhes=json.dumps(detalhes, ensure_ascii=False, default=str) if detalhes else None
        )
        db.session.add(log)
    except Exception as e:
        print(f"ERRO ao registrar log de auditoria: {e}")


# =============================================================================
# ROTAS DE AUTENTICAÇÃO E PRINCIPAIS
# =============================================================================

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(email=form.email.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            log_auditoria('LOGIN_SUCESSO', detalhes={'email': user.email})
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            log_auditoria('LOGIN_FALHA', detalhes={'email': form.email.data})
            db.session.commit()
            flash('E-mail ou senha inválidos.', 'danger')
            
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('main.login'))

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# =============================================================================
# CRUD DE CLIENTES
# =============================================================================

@main.route('/clientes')
@login_required
def listar_clientes():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if query:
        search_filter = f"%{query}%"
        clientes_pagination = Cliente.query.filter(
            (Cliente.nome_empresa.like(search_filter)) |
            (Cliente.cnpj.like(search_filter)) |
            (Cliente.cidade.like(search_filter))
        ).order_by(Cliente.nome_empresa).paginate(page=page, per_page=10)
    else:
        clientes_pagination = Cliente.query.order_by(Cliente.nome_empresa).paginate(page=page, per_page=10)
        
    # CORREÇÃO: Caminho do template ajustado
    return render_template('clientes.html', clientes=clientes_pagination, query=query)

@main.route('/clientes/add', methods=['GET', 'POST'])
@login_required
def adicionar_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        novo_cliente = Cliente(
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            endereco=form.endereco.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            uf=form.uf.data,
            cep=form.cep.data,
            telefone=form.telefone.data,
            integrador_id=form.integrador_id.data,
            dia_faturamento=form.dia_faturamento.data
        )
        db.session.add(novo_cliente)
        db.session.flush() 

        log_auditoria('CRIACAO', tabela_afetada='clientes', registro_id=novo_cliente.id, detalhes={'dados_novos': {c.name: getattr(novo_cliente, c.name) for c in novo_cliente.__table__.columns}})
        
        db.session.commit()
        flash('Cliente adicionado com sucesso!', 'success')
        return redirect(url_for('main.listar_clientes'))
        
    # CORREÇÃO: Caminho do template ajustado
    return render_template('cliente_form.html', form=form, cliente=None)

@main.route('/clientes/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    form = ClienteForm(obj=cliente)
    
    dados_antigos = {c.name: getattr(cliente, c.name) for c in cliente.__table__.columns}

    if form.validate_on_submit():
        form.populate_obj(cliente) # Popula o objeto com os dados do formulário
        cliente.cep = form.cep.data # Garante que o CEP seja populado
        
        db.session.add(cliente)
        
        dados_novos = {c.name: getattr(cliente, c.name) for c in cliente.__table__.columns}
        
        log_auditoria('ATUALIZACAO', tabela_afetada='clientes', registro_id=cliente.id, detalhes={'dados_antigos': dados_antigos, 'dados_novos': dados_novos})

        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('main.listar_clientes'))

    # CORREÇÃO: Caminho do template ajustado
    return render_template('cliente_form.html', form=form, cliente=cliente)

@main.route('/clientes/delete/<int:id>', methods=['POST'])
@login_required
def deletar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    dados_excluidos = {c.name: getattr(cliente, c.name) for c in cliente.__table__.columns}
    log_auditoria('EXCLUSAO', tabela_afetada='clientes', registro_id=id, detalhes={'dados_excluidos': dados_excluidos})

    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente excluído com sucesso.', 'success')
    return redirect(url_for('main.listar_clientes'))

# =============================================================================
# CRUD DE INTEGRADORES
# =============================================================================

@main.route('/integradores')
@login_required
def listar_integradores():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if query:
        search_filter = f"%{query}%"
        integradores_pagination = Integrador.query.filter(
            (Integrador.nome_empresa.like(search_filter)) |
            (Integrador.cnpj.like(search_filter))
        ).order_by(Integrador.nome_empresa).paginate(page=page, per_page=10)
    else:
        integradores_pagination = Integrador.query.order_by(Integrador.nome_empresa).paginate(page=page, per_page=10)
        
    # CORREÇÃO: Caminho do template ajustado
    return render_template('integradores.html', integradores=integradores_pagination, query=query)

@main.route('/integradores/add', methods=['GET', 'POST'])
@login_required
def adicionar_integrador():
    form = IntegradorForm()
    if form.validate_on_submit():
        novo_integrador = Integrador(
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            endereco=form.endereco.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            uf=form.uf.data,
            cep=form.cep.data,
            telefone=form.telefone_empresa.data
        )
        
        contato_principal = Contato(
            nome=form.nome_contato.data,
            email=form.email_contato.data,
            telefone=form.telefone_contato.data,
            is_principal=True,
            integrador=novo_integrador
        )
        
        db.session.add(novo_integrador)
        db.session.add(contato_principal)
        db.session.flush()

        log_auditoria('CRIACAO', tabela_afetada='integradores', registro_id=novo_integrador.id, detalhes={'dados_novos': {c.name: getattr(novo_integrador, c.name) for c in novo_integrador.__table__.columns}})

        db.session.commit()
        flash('Integrador adicionado com sucesso!', 'success')
        return redirect(url_for('main.listar_integradores'))
        
    # CORREÇÃO: Caminho do template ajustado
    return render_template('integrador_form.html', form=form, integrador=None)

@main.route('/integradores/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_integrador(id):
    integrador = Integrador.query.get_or_404(id)
    contato_principal = integrador.get_contato_principal() or Contato(is_principal=True, integrador=integrador)
    
    form = IntegradorForm(obj=integrador)
    if request.method == 'GET':
        form.telefone_empresa.data = integrador.telefone
        if contato_principal and contato_principal.id: # Checa se o contato já existe
            form.nome_contato.data = contato_principal.nome
            form.email_contato.data = contato_principal.email
            form.telefone_contato.data = contato_principal.telefone

    dados_antigos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}

    if form.validate_on_submit():
        integrador.nome_empresa = form.nome_empresa.data
        integrador.cnpj = form.cnpj.data
        integrador.endereco = form.endereco.data
        integrador.bairro = form.bairro.data
        integrador.cidade = form.cidade.data
        integrador.uf = form.uf.data
        integrador.cep = form.cep.data
        integrador.telefone = form.telefone_empresa.data
        
        contato_principal.nome = form.nome_contato.data
        contato_principal.email = form.email_contato.data
        contato_principal.telefone = form.telefone_contato.data
        
        db.session.add(integrador)
        if not contato_principal.id: # Adiciona o contato se for novo
            db.session.add(contato_principal)

        dados_novos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}

        log_auditoria('ATUALIZACAO', tabela_afetada='integradores', registro_id=integrador.id, detalhes={'dados_antigos': dados_antigos, 'dados_novos': dados_novos})

        db.session.commit()
        flash('Integrador atualizado com sucesso!', 'success')
        return redirect(url_for('main.listar_integradores'))

    # CORREÇÃO: Caminho do template ajustado
    return render_template('integrador_form.html', form=form, integrador=integrador)

@main.route('/integradores/delete/<int:id>', methods=['POST'])
@login_required
def deletar_integrador(id):
    integrador = Integrador.query.get_or_404(id)
    
    dados_excluidos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}
    log_auditoria('EXCLUSAO', tabela_afetada='integradores', registro_id=id, detalhes={'dados_excluidos': dados_excluidos})

    db.session.delete(integrador)
    db.session.commit()
    flash('Integrador excluído com sucesso.', 'success')
    return redirect(url_for('main.listar_integradores'))


from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from app.main import bp # Importar bp do __init__.py da main
from app.models import Usuario, Cliente, Integrador, Contato, AuditoriaLog
from app.main.forms import LoginForm, ClienteForm, IntegradorForm # Importar forms diretamente
from werkzeug.security import check_password_hash
from sqlalchemy import or_
from app.extensions import db # Importar db de app.extensions
import json

# =============================================================================
# FUNÇÃO DE AUDITORIA
# =============================================================================
def log_auditoria(tipo_acao, tabela_afetada=None, registro_id=None, detalhes=None):
    """
    Registra uma ação no log de auditoria.
    """
    try:
        # Limpeza de dados para evitar armazenar objetos complexos no log
        if detalhes:
            # Converte objetos SQLAlchemy para dicionários simples para log
            if "dados_novos" in detalhes and hasattr(detalhes["dados_novos"], "__dict__"):
                detalhes["dados_novos"] = {c.name: getattr(detalhes["dados_novos"], c.name) for c in detalhes["dados_novos"].__table__.columns}
            if "dados_antigos" in detalhes and hasattr(detalhes["dados_antigos"], "__dict__"):
                detalhes["dados_antigos"] = {c.name: getattr(detalhes["dados_antigos"], c.name) for c in detalhes["dados_antigos"].__table__.columns}
            if "dados_excluidos" in detalhes and hasattr(detalhes["dados_excluidos"], "__dict__"):
                detalhes["dados_excluidos"] = {c.name: getattr(detalhes["dados_excluidos"], c.name) for c in detalhes["dados_excluidos"].__table__.columns}

        log = AuditoriaLog(
            usuario_id=current_user.id if current_user.is_authenticated else None,
            tipo_acao=tipo_acao,
            tabela_afetada=tabela_afetada,
            registro_id=registro_id,
            detalhes=json.dumps(detalhes, ensure_ascii=False, default=str) if detalhes else None
        )
        db.session.add(log)
        # O commit será feito junto com a transação principal da rota
    except Exception as e:
        print(f"ERRO ao registrar log de auditoria: {e}")


# =============================================================================
# ROTAS DE AUTENTICAÇÃO E PRINCIPAIS
# =============================================================================

@bp.route("/")
@login_required
def index():
    return render_template("dashboard.html", title="Dashboard")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(email=form.email.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            log_auditoria("LOGIN_SUCESSO", detalhes={"email": user.email})
            db.session.commit() # Commit do log
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        else:
            log_auditoria("LOGIN_FALHA", detalhes={"email": form.email.data})
            db.session.commit() # Commit do log
            flash("E-mail ou senha inválidos.", "danger")
            
    return render_template("login.html", title="Entrar", form=form)

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você foi desconectado com sucesso.", "success")
    return redirect(url_for("main.index"))

# =============================================================================
# CRUD DE CLIENTES
# =============================================================================

@bp.route("/clientes")
@login_required
def listar_clientes():
    query_param = request.args.get("busca", "")
    page = request.args.get("page", 1, type=int)
    
    if query_param:
        search_filter = f"%{query_param}%"
        clientes_pagination = Cliente.query.filter(
            (Cliente.nome_empresa.like(search_filter)) |
            (Cliente.cnpj.like(search_filter)) |
            (Cliente.cidade.like(search_filter))
        ).order_by(Cliente.nome_empresa).paginate(page=page, per_page=10)
    else:
        clientes_pagination = Cliente.query.order_by(Cliente.nome_empresa).paginate(page=page, per_page=10)
        
    return render_template("clientes/lista_clientes.html", clientes=clientes_pagination, title="Clientes", termo_busca=query_param)

@bp.route("/cliente/novo", methods=["GET", "POST"])
@login_required
def cadastrar_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        novo_cliente = Cliente(
            integrador_id=form.integrador_id.data, # Usar o integrador_id do formulário
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            endereco=form.endereco.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            uf=form.uf.data.upper(),
            cep=form.cep.data, # Campo CEP adicionado
            telefone=form.telefone.data,
            dia_faturamento=form.dia_faturamento.data
        )
        db.session.add(novo_cliente)
        db.session.flush() 

        log_auditoria("CRIACAO", tabela_afetada="clientes", registro_id=novo_cliente.id, detalhes={"dados_novos": novo_cliente})
        
        db.session.commit()
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("main.listar_clientes"))
    
    return render_template("clientes/cadastrar_cliente.html", title="Cadastrar Cliente", form=form)

@bp.route("/cliente/editar/<int:id>", methods=["GET", "POST"])
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
        
        log_auditoria("ATUALIZACAO", tabela_afetada="clientes", registro_id=cliente.id, detalhes={"dados_antigos": dados_antigos, "dados_novos": dados_novos})

        db.session.commit()
        flash("Cliente atualizado com sucesso!", "success")
        return redirect(url_for("main.listar_clientes"))

    return render_template("clientes/editar_cliente.html", title="Editar Cliente", form=form, cliente=cliente)

@bp.route("/cliente/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    dados_excluidos = {c.name: getattr(cliente, c.name) for c in cliente.__table__.columns}
    log_auditoria("EXCLUSAO", tabela_afetada="clientes", registro_id=id, detalhes={"dados_excluidos": dados_excluidos})

    db.session.delete(cliente)
    db.session.commit()
    flash(f"Cliente \"{cliente.nome_empresa}\" foi excluído com sucesso.", "success")
    return redirect(url_for("main.listar_clientes"))

# =============================================================================
# CRUD DE INTEGRADORES
# =============================================================================

@bp.route("/integradores")
@login_required
def listar_integradores():
    query_param = request.args.get("busca", "")
    page = request.args.get("page", 1, type=int)
    
    if query_param:
        search_filter = f"%{query_param}%"
        integradores_pagination = Integrador.query.filter(
            (Integrador.nome_empresa.like(search_filter)) |
            (Integrador.cnpj.like(search_filter))
        ).order_by(Integrador.nome_empresa).paginate(page=page, per_page=10)
    else:
        integradores_pagination = Integrador.query.order_by(Integrador.nome_empresa).paginate(page=page, per_page=10)
        
    return render_template("integradores/lista_integradores.html", integradores=integradores_pagination, title="Integradores", termo_busca=query_param)

@bp.route("/integrador/novo", methods=["GET", "POST"])
@login_required
def cadastrar_integrador():
    form = IntegradorForm()
    if form.validate_on_submit():
        novo_integrador = Integrador(
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            endereco=form.endereco.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            uf=form.uf.data.upper(),
            cep=form.cep.data, # Campo CEP adicionado
            telefone=form.telefone.data
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

        log_auditoria("CRIACAO", tabela_afetada="integradores", registro_id=novo_integrador.id, detalhes={"dados_novos": novo_integrador})

        db.session.commit()
        flash("Integrador adicionado com sucesso!", "success")
        return redirect(url_for("main.listar_integradores"))
        
    return render_template("integradores/form_integrador.html", title="Novo Integrador", form=form)

@bp.route("/integrador/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_integrador(id):
    integrador = Integrador.query.get_or_404(id)
    contato_principal = integrador.get_contato_principal() or Contato(is_principal=True, integrador=integrador)
    
    form = IntegradorForm(obj=integrador)
    if request.method == "GET":
        form.telefone.data = integrador.telefone # Corrigido para form.telefone
        if contato_principal and contato_principal.id: 
            form.nome_contato.data = contato_principal.nome
            form.email_contato.data = contato_principal.email
            form.telefone_contato.data = contato_principal.telefone

    dados_antigos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}

    if form.validate_on_submit():
        integrador.nome_empresa = form.nome_empresa.data
        integrador.cnpj = form.cnpj.data
        integrador.endereco = form.endereco.data
        integrador.bairro = form.bairro.data
        integrador.cidade = form.cidade.data,
        integrador.uf = form.uf.data.upper()
        integrador.cep = form.cep.data # Campo CEP adicionado
        integrador.telefone = form.telefone.data # Corrigido para form.telefone
        
        contato_principal.nome = form.nome_contato.data
        contato_principal.email = form.email_contato.data
        contato_principal.telefone = form.telefone_contato.data
        
        db.session.add(integrador)
        if not contato_principal.id: 
            db.session.add(contato_principal)

        dados_novos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}

        log_auditoria("ATUALIZACAO", tabela_afetada="integradores", registro_id=integrador.id, detalhes={"dados_antigos": dados_antigos, "dados_novos": dados_novos})

        db.session.commit()
        flash("Integrador atualizado com sucesso!", "success")
        return redirect(url_for("main.listar_integradores"))

    return render_template("integradores/form_integrador.html", title="Editar Integrador", form=form, integrador=integrador)

@bp.route("/integrador/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_integrador(id):
    integrador = Integrador.query.get_or_404(id)
    dados_excluidos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}
    log_auditoria("EXCLUSAO", tabela_afetada="integradores", registro_id=id, detalhes={"dados_excluidos": dados_excluidos})
    db.session.delete(integrador)
    db.session.commit()
    flash(f"Integrador \"{integrador.nome_empresa}\" foi excluído com sucesso.", "success")
    return redirect(url_for("main.listar_integradores"))


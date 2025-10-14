from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from app.main import bp # Importar bp do __init__.py da main
from app.models import Usuario, Cliente, Integrador, Contato, Licenca, Produto, Contrato, HistoricoPagamentos, AuditoriaLog
from app.main.forms import LoginForm, ClienteForm, IntegradorForm, ProdutoForm, ContratoForm, PagamentoForm # Importar forms diretamente
from werkzeug.security import check_password_hash
from sqlalchemy import or_
from app.extensions import db # Importar db de app.extensions
import json
from datetime import timedelta, date



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
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            endereco=form.endereco.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            uf=form.uf.data.upper(),
            cep=form.cep.data, # Campo CEP adicionado
            telefone=form.telefone.data,
        )
        db.session.add(novo_cliente)
        db.session.flush() 

        log_auditoria("CRIACAO", tabela_afetada="clientes", registro_id=novo_cliente.id, detalhes={"dados_novos": novo_cliente})
        
        db.session.commit()
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("main.listar_clientes"))
        
    # --- DEBUG: Mostrar erros de validação ---
    if request.method == "POST":
        print("FORM ERRORS:", form.errors)
    
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

#@app.route('/clientes/<int:cliente_id>/licencas')
@login_required
#def licencas(cliente_id):
#    cliente = Cliente.query.get_or_404(cliente_id)
#    licencas = Licenca.query.filter_by(cliente_id=cliente_id).all()
#    return render_template('licencas/licencas.html', cliente=cliente, licencas=licencas)

@bp.route('/licencas')
@login_required
def licencas_lista():
    licencas = Licenca.query.all()
    return render_template('licencas/licencas.html', licencas=licencas)

@bp.route('/licencas/vincular/<int:licenca_id>', methods=['GET', 'POST'])
@login_required
def vincular_chave(licenca_id):
    licenca = Licenca.query.get_or_404(licenca_id)

    # Pega contratos que ainda não têm licença vinculada
    contratos = Contrato.query.filter(Contrato.licenca_id == None).all()

    if request.method == 'POST':
        contrato_id = request.form.get('contrato_id')
        if not contrato_id:
            flash('Selecione um contrato', 'danger')
            return redirect(request.url)

        contrato = Contrato.query.get(int(contrato_id))
        if not contrato:
            flash('Contrato inválido', 'danger')
            return redirect(request.url)

        # Atualiza ambos os lados
        licenca.contrato_id = contrato.id
        contrato.licenca_id = licenca.id

        db.session.commit()
        flash('Licença vinculada com sucesso', 'success')
        return redirect(url_for('main.licencas_lista'))

    return render_template('licencas/vincular_chave.html', licenca=licenca, contratos=contratos)


@bp.route('/apagar_licenca/<int:id>', methods=['POST'])
@login_required
def apagar_licenca(id):
    licenca = Licenca.query.get_or_404(id)
    db.session.delete(licenca)
    db.session.commit()
    return '', 204

@bp.route('/clientes/<int:cliente_id>/licencas')
@login_required
def cliente_licencas(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    licencas = Licenca.query.filter_by(cliente_id=cliente.id).all()
    return render_template('clientes/cliente_licencas.html', cliente=cliente, licencas=licencas)

@bp.route('/clientes/<int:cliente_id>/licencas/json')
@login_required
def cliente_licencas_json(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    licencas = Licenca.query.filter_by(cliente_id=cliente.id).all()

    licencas_data = []
    for l in licencas:
        licencas_data.append({
            'id': l.id,
            'produto': l.produto.nome_produto if l.produto else '',
            'chave_licenca': l.chave_licenca,
            'status': l.status
        })

    return jsonify({'licencas': licencas_data})

# LISTAR PRODUTOS
@bp.route('/produtos')
@login_required
def lista_produtos():
    produtos = Produto.query.order_by(Produto.nome_produto).all()
    return render_template('produtos/lista_produtos.html', produtos=produtos)

# CADASTRAR PRODUTO
@bp.route('/produtos/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar_produto():
    form = ProdutoForm()
    if form.validate_on_submit():
        produto = Produto(
            nome_produto=form.nome_produto.data,
            sku=form.sku.data,
            descricao=form.descricao.data,
            preco_mensal_base=form.preco_mensal_base.data,
            modulos_inclusos=json.dumps(form.modulos_inclusos.data or [])
        )
        db.session.add(produto)
        db.session.commit()
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('main.lista_produtos'))

    return render_template('produtos/cadastrar_produto.html', form=form, produto=None)

# EDITAR PRODUTO
@bp.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    dados_antigos = {c.name: getattr(produto, c.name) for c in produto.__table__.columns}

    if request.method == 'POST':
        produto.nome_produto = request.form.get('nome_produto')
        produto.sku = request.form.get('sku')
        produto.descricao = request.form.get('descricao')
        produto.preco_mensal_base = request.form.get('preco_mensal_base')
        produto.modulos_inclusos = request.form.get('modulos_inclusos') or '[]'

        dados_novos = {c.name: getattr(produto, c.name) for c in produto.__table__.columns}
        log_auditoria("ATUALIZACAO", tabela_afetada="produtos", registro_id=produto.id, detalhes={"dados_antigos": dados_antigos, "dados_novos": dados_novos})

        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('main.lista_produtos'))

    return render_template('produtos/cadastrar_produto.html', produto=produto)

# EXCLUIR PRODUTO
@bp.route('/produtos/excluir/<int:produto_id>', methods=['POST'])
@login_required
def excluir_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    dados_excluidos = {c.name: getattr(produto, c.name) for c in produto.__table__.columns}
    log_auditoria("EXCLUSAO", tabela_afetada="produtos", registro_id=produto.id, detalhes={"dados_excluidos": dados_excluidos})
    db.session.delete(produto)
    db.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('main.lista_produtos'))


# --- LISTAR CONTRATOS ---
@bp.route('/contratos')
@login_required
def listar_contratos():
    contratos = Contrato.query.order_by(Contrato.id.desc()).all()
    return render_template('contratos/lista_contratos.html', contratos=contratos)


# --- NOVO CONTRATO ---
@bp.route('/contrato/novo', methods=['GET', 'POST'])
@login_required
def novo_contrato():
    form = ContratoForm()
    if form.validate_on_submit():
        contrato = Contrato(
            cliente_id=form.cliente_id.data,
            integrador_id=form.integrador_id.data,
            licenca_id = int(form.licenca_id.data) if form.licenca_id.data else None,
            #licenca_id=form.licenca_id.data if form.licenca_id.data != 0 else None,
            dia_faturamento=form.dia_faturamento.data,
            valor_mensal=form.valor_mensal.data,
            status=form.status.data,
            modulos_override=form.modulos_override.data,
            observacoes=form.observacoes.data
        )
        db.session.add(contrato)
        db.session.commit()
    
        flash('Contrato cadastrado com sucesso!', 'success')
        return redirect(url_for('main.listar_contratos'))

    return render_template('contratos/cadastrar_contrato.html', form=form)


# --- EDITAR CONTRATO ---
@bp.route('/contrato/<int:contrato_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    form = ContratoForm(obj=contrato)
    if form.validate_on_submit():
        contrato.cliente_id = form.cliente_id.data
        contrato.integrador_id = form.integrador_id.data
        contrato.licenca_id = form.licenca_id.data if form.licenca_id.data != 0 else None
        contrato.dia_faturamento = form.dia_faturamento.data
        contrato.valor_mensal = form.valor_mensal.data
        contrato.status = form.status.data
        contrato.modulos_override = form.modulos_override.data
        contrato.observacoes = form.observacoes.data
        db.session.commit()

        flash('Contrato atualizado com sucesso!', 'success')
        return redirect(url_for('main.listar_contratos'))

    return render_template('contratos/editar_contrato.html', form=form, contrato=contrato)


# --- EXCLUIR CONTRATO ---
@bp.route('/contrato/<int:contrato_id>/excluir', methods=['POST', 'GET'])
@login_required
def excluir_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    db.session.delete(contrato)
    db.session.commit()
    flash('Contrato excluído com sucesso!', 'success')
    return redirect(url_for('main.listar_contratos'))

#------- PAGAMENTOS ----

@bp.route('/pagamento/novo/<int:fatura_id>', methods=['GET', 'POST'])
@login_required
def novo_pagamento_fatura(fatura_id):
    # Busca a fatura
    fatura = HistoricoPagamentos.query.get_or_404(fatura_id)

    # Formulário apenas para observação
    form = PagamentoForm()

    if request.method == 'POST' and form.validate_on_submit():
        # Atualiza a fatura existente
        fatura.valor_pago = fatura.contrato.valor_mensal
        fatura.data_pagamento = date.today()
        fatura.status_boleto = 'pago'  # Força como pago
        fatura.observacao = form.observacao.data or 'Fatura gerada automaticamente'

        # Atualiza expiração e status da licença (se existir)
        if fatura.licenca:
            nova_data_expiracao = fatura.periodo_referencia_fim
            fatura.licenca.data_expiracao = nova_data_expiracao
            fatura.licenca.status = 'Ativo'
            db.session.add(fatura.licenca)

        # Confirma alterações
        db.session.commit()

        flash('Pagamento registrado e licença ativada com sucesso!', 'success')
        return redirect(url_for('main.ver_faturas', contrato_id=fatura.contrato.id))

    # Formata vigência para exibir no template
    periodo_inicial = fatura.periodo_referencia_inicio.strftime('%d/%m/%Y') if fatura.periodo_referencia_inicio else ''
    periodo_final = fatura.periodo_referencia_fim.strftime('%d/%m/%Y') if fatura.periodo_referencia_fim else ''

    return render_template(
        'pagamentos/novo.html',
        form=form,
        periodo_inicial=periodo_inicial,
        periodo_final=periodo_final,
        fatura=fatura
    )



@bp.route('/pagamentos')
@login_required
def pagamentos_lista():
    pagamentos = HistoricoPagamentos.query.order_by(HistoricoPagamentos.data_pagamento.desc()).all()
    return render_template('pagamentos/lista.html', pagamentos=pagamentos)

############ FATURAS #######
@bp.route('/contrato/<int:contrato_id>/faturas')
@login_required
def ver_faturas(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    # Filtrar por status se passado na query string
    status_filter = request.args.get('status')
    query = contrato.historico_pagamentos  # lista de faturas

    if status_filter == 'pagas':
        faturas = [f for f in query if f.status_boleto == 'pago']
    elif status_filter == 'nao_pagas':
        faturas = [f for f in query if f.status_boleto != 'pago']
    else:
        faturas = query

    return render_template('contratos/faturas.html', contrato=contrato, faturas=faturas, status_filter=status_filter)

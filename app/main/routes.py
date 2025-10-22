from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from app.main import bp
from app.models import Usuario, Cliente, Integrador, Contato, Licenca, Produto, Contrato, HistoricoPagamentos, Modulo, AuditoriaLog
from app.main.forms import LoginForm, ClienteForm, IntegradorForm, ProdutoForm, ContratoForm, PagamentoForm, ModuloForm
from werkzeug.security import check_password_hash
from sqlalchemy import or_
from app.extensions import db
import json
from datetime import date
from app.services.primeira_fatura import gerar_primeira_fatura


#from app import app, db


# =============================================================================
# FUNÇÃO DE AUDITORIA
# =============================================================================
def log_auditoria(tipo_acao, tabela_afetada=None, registro_id=None, detalhes=None):
    try:
        if detalhes:
            for key in ["dados_novos", "dados_antigos", "dados_excluidos"]:
                if key in detalhes and hasattr(detalhes[key], "__dict__"):
                    detalhes[key] = {c.name: getattr(detalhes[key], c.name) for c in detalhes[key].__table__.columns}

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
# ROTAS DE AUTENTICAÇÃO
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
            db.session.commit()
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.index"))
        else:
            log_auditoria("LOGIN_FALHA", detalhes={"email": form.email.data})
            db.session.commit()
            flash("E-mail ou senha inválidos.", "danger")

    return render_template("login.html", title="Entrar", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você foi desconectado com sucesso.", "success")
    return redirect(url_for("main.index"))


# =============================================================================
# CRUD CLIENTES
# =============================================================================
@bp.route("/clientes")
@login_required
def listar_clientes():
    query_param = request.args.get("busca", "")
    page = request.args.get("page", 1, type=int)

    if query_param:
        search_filter = f"%{query_param}%"
        clientes_pagination = Cliente.query.filter(
            or_(
                Cliente.nome_empresa.like(search_filter),
                Cliente.cnpj.like(search_filter),
                Cliente.cidade.like(search_filter)
            )
        ).order_by(Cliente.nome_empresa).paginate(page=page, per_page=10)
    else:
        clientes_pagination = Cliente.query.order_by(Cliente.nome_empresa).paginate(page=page, per_page=10)

    return render_template("clientes/clientes.html", clientes=clientes_pagination, title="Clientes", termo_busca=query_param)


@bp.route("/cliente/novo", methods=["GET", "POST"])
@login_required
def cadastrar_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        novo_cliente = Cliente(
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            email=form.email.data,
            ddd=form.ddd.data,
            telefone=form.telefone.data,
            logradouro=form.logradouro.data,
            numero=form.numero.data,
            complemento=form.complemento.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            estado=form.estado.data.upper() if form.estado.data else None,
            cep=form.cep.data,
        )
        db.session.add(novo_cliente)
        db.session.flush()

        log_auditoria(
            "CRIACAO",
            tabela_afetada="clientes",
            registro_id=novo_cliente.id,
            detalhes={"dados_novos": {c.name: getattr(novo_cliente, c.name) for c in novo_cliente.__table__.columns}}
        )

        db.session.commit()
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("main.listar_clientes"))

    return render_template("clientes/form_clientes.html", title="Cadastrar Cliente", form=form, modo="novo")


@bp.route("/cliente/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    form = ClienteForm(obj=cliente)
    dados_antigos = {c.name: getattr(cliente, c.name) for c in cliente.__table__.columns}

    if form.validate_on_submit():
        form.populate_obj(cliente)
        cliente.estado = cliente.estado.upper() if cliente.estado else None
        db.session.add(cliente)

        dados_novos = {c.name: getattr(cliente, c.name) for c in cliente.__table__.columns}
        log_auditoria("ATUALIZACAO", tabela_afetada="clientes", registro_id=cliente.id,
                      detalhes={"dados_antigos": dados_antigos, "dados_novos": dados_novos})
        db.session.commit()
        flash("Cliente atualizado com sucesso!", "success")
        return redirect(url_for("main.listar_clientes"))

    return render_template("clientes/form_clientes.html", title="Editar Cliente", form=form, modo="editar", cliente=cliente)


@bp.route("/cliente/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    
    contratos_vinculados = Contrato.query.filter_by(cliente_id=id).count()
    if contratos_vinculados > 0:
        flash('Não é possível excluir este cliente. Existem contratos vinculados.', 'danger')
        return redirect(url_for('main.listar_clientes'))

    dados_excluidos = {c.name: getattr(cliente, c.name) for c in cliente.__table__.columns}
    log_auditoria("EXCLUSAO", tabela_afetada="clientes", registro_id=id, detalhes={"dados_excluidos": dados_excluidos})
    db.session.delete(cliente)
    db.session.commit()
    flash(f"Cliente \"{cliente.nome_empresa}\" foi excluído com sucesso.", "success")
    return redirect(url_for("main.listar_clientes"))


# =============================================================================
# CRUD INTEGRADORES
# =============================================================================
@bp.route("/integradores")
@login_required
def listar_integradores():
    query_param = request.args.get("busca", "")
    page = request.args.get("page", 1, type=int)

    if query_param:
        search_filter = f"%{query_param}%"
        integradores_pagination = Integrador.query.filter(
            or_(
                Integrador.nome_empresa.like(search_filter),
                Integrador.cnpj.like(search_filter)
            )
        ).order_by(Integrador.nome_empresa).paginate(page=page, per_page=10)
    else:
        integradores_pagination = Integrador.query.order_by(Integrador.nome_empresa).paginate(page=page, per_page=10)

    return render_template("integradores/integradores.html", integradores=integradores_pagination, title="Integradores", termo_busca=query_param)


@bp.route("/integrador/novo", methods=["GET", "POST"])
@login_required
def cadastrar_integrador():
    form = IntegradorForm()
    if form.validate_on_submit():
        print("### FORM DATA ###", request.form)
        novo_integrador = Integrador(
            nome_empresa=form.nome_empresa.data,
            cnpj=form.cnpj.data,
            email=form.email.data,
            ddd=form.ddd.data,
            telefone=form.telefone.data,
            logradouro=form.logradouro.data,
            numero=form.numero.data,
            complemento=form.complemento.data,
            bairro=form.bairro.data,
            cidade=form.cidade.data,
            estado=form.estado.data.upper() if form.estado.data else None,
            cep=form.cep.data
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

        log_auditoria(
            "CRIACAO",
            tabela_afetada="integradores",
            registro_id=novo_integrador.id,
            detalhes={"dados_novos": {c.name: getattr(novo_integrador, c.name) for c in novo_integrador.__table__.columns}}
        )

        db.session.commit()
        flash("Integrador adicionado com sucesso!", "success")
        return redirect(url_for("main.listar_integradores"))

    return render_template("integradores/form_integradores.html", title="Cadastrar Integrador", form=form, modo="novo")


@bp.route("/integrador/editar/<int:id>", methods=["GET", "POST"])
@login_required
def editar_integrador(id):
    integrador = Integrador.query.get_or_404(id)
    contato_principal = integrador.get_contato_principal() or Contato(is_principal=True, integrador=integrador)
    form = IntegradorForm(obj=integrador)

    if request.method == "GET":
        form.telefone.data = integrador.telefone
        if contato_principal:
            form.nome_contato.data = contato_principal.nome
            form.email_contato.data = contato_principal.email
            form.telefone_contato.data = contato_principal.telefone

    dados_antigos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}

    if form.validate_on_submit():
        integrador.nome_empresa = form.nome_empresa.data
        integrador.cnpj = form.cnpj.data
        integrador.email = form.email.data
        integrador.ddd = form.ddd.data
        integrador.telefone = form.telefone.data
        integrador.logradouro = form.logradouro.data
        integrador.numero = form.numero.data
        integrador.complemento = form.complemento.data
        integrador.bairro = form.bairro.data
        integrador.cidade = form.cidade.data
        integrador.estado = form.estado.data.upper() if form.estado.data else None
        integrador.cep = form.cep.data

        contato_principal.nome = form.nome_contato.data
        contato_principal.email = form.email_contato.data
        contato_principal.telefone = form.telefone_contato.data

        db.session.add(integrador)
        if not contato_principal.id:
            db.session.add(contato_principal)

        dados_novos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}
        log_auditoria("ATUALIZACAO", tabela_afetada="integradores", registro_id=integrador.id,
                      detalhes={"dados_antigos": dados_antigos, "dados_novos": dados_novos})

        db.session.commit()
        flash("Integrador atualizado com sucesso!", "success")
        return redirect(url_for("main.listar_integradores"))

    return render_template("integradores/form_integradores.html", title="Editar Integrador", form=form, modo="editar", integrador=integrador)


@bp.route("/integrador/excluir/<int:id>", methods=["POST"])
@login_required
def excluir_integrador(id):
    integrador = Integrador.query.get_or_404(id)

    contratos_vinculados = Contrato.query.filter_by(integrador_id=id).count()
    if contratos_vinculados > 0:
        flash('Não é possível excluir este integrador. Existem contratos vinculados.', 'danger')
        return redirect(url_for('main.listar_integradores'))

    dados_excluidos = {c.name: getattr(integrador, c.name) for c in integrador.__table__.columns}
    log_auditoria("EXCLUSAO", tabela_afetada="integradores", registro_id=id, detalhes={"dados_excluidos": dados_excluidos})
    db.session.delete(integrador)
    db.session.commit()
    flash(f"Integrador \"{integrador.nome_empresa}\" foi excluído com sucesso.", "success")
    return redirect(url_for("main.listar_integradores"))


# =============================================================================
# CRUD LICENÇAS
# =============================================================================
@bp.route('/licencas')
@login_required
def licencas_lista():
    licencas = Licenca.query.all()
    return render_template('licencas/licencas.html', licencas=licencas)


@bp.route('/licencas/vincular/<int:licenca_id>', methods=['GET', 'POST'])
@login_required
def vincular_chave(licenca_id):
    licenca = Licenca.query.get_or_404(licenca_id)
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

        licenca.contrato_id = contrato.id
        contrato.licenca_id = licenca.id
        contrato.status = "ativo"
        db.session.commit()

        gerar_primeira_fatura(contrato)
        flash('Licença vinculada com sucesso', 'success')
        return redirect(url_for('main.licencas_lista'))

    return render_template('licencas/vincular_chave.html', licenca=licenca, contratos=contratos)


@bp.route('/apagar_licenca/<int:id>', methods=['POST'])
@login_required
def apagar_licenca(id):
    licenca = Licenca.query.get_or_404(id)

    contratos_vinculados = Contrato.query.filter_by(licenca_id=id).count()
    if contratos_vinculados > 0:
        flash('Não é possível excluir esta Licença. Existem contratos vinculados.', 'danger')
        return redirect(url_for('main.licencas_lista'))

    db.session.delete(licenca)
    db.session.commit()
    flash('licença apagada com sucesso.', 'success')
    return redirect(url_for('main.licencas_lista'))



# =============================================================================
# CLIENTES LICENÇAS
# =============================================================================

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


# =============================================================================
# CRUD PRODUTOS
# =============================================================================
@bp.route('/produtos')
@login_required
def lista_produtos():
    produtos = Produto.query.order_by(Produto.nome_produto).all()
    return render_template('produtos/produtos.html', produtos=produtos)


@bp.route('/produtos/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar_produto():
    form = ProdutoForm()

    if form.validate_on_submit():
        produto = Produto(
            nome_produto=form.nome_produto.data,
            descricao=form.descricao.data,
            preco_mensal_base=form.preco_mensal_base.data,
            modulos=[Modulo.query.get(mod_id) for mod_id in form.modulos.data]
        )
        print(form.modulos.data)       # lista de IDs selecionados
        print([m.id for m in produto.modulos])  # módulos atuais do produto

        db.session.add(produto)
        db.session.commit()
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('main.lista_produtos'))

    return render_template('produtos/form_produto.html', form=form, produto=None)



@bp.route('/produtos/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    form = ProdutoForm(obj=produto)

    if form.validate_on_submit():
        produto.nome_produto = form.nome_produto.data
        produto.descricao = form.descricao.data
        produto.preco_mensal_base = form.preco_mensal_base.data
        produto.modulos = [Modulo.query.get(mod_id) for mod_id in form.modulos.data]

        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('main.lista_produtos'))

    if request.method == 'GET':
        form.modulos.data = [m.id for m in produto.modulos]

    return render_template('produtos/form_produto.html', form=form, produto=produto)



@bp.route('/produtos/excluir/<int:produto_id>', methods=['POST'])
@login_required
def excluir_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    db.session.delete(produto)
    db.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('main.lista_produtos'))


# =============================================================================
# CRUD CONTRATOS
# =============================================================================
@bp.route('/contratos')
@login_required
def listar_contratos():
    contratos = Contrato.query.join(Cliente).order_by(Cliente.nome_empresa).all()
    return render_template('contratos/contratos.html', contratos=contratos)

@bp.route('/contrato/novo', methods=['GET', 'POST'])
@login_required
def novo_contrato():
    form = ContratoForm()

    produtos = Produto.query.order_by(Produto.nome_produto).all()
    produtos_modulos = {
        p.id: {
            'valor': float(p.preco_mensal_base or 0),
            'modulos': [{'id': m.id, 'nome': m.nome, 'modulo': m.modulo, 'valor': float(m.valor or 0)} for m in p.modulos]
        } for p in produtos
    }

    # Módulos enviados pelo front (via hidden 'modulos_nomes[]')
    modulos_nomes = request.form.getlist('modulos_nomes[]')

    if form.validate_on_submit():
        contrato = Contrato(
            cliente_id=form.cliente_id.data,
            integrador_id=form.integrador_id.data,
            produto_id=form.produto_id.data,
            dia_faturamento=form.dia_faturamento.data,
            valor_mensal=form.valor_mensal.data,
            status=form.status.data,
            modulos=",".join(modulos_nomes),
            observacoes=form.observacoes.data
        )
        db.session.add(contrato)
        db.session.commit()
        flash('Contrato cadastrado com sucesso!', 'success')
        return redirect(url_for('main.listar_contratos'))

    return render_template(
        'contratos/form_contrato.html',
        form=form,
        produtos_modulos=produtos_modulos,
        modulos_selecionados=[int(m) for m in request.form.getlist('modulos') if m]
    )


@bp.route('/contrato/<int:contrato_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    form = ContratoForm(obj=contrato)

    produtos = Produto.query.order_by(Produto.nome_produto).all()
    produtos_modulos = {
        p.id: {
            'valor': float(p.preco_mensal_base or 0),
            'modulos': [{'id': m.id, 'nome': m.nome, 'modulo': m.modulo, 'valor': float(m.valor or 0)} for m in p.modulos]
        } for p in produtos
    }

    # GET: converte os nomes de módulos do contrato em IDs para pré-seleção
    if request.method == 'GET':
        nomes_modulos = [m.strip() for m in contrato.modulos.split(',') if m.strip()]
        modulos_objetos = Modulo.query.filter(Modulo.modulo.in_(nomes_modulos)).all()
        modulos_selecionados = [m.id for m in modulos_objetos]

        # Popula os campos do form
        form.produto_id.data = contrato.produto_id
        form.cliente_id.data = contrato.cliente_id
        form.integrador_id.data = contrato.integrador_id
        form.dia_faturamento.data = contrato.dia_faturamento
        form.valor_mensal.data = contrato.valor_mensal
        form.status.data = contrato.status
        form.observacoes.data = contrato.observacoes
    else:
        # POST: pega os módulos enviados pelo front
        modulos_selecionados = [m for m in request.form.getlist('modulos') if m]
        modulos_nomes = request.form.getlist('modulos_nomes[]')

    if form.validate_on_submit():
        contrato.cliente_id = form.cliente_id.data
        contrato.integrador_id = form.integrador_id.data
        contrato.produto_id = form.produto_id.data
        contrato.dia_faturamento = form.dia_faturamento.data
        contrato.valor_mensal = form.valor_mensal.data
        contrato.status = form.status.data
        contrato.modulos = ",".join(modulos_nomes)
        contrato.observacoes = form.observacoes.data

        db.session.commit()
        flash('Contrato atualizado com sucesso!', 'success')
        return redirect(url_for('main.listar_contratos'))

    return render_template(
        'contratos/form_contrato.html',
        form=form,
        contrato=contrato,
        produtos_modulos=produtos_modulos,
        modulos_selecionados=modulos_selecionados
    )


@bp.route('/contrato/<int:contrato_id>/excluir', methods=['GET', 'POST'])
@login_required
def excluir_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    
    db.session.delete(contrato)
    db.session.commit()

    flash('Contrato excluído com sucesso!', 'success')
    return redirect(url_for('main.listar_contratos'))


# =============================================================================
# PAGAMENTOS / FATURAS
# =============================================================================
@bp.route('/pagamento/novo/<int:fatura_id>', methods=['GET', 'POST'])
@login_required
def novo_pagamento_fatura(fatura_id):
    fatura = HistoricoPagamentos.query.get_or_404(fatura_id)
    form = PagamentoForm()

    if form.validate_on_submit():
        fatura.valor_pago = fatura.contrato.valor_mensal
        fatura.data_pagamento = date.today()
        fatura.status_boleto = 'pago'
        fatura.observacao = form.observacao.data or 'Fatura gerada automaticamente'

        if fatura.licenca:
            fatura.licenca.data_expiracao = fatura.periodo_referencia_fim
            fatura.licenca.status = 'Ativo'
            db.session.add(fatura.licenca)

        db.session.commit()
        flash('Pagamento registrado e licença ativada com sucesso!', 'success')
        return redirect(url_for('main.ver_faturas', contrato_id=fatura.contrato.id))

    periodo_inicial = fatura.periodo_referencia_inicio.strftime('%d/%m/%Y') if fatura.periodo_referencia_inicio else ''
    periodo_final = fatura.periodo_referencia_fim.strftime('%d/%m/%Y') if fatura.periodo_referencia_fim else ''

    return render_template('pagamentos/novo.html', form=form, periodo_inicial=periodo_inicial, periodo_final=periodo_final, fatura=fatura)


@bp.route('/pagamentos')
@login_required
def pagamentos_lista():
    pagamentos = HistoricoPagamentos.query.order_by(HistoricoPagamentos.data_pagamento.desc()).all()
    return render_template('pagamentos/lista.html', pagamentos=pagamentos)


@bp.route('/contrato/<int:contrato_id>/faturas')
@login_required
def ver_faturas(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    status_filter = request.args.get('status')
    faturas = contrato.historico_pagamentos

    if status_filter == 'pagas':
        faturas = [f for f in faturas if f.status_boleto == 'pago']
    elif status_filter == 'nao_pagas':
        faturas = [f for f in faturas if f.status_boleto != 'pago']

    return render_template('contratos/faturas.html', contrato=contrato, faturas=faturas, status_filter=status_filter)

# LISTAGEM DE MÓDULOS
@bp.route('/modulos')
def lista_modulos():
    termo_busca = request.args.get('busca', '')
    if termo_busca:
        modulos = Modulo.query.filter(Modulo.nome_modulo.ilike(f"%{termo_busca}%")).all()
    else:
        modulos = Modulo.query.all()
    return render_template('modulos/modulos.html', modulos=modulos, termo_busca=termo_busca)

# CADASTRAR MÓDULO
@bp.route('/modulos/cadastrar', methods=['GET', 'POST'])
def cadastrar_modulo():
    form = ModuloForm()
    if form.validate_on_submit():
        novo_modulo = Modulo(
            nome=form.nome.data,
            modulo=form.modulo.data,
            valor=form.valor.data,
            descricao=form.descricao.data
        )
        db.session.add(novo_modulo)
        db.session.commit()
        flash('Módulo cadastrado com sucesso!', 'success')
        return redirect(url_for('main.lista_modulos'))
    return render_template('modulos/form_modulos.html', form=form, modulo=None)

# EDITAR MÓDULO
@bp.route('/modulos/<int:modulo_id>/editar', methods=['GET', 'POST'])
def editar_modulo(modulo_id):
    modulo = Modulo.query.get_or_404(modulo_id)
    form = ModuloForm(obj=modulo)
    if form.validate_on_submit():
        modulo.nome = form.nome.data
        modulo.modulo = form.modulo.data
        modulo.valor = form.valor.data
        modulo.descricao = form.descricao.data
        db.session.commit()
        flash('Módulo atualizado com sucesso!', 'success')
        return redirect(url_for('main.lista_modulos'))
    return render_template('modulos/form_modulos.html', form=form, modulo=modulo)

# EXCLUIR MÓDULO
@bp.route('/modulos/excluir/<int:modulo_id>', methods=['POST'])
def excluir_modulo(modulo_id):
    modulo = Modulo.query.get_or_404(modulo_id)
    db.session.delete(modulo)
    db.session.commit()
    flash('Módulo excluído com sucesso!', 'success')
    return redirect(url_for('main.lista_modulos'))


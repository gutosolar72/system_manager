from app.extensions import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.mysql import LONGTEXT
import json
from datetime import datetime

# --- Modelos Principais ---

class Integrador(db.Model):
    __tablename__ = 'integradores'

    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=True)
    email = db.Column(db.String(255), nullable=True)
    ddd = db.Column(db.String(3), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    logradouro = db.Column(db.String(100), nullable=True)
    numero = db.Column(db.String(20), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    cep = db.Column(db.String(9), nullable=True)
    data_cadastro = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    # Relacionamentos
    contratos = db.relationship('Contrato', back_populates='integrador', lazy=True)
    contatos = db.relationship('Contato', back_populates='integrador', cascade="all, delete-orphan")

    @property
    def endereco_completo(self):
        partes = [
            self.logradouro,
            f"Nº {self.numero}" if self.numero else None,
            self.complemento,
            self.bairro,
            self.cidade,
            self.estado,
            self.cep
        ]
        return ', '.join([p for p in partes if p])

    def get_contato_principal(self):
        for contato in self.contatos:
            if contato.is_principal:
                return contato
        return None


class Cliente(db.Model):
    __tablename__ = 'clientes'

    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=True)
    email = db.Column(db.String(255), nullable=True)
    ddd = db.Column(db.String(3), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    logradouro = db.Column(db.String(100), nullable=True)
    numero = db.Column(db.String(20), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    estado = db.Column(db.String(2), nullable=True)
    cep = db.Column(db.String(9), nullable=True)
    data_cadastro = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    # Relacionamentos
    contatos = db.relationship('Contato', back_populates='cliente', cascade="all, delete-orphan")
    contratos = db.relationship('Contrato', back_populates='cliente', lazy=True)
    licencas = db.relationship('Licenca', back_populates='cliente', lazy=True)

    @property
    def endereco_completo(self):
        partes = [
            self.logradouro,
            f"Nº {self.numero}" if self.numero else None,
            self.complemento,
            self.bairro,
            self.cidade,
            self.estado,
            self.cep
        ]
        return ', '.join([p for p in partes if p])


class Contato(db.Model):
    __tablename__ = 'contatos'
    id = db.Column(db.Integer, primary_key=True)
    integrador_id = db.Column(db.Integer, db.ForeignKey('integradores.id', ondelete='CASCADE'), nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id', ondelete='CASCADE'), nullable=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    departamento = db.Column(db.String(100), nullable=True)
    is_principal = db.Column(db.Boolean, nullable=False, default=False)

    # Relacionamentos
    integrador = db.relationship('Integrador', back_populates='contatos')
    cliente = db.relationship('Cliente', back_populates='contatos')


# ----------------- NOVO: Módulo e associação Produto ↔ Módulo -----------------

produto_modulo = db.Table(
    'produto_modulo',
    db.Column('produto_id', db.Integer, db.ForeignKey('produtos.id', ondelete='CASCADE'), primary_key=True),
    db.Column('modulo_id', db.Integer, db.ForeignKey('modulos.id', ondelete='CASCADE'), primary_key=True)
)

class Modulo(db.Model):
    __tablename__ = 'modulos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    modulo = db.Column(db.String(20), nullable=False)
    descricao = db.Column(db.Text)
    valor = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamento N:N com Produto
    produtos = db.relationship(
        'Produto',
        secondary=produto_modulo,
        back_populates='modulos'
    )


class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome_produto = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco_mensal_base = db.Column(db.Numeric(10, 2), nullable=False)

    # Relacionamentos
    licencas = db.relationship('Licenca', back_populates='produto', lazy=True)
    modulos = db.relationship(
        'Modulo',
        secondary=produto_modulo,
        back_populates='produtos'
    )

class Licenca(db.Model):
    __tablename__ = 'licencas'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=True)
    chave_licenca = db.Column(db.String(255), unique=True, nullable=False)
    uuid = db.Column(db.String(64), nullable=True)
    mac = db.Column(db.String(32), nullable=True)
    mac_gw = db.Column(db.String(17), nullable=True)
    data_ativacao = db.Column(db.TIMESTAMP, nullable=True)
    data_expiracao = db.Column(db.Date, nullable=True)
    ultima_verificacao = db.Column(db.TIMESTAMP, nullable=True)

    # Relacionamentos
    cliente = db.relationship('Cliente', back_populates='licencas')
    produto = db.relationship('Produto', back_populates='licencas')
    contrato = db.relationship('Contrato', back_populates='licenca', uselist=False)  # inverso de Contrato.licenca
    historico_pagamentos = db.relationship('HistoricoPagamentos', back_populates='licenca', lazy=True)


class Contrato(db.Model):
    __tablename__ = 'contratos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    integrador_id = db.Column(db.Integer, db.ForeignKey('integradores.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=True)
    licenca_id = db.Column(db.Integer, db.ForeignKey('licencas.id'), nullable=True)
    local_instalacao = db.Column(db.Text, nullable=True)
    dia_vencimento_boleto = db.Column(db.Integer, nullable=True)
    valor_mensal = db.Column(db.Numeric(10,2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum('pendente','ativo','cancelado'), nullable=False, default='pendente')
    data_criacao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    modulos = db.Column(db.Text)  # continua para compatibilidade com nanosip

    # Relacionamentos
    cliente = db.relationship('Cliente', back_populates='contratos')
    integrador = db.relationship('Integrador', back_populates='contratos')
    licenca = db.relationship('Licenca', back_populates='contrato', uselist=False)
    historico_pagamentos = db.relationship('HistoricoPagamentos', back_populates='contrato', lazy=True)


# ----------------- Usuários e auditoria -----------------

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    hash_senha = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin','financeiro','suporte'), nullable=False, default='suporte')
    data_criacao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.hash_senha = generate_password_hash(password, method='pbkdf2:sha256:1000000')

    def verify_password(self, password):
        return check_password_hash(self.hash_senha, password)

@login.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


class AuditoriaLog(db.Model):
    __tablename__ = 'auditoria_logs'
    id = db.Column(db.BigInteger, primary_key=True)
    timestamp = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)
    tipo_acao = db.Column(db.String(50), nullable=False)
    tabela_afetada = db.Column(db.String(50), nullable=True)
    registro_id = db.Column(db.Integer, nullable=True)
    detalhes = db.Column(LONGTEXT, nullable=True)

    usuario = db.relationship('Usuario', backref='logs_auditoria')

    @property
    def detalhes_dict(self):
        return json.loads(self.detalhes) if self.detalhes else {}

    @detalhes_dict.setter
    def detalhes_dict(self, value):
        self.detalhes = json.dumps(value, ensure_ascii=False)


#class HistoricoPagamentos(db.Model):
#    __tablename__ = 'historico_pagamentos'
#    id = db.Column(db.Integer, primary_key=True)
#    licenca_id = db.Column(db.Integer, db.ForeignKey('licencas.id'), nullable=False)
#    contrato_id = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=True)
#    valor_pago = db.Column(db.Numeric(10, 2), nullable=False)
#    data_pagamento = db.Column(db.Date, nullable=False)
#    periodo_referencia_inicio = db.Column(db.Date, nullable=False)
#    periodo_referencia_fim = db.Column(db.Date, nullable=False)
#    observacao = db.Column(db.Text)
#
#    # Campos CNAB 240 / Boleto
#    nosso_numero = db.Column(db.String(20))
#    numero_documento = db.Column(db.String(20))
#    linha_digitavel = db.Column(db.String(60))
#    codigo_banco = db.Column(db.String(3))
#    status_boleto = db.Column(db.Enum('emitido', 'pago', 'cancelado', 'erro', 'pendente'), default='pendente')
#    data_emissao = db.Column(db.Date)
#    data_vencimento = db.Column(db.Date)
#    data_credito = db.Column(db.Date)
#
#    # Relacionamentos
#    licenca = db.relationship('Licenca', back_populates='historico_pagamentos')
#    contrato = db.relationship('Contrato', back_populates='historico_pagamentos')
#
#    def __repr__(self):
#        return f"<Pagamento {self.id} | Licença {self.licenca_id} | Valor {self.valor_pago}>"
#
#    @property
#    def pago(self):
#        return self.status_boleto == 'pago'
#
#    @property
#    def em_aberto(self):
#        return self.status_boleto in ('emitido', 'pendente')
#

class HistoricoPagamentos(db.Model):
    __tablename__ = 'historico_pagamentos'

    id = db.Column(db.Integer, primary_key=True)

    # --- Gateway de pagamento (agnóstico) ---
    gateway = db.Column(db.String(30))  # ex: 'asaas'
    gateway_payment_id = db.Column(db.String(64), index=True)
    gateway_invoice_id = db.Column(db.String(64))
    gateway_payload = db.Column(db.JSON)

    licenca_id = db.Column(db.Integer, db.ForeignKey('licencas.id'), nullable=False)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=True)

    valor_pago = db.Column(db.Numeric(10, 2), nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)
    periodo_referencia_inicio = db.Column(db.Date, nullable=False)
    periodo_referencia_fim = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.Text)

    # Campos bancários / boleto (domínio financeiro)
    nosso_numero = db.Column(db.String(20))
    numero_documento = db.Column(db.String(20))
    linha_digitavel = db.Column(db.String(60))
    codigo_banco = db.Column(db.String(3))
    status_boleto = db.Column(
        db.Enum('emitido', 'pago', 'cancelado', 'erro', 'pendente'),
        default='pendente'
    )
    data_emissao = db.Column(db.Date)
    data_vencimento = db.Column(db.Date)
    data_credito = db.Column(db.Date)

    # Relacionamentos
    licenca = db.relationship('Licenca', back_populates='historico_pagamentos')
    contrato = db.relationship('Contrato', back_populates='historico_pagamentos')

    def __repr__(self):
        return f"<Pagamento {self.id} | Licença {self.licenca_id} | Valor {self.valor_pago}>"

    @property
    def pago(self):
        return self.status_boleto == 'pago'

    @property
    def em_aberto(self):
        return self.status_boleto in ('emitido', 'pendente')

class ClienteGateway(db.Model):
    __tablename__ = 'clientes_gateway'

    id = db.Column(db.Integer, primary_key=True)

    # Relacionamento interno
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('clientes.id', ondelete='CASCADE'),
        nullable=False
    )

    # Gateway (agnóstico)
    gateway = db.Column(db.String(30), nullable=False)  # ex: 'asaas'
    ambiente = db.Column(db.Enum('sandbox', 'producao'), nullable=False)

    gateway_customer_id = db.Column(db.String(64), nullable=False, index=True)
    gateway_payload = db.Column(db.JSON)

    criado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relacionamento ORM
    cliente = db.relationship('Cliente', backref=db.backref(
        'gateways',
        lazy=True,
        cascade='all, delete-orphan'
    ))

    __table_args__ = (
        db.UniqueConstraint(
            'gateway',
            'ambiente',
            'gateway_customer_id',
            name='uq_gateway_customer'
        ),
    )

    def __repr__(self):
        return (
            f"<ClienteGateway cliente={self.cliente_id} "
            f"gateway={self.gateway} ambiente={self.ambiente}>"
        )


from app.extensions import db, login # Importa db e login de app.extensions
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.mysql import LONGTEXT
import json

# --- Modelos Principais ---

class Integrador(db.Model):
    __tablename__ = 'integradores'
    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=True)
    endereco = db.Column(db.String(255), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    cep = db.Column(db.String(9), nullable=True)  # CAMPO ADICIONADO
    telefone = db.Column(db.String(20), nullable=True)
    data_cadastro = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    # Relacionamentos
    clientes = db.relationship('Cliente', backref='integrador', lazy=True)
    contatos = db.relationship('Contato', back_populates='integrador', cascade="all, delete-orphan")

    def get_contato_principal(self):
        """Retorna o contato principal do integrador."""
        for contato in self.contatos:
            if contato.is_principal:
                return contato
        return None

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    integrador_id = db.Column(db.Integer, db.ForeignKey('integradores.id'), nullable=False)
    nome_empresa = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=True)
    endereco = db.Column(db.String(255), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    cidade = db.Column(db.String(100), nullable=True)
    uf = db.Column(db.String(2), nullable=True)
    cep = db.Column(db.String(9), nullable=True)  # CAMPO ADICIONADO
    telefone = db.Column(db.String(20), nullable=True)
    data_cadastro = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    # Relacionamentos
    contatos = db.relationship('Contato', back_populates='cliente', cascade="all, delete-orphan")
    licencas = db.relationship('Licencas', backref='cliente', lazy=True)

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

class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome_produto = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    preco_mensal_base = db.Column(db.Numeric(10, 2), nullable=False)
    modulos_inclusos = db.Column(db.Text, nullable=False) # JSON como string

    # Relacionamento
    licencas = db.relationship('Licencas', backref='produto', lazy=True)

    @property
    def modulos(self):
        return json.loads(self.modulos_inclusos) if self.modulos_inclusos else []

    @modulos.setter
    def modulos(self, value):
        self.modulos_inclusos = json.dumps(value)

class Licencas(db.Model):
    __tablename__ = 'licencas'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    chave_licenca = db.Column(db.String(255), unique=True, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum('pendente', 'ativo', 'bloqueado'), nullable=False, default='pendente')
    dia_faturamento = db.Column(db.Integer, nullable=False)
    data_ativacao = db.Column(db.TIMESTAMP, nullable=True)
    data_expiracao = db.Column(db.Date, nullable=True)
    ultima_verificacao = db.Column(db.TIMESTAMP, nullable=True)
    modulos_override = db.Column(db.Text, nullable=True) # JSON como string

    # Relacionamentos
    pagamentos = db.relationship('HistoricoPagamento', backref='licenca', lazy=True)

    @property
    def modulos_custom(self):
        return json.loads(self.modulos_override) if self.modulos_override else None

    @modulos_custom.setter
    def modulos_custom(self, value):
        self.modulos_override = json.dumps(value)

class HistoricoPagamento(db.Model):
    __tablename__ = 'historico_pagamentos'
    id = db.Column(db.Integer, primary_key=True)
    licenca_id = db.Column(db.Integer, db.ForeignKey('licencas.id'), nullable=False)
    valor_pago = db.Column(db.Numeric(10, 2), nullable=False)
    data_pagamento = db.Column(db.Date, nullable=False)
    periodo_referencia_inicio = db.Column(db.Date, nullable=False)
    periodo_referencia_fim = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.Text, nullable=True)

# --- Modelos de Suporte e Autenticação ---

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    hash_senha = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'financeiro', 'suporte'), nullable=False, default='suporte')
    data_criacao = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.hash_senha = generate_password_hash(password, method='pbkdf2:sha256:1000000')

    def verify_password(self, password):
        return check_password_hash(self.hash_senha, password)

@login.user_loader # Usa login.user_loader
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
    detalhes = db.Column(LONGTEXT, nullable=True) # JSON como string

    # Relacionamento
    usuario = db.relationship('Usuario', backref='logs_auditoria')

    @property
    def detalhes_dict(self):
        return json.loads(self.detalhes) if self.detalhes else {}

    @detalhes_dict.setter
    def detalhes_dict(self, value):
        self.detalhes = json.dumps(value, ensure_ascii=False)


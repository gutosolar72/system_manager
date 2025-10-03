# /deploy/system_manager/app/models.py

from .extensions import db, login 
from datetime import datetime
from flask_login import UserMixin

@login.user_loader
def load_user(id):
    try:
        user_id = int(id)
    except (ValueError, TypeError):
        return None
    return db.session.get(Usuario, user_id)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    hash_senha = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'financeiro', 'suporte'), nullable=False, default='suporte')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    logs = db.relationship('AuditoriaLog', backref='usuario', lazy='dynamic')

class AuditoriaLog(db.Model):
    __tablename__ = 'auditoria_logs'
    id = db.Column(db.BigInteger, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    tipo_acao = db.Column(db.String(50), nullable=False)
    tabela_afetada = db.Column(db.String(50))
    registro_id = db.Column(db.Integer)
    detalhes = db.Column(db.JSON)

class Integrador(db.Model):
    __tablename__ = 'integradores'
    id = db.Column(db.Integer, primary_key=True)
    nome_empresa = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    endereco = db.Column(db.String(255))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    telefone = db.Column(db.String(20))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    clientes = db.relationship('Cliente', backref='integrador', lazy='dynamic')
    contatos = db.relationship('Contato', backref='integrador', lazy='dynamic')

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    integrador_id = db.Column(db.Integer, db.ForeignKey('integradores.id'), nullable=False)
    nome_empresa = db.Column(db.String(255), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    endereco = db.Column(db.String(255))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    telefone = db.Column(db.String(20))
    dia_faturamento = db.Column(db.Integer, nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    equipamentos = db.relationship('Equipamento', backref='cliente', lazy='dynamic')
    contatos = db.relationship('Contato', backref='cliente', lazy='dynamic')

class Contato(db.Model):
    __tablename__ = 'contatos'
    id = db.Column(db.Integer, primary_key=True)
    integrador_id = db.Column(db.Integer, db.ForeignKey('integradores.id'))
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    telefone = db.Column(db.String(20))
    departamento = db.Column(db.String(100))
    is_principal = db.Column(db.Boolean, default=False, nullable=False)

class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome_produto = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.Text)
    preco_mensal_base = db.Column(db.Numeric(10, 2), nullable=False)
    modulos_inclusos = db.Column(db.JSON, nullable=False)

    equipamentos = db.relationship('Equipamento', backref='produto', lazy='dynamic')

class Equipamento(db.Model):
    __tablename__ = 'equipamentos'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    chave_licenca = db.Column(db.String(255), unique=True, nullable=False)
    descricao = db.Column(db.String(255))
    status = db.Column(db.Enum('pendente', 'ativo', 'bloqueado'), nullable=False, default='pendente')
    data_ativacao = db.Column(db.DateTime)
    data_expiracao = db.Column(db.Date)
    ultima_verificacao = db.Column(db.DateTime)
    modulos_override = db.Column(db.JSON)

    pagamentos = db.relationship('HistoricoPagamento', backref='equipamento', lazy='dynamic')

class HistoricoPagamento(db.Model):
    __tablename__ = 'historico_pagamentos'
    id = db.Column(db.Integer, primary_key=True)
    equipamento_id = db.Column(db.Integer, db.ForeignKey('equipamentos.id'), nullable=False)
    valor_pago = db.Column(db.Numeric(10, 2), nullable=False)
    data_pagamento = db.Column(db.Date, nullable=False)
    periodo_referencia_inicio = db.Column(db.Date, nullable=False)
    periodo_referencia_fim = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.Text)



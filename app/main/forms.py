from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField, IntegerField, DecimalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, ValidationError, Regexp
from app.models import Integrador, Usuario # Importar modelos de app.models

# --- Formulários de Autenticação ---

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Length(1, 255), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Login')

# --- Formulários de Cadastro ---

class ClienteForm(FlaskForm):
    # Dados da Empresa
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired(), Length(max=255)])
    cnpj = StringField('CNPJ', validators=[Optional(), Length(max=18)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    
    # Endereço
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    bairro = StringField('Bairro', validators=[Optional(), Length(max=100)])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=100)])
    uf = SelectField('UF', choices=[
        ('', 'Selecione...'), ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'), ('BA', 'BA'), 
        ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'), ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), 
        ('MS', 'MS'), ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'), ('PE', 'PE'), 
        ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'), ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), 
        ('SC', 'SC'), ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO')
    ], validators=[Optional()])
    cep = StringField('CEP', validators=[Optional(), Length(max=9)]) # CAMPO ADICIONADO

    # Configurações
    #integrador_id = SelectField('Integrador Responsável', coerce=int, validators=[DataRequired()])
    
    submit = SubmitField('Salvar')

    #def __init__(self, *args, **kwargs):
    #    super(ClienteForm, self).__init__(*args, **kwargs)
    #    # Popula o campo de seleção de integradores
    #    self.integrador_id.choices = [(i.id, i.nome_empresa) for i in Integrador.query.order_by(Integrador.nome_empresa).all()]

    def validate_cnpj(self, field):
        if field.data:
            cnpj_limpo = ''.join(filter(str.isdigit, field.data))
            if len(cnpj_limpo) != 14:
                raise ValidationError('CNPJ deve ter 14 dígitos.')


class IntegradorForm(FlaskForm):
    # Dados da Empresa
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired(), Length(max=255)])
    cnpj = StringField('CNPJ', validators=[Optional(), Length(max=18)])
    telefone = StringField('Telefone da Empresa', validators=[Optional(), Length(max=20)]) # Renomeado de telefone_empresa para telefone

    # Endereço
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    bairro = StringField('Bairro', validators=[Optional(), Length(max=100)])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=100)])
    uf = SelectField('UF', choices=[
        ('', 'Selecione...'), ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'), ('BA', 'BA'), 
        ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'), ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'), 
        ('MS', 'MS'), ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'), ('PE', 'PE'), 
        ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'), ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'), 
        ('SC', 'SC'), ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO')
    ], validators=[Optional()])
    cep = StringField('CEP', validators=[Optional(), Length(max=9)]) # CAMPO ADICIONADO

    # Contato Principal
    nome_contato = StringField('Nome do Contato', validators=[DataRequired(), Length(max=255)])
    email_contato = StringField('Email do Contato', validators=[DataRequired(), Email(), Length(max=255)])
    telefone_contato = StringField('Telefone do Contato', validators=[Optional(), Length(max=20)])

    submit = SubmitField('Salvar')

    def validate_cnpj(self, field):
        if field.data:
            cnpj_limpo = ''.join(filter(str.isdigit, field.data))
            if len(cnpj_limpo) != 14:
                raise ValidationError('CNPJ deve ter 14 dígitos.')

    def validate_email_contato(self, field):
        pass

class ProdutoForm(FlaskForm):
    nome_produto = StringField('Nome do Produto', validators=[DataRequired()])
    sku = StringField('SKU', validators=[DataRequired()])
    descricao = TextAreaField('Descrição')
    preco_mensal_base = DecimalField('Preço Mensal Base', validators=[DataRequired()])
    modulos_inclusos = TextAreaField('Módulos Inclusos (JSON)')
    submit = SubmitField('Salvar')

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField, IntegerField, DecimalField, DateField
from wtforms.validators import DataRequired, Length, Email, Optional, ValidationError
from .models import Integrador, Cliente, Contrato

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
    cep = StringField('CEP', validators=[Optional(), Length(max=9)])

    submit = SubmitField('Salvar')

    def validate_cnpj(self, field):
        if field.data:
            cnpj_limpo = ''.join(filter(str.isdigit, field.data))
            if len(cnpj_limpo) != 14:
                raise ValidationError('CNPJ deve ter 14 dígitos.')

class IntegradorForm(FlaskForm):
    # Dados da Empresa
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired(), Length(max=255)])
    cnpj = StringField('CNPJ', validators=[Optional(), Length(max=18)])
    telefone_empresa = StringField('Telefone da Empresa', validators=[Optional(), Length(max=20)])

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
    cep = StringField('CEP', validators=[Optional(), Length(max=9)])

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
        pass  # Placeholder para futura validação

# --- Formulário de Contrato ---

class ContratoForm(FlaskForm):
    cliente_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    integrador_id = SelectField('Integrador', coerce=int, validators=[DataRequired()])
    licenca_id = SelectField('Licença', coerce=int, validators=[Optional()])
    data_faturamento = DateField('Data de Faturamento', validators=[Optional()])
    valor_mensal = DecimalField('Valor Mensal', validators=[Optional()])
    status = SelectField('Status', choices=[('pendente','Pendente'),('ativo','Ativo'),('cancelado','Cancelado')], validators=[DataRequired()])
    observacoes = TextAreaField('Observações', validators=[Optional()])
    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(ContratoForm, self).__init__(*args, **kwargs)
        self.cliente_id.choices = [(c.id, c.nome_empresa) for c in Cliente.query.order_by(Cliente.nome_empresa).all()]
        self.integrador_id.choices = [(i.id, i.nome_empresa) for i in Integrador.query.order_by(Integrador.nome_empresa).all()]
        # Licença será opcional e carregada dinamicamente conforme cliente ou produto
        self.licenca_id.choices = [(0, 'Selecione...')]  # Placeholder inicial


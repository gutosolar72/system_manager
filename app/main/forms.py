from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField, IntegerField, DecimalField, DateField, HiddenField, SelectMultipleField, widgets 
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, ValidationError, Regexp, NumberRange
from app.models import Cliente, Integrador, Usuario, Licenca, Produto, Modulo  # Importar modelos de app.models

# --- Formulários de Autenticação ---

class LoginForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Length(1, 255), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Login')


# --- Formulários de Cadastro ---

class ClienteForm(FlaskForm):
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired(), Length(max=255)])
    cnpj = StringField('CNPJ', validators=[Optional(), Length(max=18)])
    email = StringField('E-mail', validators=[Optional(), Length(max=255)])
    ddd = StringField('DDD', validators=[Optional(), Length(max=3)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    logradouro = StringField('Logradouro', validators=[Optional(), Length(max=100)])
    numero = StringField('Número', validators=[Optional(), Length(max=20)])
    complemento = StringField('Complemento', validators=[Optional(), Length(max=100)])
    bairro = StringField('Bairro', validators=[Optional(), Length(max=100)])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=100)])
    estado = SelectField('UF', choices=[
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
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired(), Length(max=255)])
    cnpj = StringField('CNPJ', validators=[Optional(), Length(max=18)])
    email = StringField('Email da Empresa', validators=[Optional(), Email(), Length(max=255)])
    ddd = StringField('DDD', validators=[Optional(), Length(max=3)])
    telefone = StringField('Telefone da Empresa', validators=[Optional(), Length(max=20)])
    logradouro = StringField('Logradouro', validators=[Optional(), Length(max=100)])
    numero = StringField('Número', validators=[Optional(), Length(max=20)])
    complemento = StringField('Complemento', validators=[Optional(), Length(max=100)])
    bairro = StringField('Bairro', validators=[Optional(), Length(max=100)])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=100)])
    estado = SelectField('Estado', choices=[
        ('', 'Selecione...'), ('AC', 'AC'), ('AL', 'AL'), ('AP', 'AP'), ('AM', 'AM'), ('BA', 'BA'),
        ('CE', 'CE'), ('DF', 'DF'), ('ES', 'ES'), ('GO', 'GO'), ('MA', 'MA'), ('MT', 'MT'),
        ('MS', 'MS'), ('MG', 'MG'), ('PA', 'PA'), ('PB', 'PB'), ('PR', 'PR'), ('PE', 'PE'),
        ('PI', 'PI'), ('RJ', 'RJ'), ('RN', 'RN'), ('RS', 'RS'), ('RO', 'RO'), ('RR', 'RR'),
        ('SC', 'SC'), ('SP', 'SP'), ('SE', 'SE'), ('TO', 'TO')
    ], validators=[Optional()])
    cep = StringField('CEP', validators=[Optional(), Length(max=9)])
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
    descricao = TextAreaField('Descrição')
    preco_mensal_base = DecimalField('Preço Mensal Base', validators=[DataRequired()])
    modulos = SelectMultipleField(
        'Módulos do Produto',
        coerce=int,
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False)
    )
    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(ProdutoForm, self).__init__(*args, **kwargs)
        self.modulos.choices = [(m.id, m.nome) for m in Modulo.query.order_by(Modulo.nome).all()]


class ModuloForm(FlaskForm):
    nome = StringField('Nome do Módulo', validators=[DataRequired(), Length(max=100)])
    modulo = StringField('Funcionalidade', validators=[DataRequired(), Length(max=20)])
    descricao = TextAreaField('Descrição', validators=[Optional()])
    valor = DecimalField('Valor', validators=[Optional()])
    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super(ModuloForm, self).__init__(*args, **kwargs)

def coerce_int_or_none(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

class ContratoForm(FlaskForm):
    cliente_id = SelectField('Cliente', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione um cliente")]
    )
    integrador_id = SelectField('Integrador', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione um integrador")]
    )
    produto_id = SelectField('Produto', coerce=coerce_int_or_none, validators=[DataRequired(message="Selecione um Produto")])
    
    local_instalacao = StringField('Local de Instalação', validators=[Optional()])
    dia_vencimento_boleto = IntegerField('Dia Vencimento Boleto', default=25, validators=[Optional(), NumberRange(min=1, max=31)])
    valor_mensal = DecimalField('Valor Mensal', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('pendente', 'Pendente'),
        ('ativo', 'Ativo'),
        ('cancelado', 'Cancelado')
    ], validators=[DataRequired()])
    modulos = HiddenField()
    observacoes = TextAreaField('Observações', validators=[Optional()])
    submit = SubmitField('Salvar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cliente_id.choices = [("", 'Selecione um cliente')] + [
            (c.id, c.nome_empresa) for c in Cliente.query.order_by(Cliente.nome_empresa).all()
        ]
        self.integrador_id.choices = [("", 'Selecione um integrador')] + [
            (i.id, i.nome_empresa) for i in Integrador.query.order_by(Integrador.nome_empresa).all()
        ]
        self.produto_id.choices = [("", 'Selecione um produto')] + [
            (p.id, p.nome_produto) for p in Produto.query.order_by(Produto.nome_produto).all()
        ]

class PagamentoForm(FlaskForm):
    observacao = TextAreaField('Observação', validators=[Optional()])
    submit = SubmitField('Salvar Pagamento')


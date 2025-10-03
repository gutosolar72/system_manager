# /deploy/system_manager/app/main/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange

class LoginForm(FlaskForm):
    """Formulário de login para os usuários."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class ClienteForm(FlaskForm):
    """Formulário completo para criar ou editar um Cliente."""
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired(), Length(min=3, max=255)])
    cnpj = StringField('CNPJ', validators=[DataRequired(), Length(min=14, max=18)])
    telefone = StringField('Telefone', validators=[DataRequired(), Length(min=10, max=15)])
    
    endereco = StringField('Endereço (Rua, Nº)', validators=[DataRequired(), Length(max=255)])
    bairro = StringField('Bairro', validators=[DataRequired(), Length(max=100)])
    cidade = StringField('Cidade', validators=[DataRequired(), Length(max=100)])
    uf = StringField('UF', validators=[DataRequired(), Length(min=2, max=2)])
    
    dia_faturamento = IntegerField(
        'Dia do Faturamento', 
        validators=[DataRequired(), NumberRange(min=1, max=31, message="O dia deve ser entre 1 e 31.")]
    )
    
    submit = SubmitField('Salvar Cliente')

class IntegradorForm(FlaskForm):
    """Formulário para criar ou editar um Integrador."""
    nome_empresa = StringField('Nome da Empresa', validators=[DataRequired(), Length(min=3, max=255)])
    cnpj = StringField('CNPJ', validators=[DataRequired(), Length(min=14, max=18)])
    telefone = StringField('Telefone Principal', validators=[DataRequired(), Length(min=10, max=15)])
    endereco = StringField('Endereço (Rua, Nº)', validators=[Length(max=255)])
    bairro = StringField('Bairro', validators=[Length(max=100)])
    cidade = StringField('Cidade', validators=[Length(max=100)])
    uf = StringField('UF', validators=[Length(min=2, max=2)])

    contato_nome = StringField('Nome do Contato Principal', validators=[DataRequired(), Length(max=100)])
    contato_email = StringField('Email do Contato', validators=[DataRequired(), Email(), Length(max=100)])
    contato_telefone = StringField('Telefone do Contato (Opcional)', validators=[Length(max=15)])
    
    submit = SubmitField('Salvar Integrador')

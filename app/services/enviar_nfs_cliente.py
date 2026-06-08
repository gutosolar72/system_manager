#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: enviar_nfs.py
Envia NFS-e e boleto por email para os clientes com notas autorizadas e ainda não enviadas.
"""
import sys
import os
import re
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import unicodedata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db
from app.models import HistoricoPagamentos

# --- Configuração do Gmail
GMAIL_USER = "nanosipconnect@gmail.com"
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "acvi vrzy ykqd nkpb")  # mova para .env

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}


def parsear_emails(email_str):
    """Suporta separadores: vírgula, ponto e vírgula, espaço."""
    if not email_str:
        return []
    emails = re.split(r'[;,\s]+', email_str.strip())
    return [e.strip() for e in emails if e.strip() and '@' in e]

def slugify(texto):
    """Remove acentos, caracteres especiais e substitui espaços por underscore."""
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'[^\w\s-]', '', texto).strip()
    return re.sub(r'\s+', '_', texto)

#def slugify(texto):
#    """Remove caracteres especiais e substitui espaços por underscore."""
#    texto = re.sub(r'[^\w\s-]', '', texto or '').strip()
#    return re.sub(r'\s+', '_', texto)


def montar_nome_nf(local_instalacao, periodo_inicio):
    mes = str(periodo_inicio.month).zfill(2)
    ano = periodo_inicio.year
    return f"NFs_NanoSIP_{slugify(local_instalacao)}_ref_{mes}-{ano}.pdf"


def montar_nome_boleto(local_instalacao, periodo_inicio):
    mes = str(periodo_inicio.month).zfill(2)
    ano = periodo_inicio.year
    return f"Boleto_NanoSIP_{slugify(local_instalacao)}_ref_{mes}-{ano}.pdf"


def baixar_pdf(url):
    """Baixa o PDF e retorna os bytes."""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def enviar_email(destinatarios, local_instalacao, periodo_inicio, anexos):
    """
    anexos: lista de tuplas (nome_arquivo, bytes)
    """
    mes_ano = f"{MESES_PT[periodo_inicio.month]}/{periodo_inicio.year}"

    msg = MIMEMultipart()
    msg['From']    = GMAIL_USER
    msg['To']      = ', '.join(destinatarios)
    msg['Subject'] = f"NFS-e e Boleto NanoSIP — {local_instalacao} — {mes_ano}"

    corpo = f"""Olá,

Seguem em anexo a Nota Fiscal de Serviços Eletrônica (NFS-e) e o boleto referentes ao mês de {mes_ano}.

Em caso de dúvidas, entre em contato conosco.

Atenciosamente,
NanoSIP Connect
nanosipconnect@gmail.com
"""
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))

    for nome_arquivo, pdf_bytes in anexos:
        parte = MIMEBase('application', 'octet-stream')
        parte.set_payload(pdf_bytes)
        encoders.encode_base64(parte)
        #parte.add_header('Content-Disposition', f'attachment; filename="{nome_arquivo}"')
        parte.add_header('Content-Disposition', 'attachment', filename=nome_arquivo)
        parte.add_header('Content-Type', 'application/pdf', name=nome_arquivo)
        msg.attach(parte)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_PASS)
        smtp.sendmail(GMAIL_USER, destinatarios, msg.as_string())


def enviar_nfs():
    app = create_app()
    with app.app_context():

        pagamentos = HistoricoPagamentos.query.filter(
            HistoricoPagamentos.nf_status == 'AUTHORIZED',
            HistoricoPagamentos.nf_pdf_url.isnot(None),
            HistoricoPagamentos.nf_enviada_email == False
        ).all()

        if not pagamentos:
            print("Nenhuma NF pendente de envio.")
            return

        enviados = 0
        erros    = 0

        for pag in pagamentos:
            try:
                cliente           = pag.contrato.cliente
                local_instalacao  = pag.contrato.local_instalacao or cliente.nome_empresa
                emails            = parsear_emails(cliente.email)

                if not emails:
                    print(f"⚠️  Sem email — {local_instalacao} (pagamento {pag.id})")
                    continue

                anexos = []

                # --- NFS-e
                nome_nf = montar_nome_nf(local_instalacao, pag.periodo_referencia_inicio)
                print(f"📥 Baixando NF: {pag.nf_pdf_url}")
                anexos.append((nome_nf, baixar_pdf(pag.nf_pdf_url)))

                # --- Boleto
                bank_slip_url = (pag.gateway_payload or {}).get('bankSlipUrl')
                if bank_slip_url:
                    nome_boleto = montar_nome_boleto(local_instalacao, pag.periodo_referencia_inicio)
                    print(f"📥 Baixando boleto: {bank_slip_url}")
                    anexos.append((nome_boleto, baixar_pdf(bank_slip_url)))
                else:
                    print(f"⚠️  Boleto não encontrado para pagamento {pag.id}")

                print(f"📧 Enviando para {emails}")
                enviar_email(
                    destinatarios=emails,
                    local_instalacao=local_instalacao,
                    periodo_inicio=pag.periodo_referencia_inicio,
                    anexos=anexos
                )

                pag.nf_enviada_email = True
                db.session.commit()
                print(f"✅ Enviado: {nome_nf}")
                enviados += 1

            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro no pagamento {pag.id}: {e}")
                erros += 1

        print(f"\n📊 Enviados: {enviados} | Erros: {erros}")


if __name__ == '__main__':
    enviar_nfs()

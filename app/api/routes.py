from flask import request, jsonify
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models import Licenca, Produto, Contrato
import hashlib
import subprocess

from app.api import bp_api
    
BR_TZ = timezone(timedelta(hours=-3))
now = datetime.now(BR_TZ)

@bp_api.route('/ativar_licenca', methods=['POST'])
def ativar_licenca():
    """
    Recebe JSON:
    {
        "uuid": "...",
        "mac": "...",
        "mac_gw": "...",
        "chave_licenca": "...",
        "produto": "...",
    }
    """
    data = request.get_json()
    uuid = data.get('uuid')
    mac = data.get('mac')
    mac_gw = data.get('mac_gw')
    chave_licenca = data.get('chave_licenca')
    produto_nome = data.get('produto')

    if not uuid or not mac or not chave_licenca or not produto_nome or not mac_gw:
        return jsonify({'status': 'erro', 'mensagem': 'Campos obrigatórios ausentes'}), 400

    # Recalcula o hash esperado da chave_licenca
    combined = f"UUID:{uuid}|MAC:{mac}"
    hash_esperado = hashlib.sha256(combined.encode('utf-8')).hexdigest().upper()

    if chave_licenca != hash_esperado:
        return jsonify({'status': 'erro', 'mensagem': 'Chave da licença inválida'}), 403

    # Busca produto
    produto = Produto.query.filter_by(nome_produto=produto_nome).first()
    if not produto:
        return jsonify({'status': 'erro', 'mensagem': 'Produto não encontrado'}), 404

    # Busca licença existente
    licenca = Licenca.query.filter_by(chave_licenca=chave_licenca).first()
    if not licenca:
        # Cria nova licença
        licenca = Licenca(
            produto_id=produto.id,
            chave_licenca=chave_licenca,
            uuid=uuid,
            mac=mac,
            mac_gw=mac_gw,
            data_ativacao=now,
            ultima_verificacao=now
        )
        db.session.add(licenca)
        db.session.commit()  # commit para gerar ID e permitir vincular contrato depois
    if licenca.mac_gw != mac_gw:
        return jsonify({'status': 'erro', 'mensagem': 'Licença inválida para esta rede'}), 401    

    # Busca contrato vinculado, se houver
    contrato = Contrato.query.filter_by(licenca_id=licenca.id).first()

    return jsonify({
        'status': contrato.status if contrato else None,
        'valid_until': licenca.data_expiracao.isoformat() if licenca.data_expiracao else None,
        'modulos': contrato.modulos if contrato else None
    }), 200


@bp_api.route('/remote_access', methods=['POST'])
def remote_access():
    """
    NanoSIP envia:
    {
       "chave_licenca": "...",
       "has_wg": true|false,
       "public_key": "..."
    }
    """
    import subprocess
    import os

    WG_SERVER_ENDPOINT = "gerenciamento.nanosip.com.br:51820"
    WG_ALLOWED_IPS = "10.10.0.0/16"
    WG_CONF_FILE = "/etc/wireguard/wg0.conf"
    server_public_key = "2keiZtuQYmQ/A1Y/JvAhhF80xzKloHrBipqj74Fn8gQ="

    data = request.get_json() or {}

    chave_licenca = data.get("chave_licenca")
    has_wg = data.get("has_wg", False)
    peer_public_key = data.get("public_key")

    # 1. Já existe WireGuard configurado
    if has_wg:
        return jsonify({"message": "Configuração WireGuard já existe"}), 200

    # 2. Valida campos obrigatórios
    if not chave_licenca:
        return jsonify({"error": "chave_licenca é obrigatório"}), 400
    if not peer_public_key:
        return jsonify({"error": "public_key é obrigatório"}), 400

    # 3. Buscar licença no banco
    licenca = Licenca.query.filter_by(chave_licenca=chave_licenca).first()
    if not licenca:
        return jsonify({"authorized": False, "message": "Licença não encontrada"}), 404

    # 4. Calcular IP único do peer
    max_hosts_per_block = 254
    bloco = (licenca.id // max_hosts_per_block) % 256
    host  = (licenca.id % max_hosts_per_block) + 1
    wg_address = f"10.10.{bloco}.{host}/32"

    # Adicionar peer dinamicamente



    result = subprocess.run(
        ["/usr/bin/sudo", "wg", "set", "wg0", "peer", peer_public_key, "allowed-ips", wg_address],
        capture_output=True, text=True
    )
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)

#    subprocess.run(["/usr/bin/sudo", "wg-quick", "down", "wg0"], check=True)
#    subprocess.run(["/usr/bin/sudo", "wg-quick", "up", "wg0"], check=True)

    peer_block = f"\n[Peer]\n#Chave_Licenca = {chave_licenca}\nPublicKey = {peer_public_key}\nAllowedIPs = {wg_address}\n"

    subprocess.run(
        f"echo '{peer_block}' | /usr/bin/sudo tee -a /etc/wireguard/wg0.conf",
        shell=True,
        check=True
    )

    subprocess.run(["/usr/bin/sudo", "systemctl", "restart", "wg-quick@wg0.service"], check=True)

    # Retornar configuração para o NanoSIP
    response = {
        "authorized": True,
        "has_wg": True,
        "wg_config": {
            "address": wg_address,
            "private_key": None,       # NanoSIP gera localmente
            "server_public_key": server_public_key,
            "endpoint": WG_SERVER_ENDPOINT,
            "allowed_ips": WG_ALLOWED_IPS
        }
    }

    return jsonify(response), 200
@bp_api.route('/asaas/webhook', methods=['POST'])
def asaas_webhook():
    """
    Recebe eventos do Asaas.
    Eventos tratados:
      - PAYMENT_RECEIVED/CONFIRMED → marca boleto como pago + atualiza licença
      - PAYMENT_OVERDUE            → marca boleto como vencido
      - INVOICE_AUTHORIZED         → salva pdf/xml da NF emitida
      - INVOICE_CANCELED           → limpa pdf/xml da NF cancelada
      - INVOICE_ERROR              → loga erro da NF na prefeitura

    Lógica de atualização da licença (data_expiracao):
      - Tem faturas em aberto não pagas?
          → SIM → data_expiracao = vencimento da mais antiga em aberto + 1 mês
          → NÃO → data_expiracao = vencimento da fatura paga mais recente + 1 mês
    """
    from app.models import HistoricoPagamentos
    from app.integrations.asaas.mapper import map_webhook_event
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    import os

    token = request.headers.get("asaas-access-token")
    if token != os.getenv("ASAAS_WEBHOOK_TOKEN"):
        return jsonify({"status": "unauthorized"}), 401

    payload = request.get_json() or {}
    event   = payload.get("event")

    print(f"\n=== WEBHOOK ASAAS | evento: {event} ===")
    print(payload)

    try:
        # ----------------------------------------------------------
        # 1. Pagamento confirmado → atualiza historico + licença
        # ----------------------------------------------------------
        if event in ("PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"):
            dados      = map_webhook_event(payload)
            payment_id = dados.get("gateway_payment_id")

            if not payment_id:
                return jsonify({"status": "ignored"}), 200

            historico = HistoricoPagamentos.query.filter_by(
                gateway='asaas',
                gateway_payment_id=payment_id
            ).first()

            if not historico:
                print(f"Pagamento não encontrado: {payment_id}")
                return jsonify({"status": "not_found"}), 200

            historico.status_boleto   = dados.get("status_boleto")
            historico.data_pagamento  = dados.get("data_pagamento")
            historico.data_credito    = dados.get("data_credito")
            historico.gateway_payload = payload

            if historico.status_boleto == 'pago' and historico.licenca:
                licenca_id = historico.licenca_id

                # Faturas em aberto (não pagas, excluindo a atual)
                faturas_abertas = HistoricoPagamentos.query.filter(
                    HistoricoPagamentos.licenca_id == licenca_id,
                    HistoricoPagamentos.id != historico.id,
                    HistoricoPagamentos.status_boleto.in_(['pendente', 'emitido', 'vencido'])
                ).order_by(HistoricoPagamentos.data_vencimento.asc()).all()

                if faturas_abertas:
                    # Tem inadimplência → trava na mais antiga em aberto
                    mais_antiga = faturas_abertas[0]
                    nova_expiracao = mais_antiga.data_vencimento + relativedelta(months=1)
                    print(f"⚠️  Inadimplência detectada — travando em {mais_antiga.data_vencimento}")
                else:
                    # Sem pendências → pega a fatura paga mais recente (incluindo a atual)
                    fatura_mais_recente = HistoricoPagamentos.query.filter(
                        HistoricoPagamentos.licenca_id == licenca_id,
                        HistoricoPagamentos.status_boleto == 'pago'
                    ).order_by(HistoricoPagamentos.data_vencimento.desc()).first()

                    if not fatura_mais_recente:
                        fatura_mais_recente = historico

                    nova_expiracao = fatura_mais_recente.data_vencimento + relativedelta(months=1)

                historico.licenca.data_expiracao = nova_expiracao
                historico.licenca.status = 'Ativo'
                print(f"✅ Licença atualizada: {historico.licenca.id} → {nova_expiracao}")

            db.session.commit()
            print(f"✅ Pagamento atualizado: {payment_id}")
            return jsonify({"status": "updated"}), 200

        # ----------------------------------------------------------
        # 2. Boleto vencido → atualiza status
        # ----------------------------------------------------------
        elif event == "PAYMENT_OVERDUE":
            dados      = map_webhook_event(payload)
            payment_id = dados.get("gateway_payment_id")

            if not payment_id:
                return jsonify({"status": "ignored"}), 200

            historico = HistoricoPagamentos.query.filter_by(
                gateway='asaas',
                gateway_payment_id=payment_id
            ).first()

            if not historico:
                print(f"Pagamento não encontrado: {payment_id}")
                return jsonify({"status": "not_found"}), 200

            historico.status_boleto   = 'vencido'
            historico.gateway_payload = payload
            db.session.commit()
            print(f"⚠️  Boleto vencido: {payment_id}")
            return jsonify({"status": "updated"}), 200

        # ----------------------------------------------------------
        # 3. Eventos de NFS-e
        # ----------------------------------------------------------
        elif event in ("INVOICE_AUTHORIZED", "INVOICE_CANCELED", "INVOICE_ERROR"):
            invoice_data = payload.get("invoice", {})
            invoice_id   = invoice_data.get("id")

            if not invoice_id:
                return jsonify({"status": "ignored"}), 200

            historico = HistoricoPagamentos.query.filter_by(
                nf_id=invoice_id
            ).first()

            if not historico:
                print(f"NF não encontrada no banco: {invoice_id}")
                return jsonify({"status": "not_found"}), 200

            historico.nf_status = invoice_data.get("status")

            if event == "INVOICE_AUTHORIZED":
                historico.nf_pdf_url    = invoice_data.get("pdfUrl")
                historico.nf_xml_url    = invoice_data.get("xmlUrl")
                historico.nf_emitida_em = datetime.utcnow()
                print(f"✅ NF autorizada: {invoice_id}")

            elif event == "INVOICE_CANCELED":
                historico.nf_pdf_url = None
                historico.nf_xml_url = None
                print(f"🚫 NF cancelada: {invoice_id}")

            elif event == "INVOICE_ERROR":
                print(f"❌ NF com erro: {invoice_id} — {invoice_data.get('statusDescription')}")

            db.session.commit()
            return jsonify({"status": "updated"}), 200

        # ----------------------------------------------------------
        # 4. Qualquer outro evento → ignora
        # ----------------------------------------------------------
        else:
            return jsonify({"status": "ignored"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro no webhook: {str(e)}")
        return jsonify({"status": "error"}), 500

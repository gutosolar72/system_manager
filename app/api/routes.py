from flask import request, jsonify
from datetime import datetime
from app.extensions import db
from app.models import Licenca, Produto, Contrato
import hashlib

from app.api import bp_api

@bp_api.route('/ativar_licenca', methods=['POST'])
def ativar_licenca():
    """
    Recebe JSON:
    {
        "uuid": "...",
        "mac": "...",
        "chave_licenca": "...",
        "produto": "...",
    }
    """
    data = request.get_json()
    uuid = data.get('uuid')
    mac = data.get('mac')
    chave_licenca = data.get('chave_licenca')
    produto_nome = data.get('produto')

    if not uuid or not mac or not chave_licenca or not produto_nome:
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
            data_ativacao=datetime.utcnow(),
            ultima_verificacao=datetime.utcnow()
        )
        db.session.add(licenca)
        db.session.commit()  # commit para gerar ID e permitir vincular contrato depois

    # Busca contrato vinculado, se houver
    contrato = Contrato.query.filter_by(licenca_id=licenca.id).first()

    return jsonify({
        'status': contrato.status if contrato else None,
        'valid_until': licenca.data_expiracao.isoformat() if licenca.data_expiracao else None,
        'modulos_override': contrato.modulos_override if contrato else None
    }), 200


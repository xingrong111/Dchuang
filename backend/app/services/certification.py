"""SHA-256 内容指纹 + EVM JSON-RPC 存证。只有链上回执验证通过才认证。"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse, unquote
import requests
from flask import current_app
from app.utils.exceptions import ValidationError, AIServiceError


def fingerprint(artwork):
    url = urlparse(artwork.model_url or '')
    prefix = '/api/static/uploads/'
    if url.scheme or url.netloc or not url.path.startswith(prefix):
        raise ValidationError('存证需要本站已持久化的模型文件')
    root = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    path = (root / unquote(url.path[len(prefix):])).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValidationError('模型文件不存在或路径非法')
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(chunk)
    manifest = {'version': 1, 'artwork_id': artwork.id, 'author_id': artwork.user_id,
                'title': artwork.title, 'description': artwork.description or '',
                'model_sha256': digest.hexdigest(), 'ai_model': artwork.ai_model,
                'ai_prompt': artwork.ai_prompt, 'ai_params': artwork.ai_params}
    serialized = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(serialized).hexdigest(), manifest


class EVMNotary:
    def __init__(self):
        self.url = current_app.config.get('BLOCKCHAIN_RPC_URL', '')
        self.sender = current_app.config.get('BLOCKCHAIN_FROM_ADDRESS', '')
        self.recipient = current_app.config.get('BLOCKCHAIN_TO_ADDRESS', '') or self.sender
        self.chain_id = current_app.config.get('BLOCKCHAIN_CHAIN_ID', '')
        if not self.url or not self.chain_id or not all(re.fullmatch(r'0x[0-9a-fA-F]{40}', v) for v in [self.sender, self.recipient]):
            raise AIServiceError('存证服务未配置：需要 RPC、chain_id 和节点托管账户')
        if urlparse(self.url).scheme not in ('http', 'https'):
            raise AIServiceError('存证 RPC 地址配置非法')

    def rpc(self, method, params):
        try:
            response = requests.post(self.url, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}, timeout=15)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError):
            raise AIServiceError('存证节点连接或响应失败；请核对节点交易记录后再提交')
        if not isinstance(body, dict) or body.get('error') or 'result' not in body:
            raise AIServiceError('存证节点拒绝请求，请检查账户授权和余额')
        return body['result']

    def check_chain(self):
        if int(self.rpc('eth_chainId', []), 16) != int(str(self.chain_id), 0):
            raise AIServiceError('存证节点链 ID 与配置不一致')

    def submit(self, digest):
        self.check_chain()
        transaction = self.rpc('eth_sendTransaction', [{'from': self.sender, 'to': self.recipient,
            'value': '0x0', 'gas': hex(100000), 'data': '0x' + digest}])
        if not isinstance(transaction, str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}', transaction):
            raise AIServiceError('存证节点未返回有效交易编号，请核对节点记录')
        return transaction

    def verify(self, transaction, digest):
        self.check_chain()
        receipt = self.rpc('eth_getTransactionReceipt', [transaction])
        if receipt is None:
            return {'status': 'PENDING', 'verified': False}
        if not isinstance(receipt, dict) or receipt.get('status') != '0x1':
            return {'status': 'FAILED', 'verified': False}
        tx = self.rpc('eth_getTransactionByHash', [transaction])
        if not isinstance(tx, dict) or tx.get('input', '').lower() != '0x' + digest or tx.get('from', '').lower() != self.sender.lower() or tx.get('to', '').lower() != self.recipient.lower():
            return {'status': 'MISMATCH', 'verified': False}
        # 确认区块仍在规范链上，避免将孤块回执视为成功。
        block = self.rpc('eth_getBlockByNumber', [receipt['blockNumber'], False])
        if not block or block.get('hash') != receipt.get('blockHash'):
            return {'status': 'PENDING', 'verified': False}
        confirmations = int(self.rpc('eth_blockNumber', []), 16) - int(receipt['blockNumber'], 16) + 1
        verified = confirmations >= current_app.config.get('BLOCKCHAIN_CONFIRMATIONS', 2)
        return {'status': 'CONFIRMED' if verified else 'PENDING', 'verified': verified,
                'confirmations': confirmations, 'block_number': int(receipt['blockNumber'], 16)}

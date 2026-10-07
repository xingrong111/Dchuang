from pathlib import Path
import pytest
from app import create_app
from app.extensions import db
from app.models.artwork import Artwork
from app.models.user import User


@pytest.fixture
def setup(tmp_path):
    app = create_app('testing')
    app.config.update(UPLOAD_FOLDER=str(tmp_path), BLOCKCHAIN_RPC_URL='http://127.0.0.1:8545',
        BLOCKCHAIN_FROM_ADDRESS='0x'+'1'*40, BLOCKCHAIN_TO_ADDRESS='0x'+'1'*40,
        BLOCKCHAIN_CHAIN_ID='1337', BLOCKCHAIN_CONFIRMATIONS=2)
    (tmp_path/'models').mkdir()
    model_path=tmp_path/'models/model.glb'; model_path.write_bytes(b'glTF-content')
    with app.app_context():
        db.create_all()
        user=User('owner','owner@example.com','password123');db.session.add(user);db.session.flush()
        work=Artwork(user_id=user.id,title='阿福',model_url='/api/static/uploads/models/model.glb')
        db.session.add(work);db.session.commit();work_id=work.id
    client=app.test_client()
    response=client.post('/auth/login',json={'email':'owner@example.com','password':'password123'})
    headers={'Authorization':'Bearer '+response.json['data']['token']}
    yield app, client, headers, work_id, model_path
    with app.app_context():db.session.remove();db.drop_all()


def test_pending_confirmed_tamper_and_idempotency(setup,monkeypatch):
    app,client,headers,work_id,path=setup
    calls=[];txid='0x'+'a'*64
    def rpc(self,method,params):
        calls.append(method)
        if method=='eth_chainId':return hex(1337)
        if method=='eth_sendTransaction':return txid
        if method=='eth_getTransactionReceipt':return {'status':'0x1','blockNumber':'0xa','blockHash':'0xbbb'}
        if method=='eth_getTransactionByHash':
            with app.app_context(): digest=db.session.get(Artwork,work_id).blockchain_hash
            return {'input':'0x'+digest,'from':'0x'+'1'*40,'to':'0x'+'1'*40}
        if method=='eth_getBlockByNumber':return {'hash':'0xbbb'}
        if method=='eth_blockNumber':return '0xb'
        raise AssertionError(method)
    monkeypatch.setattr('app.services.certification.EVMNotary.rpc',rpc)
    response=client.post(f'/workshop/works/{work_id}/certify',headers=headers)
    assert response.status_code==200 and response.json['data']['status']=='PENDING'
    client.post(f'/workshop/works/{work_id}/certify',headers=headers)
    assert calls.count('eth_sendTransaction')==1
    assert client.get(f'/workshop/works/{work_id}/certificate').json['data']['verified'] is True
    path.write_bytes(b'glTF-modified')
    assert client.get(f'/workshop/works/{work_id}/certificate').json['data']['status']=='CONTENT_CHANGED'
    with app.app_context():assert db.session.get(Artwork,work_id).is_certified is False


def test_no_config_and_path_escape(setup):
    app,client,headers,work_id,_=setup
    app.config['BLOCKCHAIN_RPC_URL']=''
    assert client.post(f'/workshop/works/{work_id}/certify',headers=headers).status_code==503
    with app.app_context():
        work=db.session.get(Artwork,work_id);work.model_url='/api/static/uploads/../../secret';db.session.commit()
    assert client.get(f'/workshop/works/{work_id}/certificate').status_code==400


def test_receipt_mismatch_and_pending(setup,monkeypatch):
    app,client,_,work_id,_=setup
    from app.services.certification import fingerprint
    with app.app_context():
        work=db.session.get(Artwork,work_id);work.blockchain_hash=fingerprint(work)[0];work.blockchain_tx_id='0x'+'b'*64;db.session.commit()
    state={'pending':True}
    def rpc(self,method,params):
        if method=='eth_chainId':return hex(1337)
        if method=='eth_getTransactionReceipt':return None if state['pending'] else {'status':'0x1','blockNumber':'0xa'}
        if method=='eth_getTransactionByHash':return {'input':'0x'+'0'*64,'from':'0x'+'1'*40,'to':'0x'+'1'*40}
        raise AssertionError(method)
    monkeypatch.setattr('app.services.certification.EVMNotary.rpc',rpc)
    assert client.get(f'/workshop/works/{work_id}/certificate').json['data']['status']=='PENDING'
    state['pending']=False
    assert client.get(f'/workshop/works/{work_id}/certificate').json['data']['status']=='MISMATCH'

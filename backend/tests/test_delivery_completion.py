import pytest
from tests.test_artwork_api import app, db, client, _register, _login, _auth_headers


def test_real_statistics_and_personalized_recommendations(client):
    _register(client, 'viewer', 'viewer@example.com')
    viewer = _auth_headers(_login(client, 'viewer@example.com'))
    client.post('/auth/logout')
    _register(client, 'maker', 'maker@example.com')
    maker = _auth_headers(_login(client, 'maker@example.com'))
    ids = []
    for title, tags, public in [('收藏来源', ['惠山泥人'], True), ('相关作品', ['惠山泥人'], True),
                                ('不相关', ['锡绣'], True), ('秘密', ['惠山泥人'], False)]:
        response = client.post('/workshop/save', headers=maker, json={'title': title, 'tags': tags, 'is_public': public})
        ids.append(response.json['data']['id'])
    client.post(f'/workshop/works/{ids[0]}/collect', headers=viewer)
    client.get(f'/workshop/works/{ids[1]}')
    data = client.get('/statistics/public').json['data']
    assert data == {'artworks': 3, 'users': 2, 'creators': 1, 'views': 1}
    response = client.get('/workshop/recommendations', headers=viewer)
    assert response.json['meta']['recommendation']['personalized'] is True
    assert response.json['data'][0]['id'] == ids[1]
    assert ids[3] not in [row['id'] for row in response.json['data']]
    assert '相关' in response.json['data'][0]['recommendation_reason']


def test_reset_code_is_persistent_single_use_and_password_atomic(app, db, client, monkeypatch):
    from app.utils.verification_code import generate_code, verify_code
    from app.models.reset_code import PasswordResetCode
    _register(client, 'resetter', 'reset@example.com')
    with app.app_context():
        code = generate_code('reset@example.com')
        assert db.session.get(PasswordResetCode, 'reset@example.com').digest != code
        with pytest.raises(ValueError): generate_code('reset@example.com')
        db.session.remove()
        assert verify_code('reset@example.com', code)
        db.session.rollback()
    # Rolled-back consumption still permits legitimate reset.
    response = client.post('/auth/reset-password', json={'email': 'reset@example.com', 'code': code, 'new_password': 'changedpassword'})
    assert response.status_code == 200
    assert client.post('/auth/reset-password', json={'email': 'reset@example.com', 'code': code, 'new_password': 'anotherpassword'}).status_code == 400
    assert client.post('/auth/login', json={'email': 'reset@example.com', 'password': 'changedpassword'}).status_code == 200
    with app.app_context():
        code = generate_code('reset@example.com')
        for _ in range(5):
            with pytest.raises(ValueError): verify_code('reset@example.com', 'invalid')
        with pytest.raises(ValueError): verify_code('reset@example.com', code)


def test_failed_email_clears_challenge(app, db, client, monkeypatch):
    from app.models.reset_code import PasswordResetCode
    _register(client, 'mailer', 'mailer@example.com')
    monkeypatch.setattr('app.utils.email.send_verification_email', lambda *args: False)
    assert client.post('/auth/forgot-password', json={'email': 'mailer@example.com'}).status_code == 200
    with app.app_context(): assert db.session.get(PasswordResetCode, 'mailer@example.com') is None


def test_backup_restore_roundtrip_and_nonempty_guard(app, db, client, tmp_path):
    from scripts.backup_restore import backup, restore
    from app.models.user import User
    from pathlib import Path
    with app.app_context():
        # Fixture uses create_all; add the actual migration revision required for portable backups.
        db.session.execute(db.text('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)'))
        db.session.execute(db.text("INSERT INTO alembic_version VALUES ('ac1020260002')"))
        user = User('backup', 'backup@example.com', 'password123'); db.session.add(user); db.session.commit()
        uploads = Path(app.config['UPLOAD_FOLDER']); uploads.mkdir(parents=True)
        (uploads/'asset.glb').write_bytes(b'glTF-test')
        archive = tmp_path/'backup.zip'
        assert backup(archive) >= 1
        with pytest.raises(ValueError): restore(archive)
        for table in reversed(db.metadata.sorted_tables): db.session.execute(table.delete())
        db.session.commit()
        (uploads/'asset.glb').unlink()
        assert restore(archive) >= 1
        assert User.query.filter_by(email='backup@example.com').first().check_password('password123')
        assert (uploads/'asset.glb').read_bytes() == b'glTF-test'


def test_worker_lock_refuses_duplicate_and_releases(tmp_path):
    from worker import acquire_lock
    path = tmp_path/'worker.lock'
    first = acquire_lock(path)
    try:
        with pytest.raises(RuntimeError): acquire_lock(path)
    finally:
        first.close()
    with acquire_lock(path): pass

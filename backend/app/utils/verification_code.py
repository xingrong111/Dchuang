"""Database-backed, single-use reset challenges; no plaintext codes at rest."""
import hashlib
import hmac
import secrets
import time
from flask import current_app
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.reset_code import PasswordResetCode

CODE_EXPIRE_SECONDS = 600
MAX_ATTEMPTS = 5
SEND_COOLDOWN_SECONDS = 60


def _digest(email, nonce, code):
    key = str(current_app.config['SECRET_KEY']).encode()
    return hmac.new(key, f'{email}:{nonce}:{code}'.encode(), hashlib.sha256).hexdigest()


def generate_code(email):
    now = time.time()
    code = f'{secrets.randbelow(1000000):06d}'
    nonce = secrets.token_hex(16)
    values = dict(digest=_digest(email, nonce, code), nonce=nonce, expires=now + CODE_EXPIRE_SECONDS,
                  sent_at=now, attempts=0)
    row = db.session.get(PasswordResetCode, email)
    if row:
        changed = PasswordResetCode.query.filter_by(email=email).filter(
            PasswordResetCode.sent_at <= now - SEND_COOLDOWN_SECONDS).update(values, synchronize_session=False)
        if not changed:
            db.session.rollback()
            raise ValueError('验证码已发送，请 60 秒后再试')
    else:
        db.session.add(PasswordResetCode(email=email, **values))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError('验证码已发送，请 60 秒后再试')
    return code


def verify_code(email, code):
    row = db.session.get(PasswordResetCode, email)
    if not row:
        raise ValueError('请先获取验证码')
    nonce = row.nonce
    now = time.time()
    if now >= row.expires:
        PasswordResetCode.query.filter_by(email=email, nonce=nonce).delete()
        db.session.commit()
        raise ValueError('验证码已过期，请重新获取')
    valid = hmac.compare_digest(row.digest, _digest(email, nonce, code))
    if valid:
        changed = PasswordResetCode.query.filter_by(email=email, nonce=nonce).filter(
            PasswordResetCode.attempts < MAX_ATTEMPTS, PasswordResetCode.expires > now).delete()
        if not changed:
            db.session.rollback()
            raise ValueError('验证码已使用或尝试次数过多')
        # Caller commits consumption and password change in the same transaction.
        return True
    PasswordResetCode.query.filter_by(email=email, nonce=nonce).update(
        {PasswordResetCode.attempts: PasswordResetCode.attempts + 1}, synchronize_session=False)
    db.session.commit()
    raise ValueError('验证码错误或尝试次数过多，请重新获取')


def clear_code(email):
    PasswordResetCode.query.filter_by(email=email).delete()
    db.session.commit()

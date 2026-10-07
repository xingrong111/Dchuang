from app.api.v1 import api_bp
from app.api.v1.user import _get_authenticated_user_or_401
from app.extensions import db
from app.models.artwork import Artwork
from app.services.certification import fingerprint, EVMNotary
from app.utils.exceptions import ResourceNotFoundError, PermissionError_, ValidationError
from app.utils.response import APIResponse


def _owned(artwork_id):
    user = _get_authenticated_user_or_401()
    artwork = Artwork.query.filter_by(id=artwork_id).with_for_update().first()
    if not artwork:
        raise ResourceNotFoundError('作品不存在')
    if artwork.user_id != user.id:
        raise PermissionError_('仅作者可提交存证')
    return artwork


@api_bp.post('/workshop/works/<artwork_id>/certify')
def certify(artwork_id):
    artwork = _owned(artwork_id)
    digest, manifest = fingerprint(artwork)
    if artwork.blockchain_tx_id:
        if digest != artwork.blockchain_hash:
            raise ValidationError('作品内容已变化，请更新作品后重新存证')
        return APIResponse.success({'status': 'CONFIRMED' if artwork.is_certified else 'PENDING',
                                    'transaction_id': artwork.blockchain_tx_id, 'digest': digest})
    tx = EVMNotary().submit(digest)
    artwork.blockchain_hash, artwork.blockchain_tx_id = digest, tx
    artwork.is_certified = False
    db.session.commit()
    return APIResponse.success({'status': 'PENDING', 'transaction_id': tx, 'digest': digest, 'manifest': manifest})


@api_bp.get('/workshop/works/<artwork_id>/certificate')
def certificate(artwork_id):
    from app.utils.auth import get_authenticated_user
    artwork = db.session.get(Artwork, artwork_id)
    user = get_authenticated_user()
    if not artwork or (not artwork.is_public and (not user or user.id != artwork.user_id)):
        raise ResourceNotFoundError('作品不存在')
    digest, manifest = fingerprint(artwork)
    result = {'status': 'UNSUBMITTED', 'verified': False}
    if artwork.blockchain_tx_id:
        if digest != artwork.blockchain_hash:
            result = {'status': 'CONTENT_CHANGED', 'verified': False}
        else:
            result = EVMNotary().verify(artwork.blockchain_tx_id, digest)
    artwork.is_certified = result['verified']
    db.session.commit()
    return APIResponse.success({**result, 'digest': digest, 'manifest': manifest,
                                'transaction_id': artwork.blockchain_tx_id})

"""Public counts and explainable recommendations based on real interactions."""
from collections import Counter
from datetime import datetime
from flask import request
from sqlalchemy.orm import joinedload
from app.api.v1 import api_bp
from app.extensions import db
from app.models.artwork import Artwork
from app.models.user import User
from app.models.like import Like
from app.models.comment import Comment
from app.models.collection import Collection
from app.utils.auth import get_authenticated_user
from app.utils.response import APIResponse


@api_bp.get('/statistics/public')
def public_statistics():
    return APIResponse.success({
        'artworks': Artwork.query.filter_by(is_public=True).count(),
        'creators': db.session.query(Artwork.user_id).filter(
            Artwork.is_public.is_(True)).distinct().count(),
        'users': User.query.filter_by(is_active=True).count(),
        'views': int(db.session.query(db.func.coalesce(db.func.sum(Artwork.view_count), 0))
                     .filter(Artwork.is_public.is_(True)).scalar()),
    })


@api_bp.get('/workshop/recommendations')
def recommendations():
    user = get_authenticated_user()
    size = max(1, min(50, request.args.get('per_page', 12, type=int)))
    # Bound ranking work; use recent public works, never expose private history.
    works = Artwork.query.filter_by(is_public=True).options(joinedload(Artwork.author)).order_by(
        Artwork.created_at.desc(), Artwork.id.desc()).limit(500).all()
    ids = [work.id for work in works]
    counts = {}
    for entity in (Like, Comment, Collection):
        counts[entity] = dict(db.session.query(entity.artwork_id, db.func.count(entity.id)).filter(
            entity.artwork_id.in_(ids)).group_by(entity.artwork_id).all()) if ids else {}
    interests = Counter()
    liked, collected = set(), set()
    if user:
        liked = {row[0] for row in db.session.query(Like.artwork_id).filter(
            Like.user_id == user.id, Like.artwork_id.in_(ids)).all()}
        collected = {row[0] for row in db.session.query(Collection.artwork_id).filter(
            Collection.user_id == user.id, Collection.artwork_id.in_(ids)).all()}
        history = Artwork.query.filter(Artwork.is_public.is_(True), Artwork.id.in_(liked | collected)).all()
        for work in history:
            for tag in work.tags or []:
                if isinstance(tag, str):
                    interests[tag] += 2 if work.id in collected else 1
    now = datetime.utcnow()
    def score(work):
        affinity = sum(interests[tag] for tag in work.tags or [] if isinstance(tag, str))
        activity = counts[Like].get(work.id, 0) + 2 * counts[Collection].get(work.id, 0) + counts[Comment].get(work.id, 0)
        days = max(0, (now - (work.created_at or now)).total_seconds() / 86400)
        novelty = 0.25 if work.id in liked | collected else 1
        return (3 * affinity + activity / (1 + days / 30) + 1 / (1 + days)) * novelty
    ranked = sorted((work for work in works if not user or work.user_id != user.id), key=score, reverse=True)
    if not ranked:
        ranked = sorted(works, key=score, reverse=True)
    items = []
    for work in ranked[:size]:
        item = work.to_dict()
        matching = [tag for tag in work.tags or [] if isinstance(tag, str) and interests[tag]]
        item.update(like_count=counts[Like].get(work.id, 0), comment_count=counts[Comment].get(work.id, 0),
                    collect_count=counts[Collection].get(work.id, 0),
                    recommendation_reason='与你喜欢的 ' + '、'.join(matching[:3]) + ' 相关' if matching else '近期社区精选',
                    current_user_status={'liked': work.id in liked, 'collected': work.id in collected,
                                         'is_author': bool(user and user.id == work.user_id)})
        items.append(item)
    return APIResponse.success(items, meta={'recommendation': {
        'strategy': 'interaction_tags_recency_v1' if interests else 'community_recency_v1',
        'candidate_limit': 500, 'personalized': bool(interests)}})

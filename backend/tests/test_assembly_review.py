import pytest
from app.services.assembly_review import validate_review, normalize_review
from app.utils.exceptions import ValidationError, AIServiceError


def test_review_requires_login_and_missing_key_is_not_mocked():
    from app import create_app
    from app.services.assembly_review import review_scene
    app = create_app('testing')
    app.config['GLM_API_KEY'] = ''
    with app.test_client() as client:
        assert client.post('/ai/review-assembly', json={}).status_code == 401
    with app.app_context(), pytest.raises(AIServiceError, match='未配置'):
        review_scene([{'id': 'p', 'category': 'pet'}], '')


def test_snapshot_and_part_validation():
    image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZfQAAAAASUVORK5CYII='
    parts, _ = validate_review({'parts': [{'id': 'pet-1', 'category': 'pet'}], 'image': image})
    assert parts[0]['id'] == 'pet-1'
    with pytest.raises(ValidationError):
        validate_review({'parts': parts, 'image': 'https://example.org/image.png'})
    with pytest.raises(ValidationError):
        validate_review({'parts': parts * 2, 'image': image})


def test_provider_cannot_move_body_or_inject_arbitrary_transforms():
    parts = [{'id': 'p', 'category': 'pet'}, {'id': 'b', 'category': 'body'}]
    result = normalize_review({'adjustments': [
        {'id': 'p', 'scaleFactor': 100, 'yawDegrees': -100, 'position': [999, 999, 999]},
        {'id': 'b', 'scaleFactor': 2}, {'id': 'unknown', 'yawDegrees': 10}]}, parts)
    assert result['adjustments'] == [{'id': 'p', 'scaleFactor': 1.1, 'yawDegrees': -15}]
    with pytest.raises(AIServiceError):
        normalize_review({'adjustments': 'execute code'}, parts)

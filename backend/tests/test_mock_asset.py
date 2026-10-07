from app import create_app
from app.models.ai_task import AITask
from app.services.mock import MockProvider


def test_mock_result_is_a_served_glb(tmp_path):
    app = create_app('testing')
    # 使用应用真正的静态目录，验证 URL 到文件的完整映射。
    from pathlib import Path
    app.static_folder = str(tmp_path)
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    with app.app_context():
        result = MockProvider().generate_3d(AITask(task_type='text_to_3d'))
        assert result['status'] == 'SUCCESS'
        response = app.test_client().get(result['result_url'].removeprefix('/api'))
        assert response.status_code == 200
        assert response.data[:4] == b'glTF'
        assert int.from_bytes(response.data[8:12], 'little') == len(response.data)
        repeated = MockProvider().generate_3d(AITask(task_type='text_to_3d'))
        assert repeated['result_url'] == result['result_url']
        assert len(list(Path(app.config['UPLOAD_FOLDER']).rglob('*.glb'))) == 1


def test_missing_demo_asset_fails_explicitly(tmp_path):
    app = create_app('testing')
    app.config.update(UPLOAD_FOLDER=str(tmp_path), MOCK_MODEL_PATH=str(tmp_path / 'absent.glb'))
    with app.app_context():
        result = MockProvider().generate_3d(AITask(task_type='text_to_3d'))
        assert result['status'] == 'FAILED'
        assert 'result_url' not in result

# ============================================================
# 智绘锡承 - 模型产物转存工具测试（阶段13-B2）
# 覆盖: download_model_to_local 的成功/失败/安全校验
# 全部 mock requests.get，禁止真实下载腾讯文件
# ============================================================
import os

import pytest


@pytest.fixture
def app(tmp_path):
    """测试应用（UPLOAD_FOLDER 临时目录）"""
    from app import create_app

    app = create_app('testing')
    uploads = tmp_path / 'uploads'
    uploads.mkdir(exist_ok=True)
    app.config['UPLOAD_FOLDER'] = str(uploads)
    return app


def _fake_resp(content=b'', status_code=200):
    """构造假 requests.Response（content + raise_for_status）"""
    from requests import HTTPError

    class FakeResp:
        def __init__(self):
            self.content = content
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise HTTPError(f'HTTP {self.status_code}', response=self)

    return FakeResp()


def _glb_bytes():
    """最小合法 GLB（glTF 魔数 + 版本 + 长度）"""
    import struct

    header = b'glTF' + struct.pack('<II', 2, 12)
    return header + b'\x00' * 8


def _monkeypatch_get(monkeypatch, resp=None, exc=None):
    """monkeypatch requests.get"""
    import requests

    def fake_get(url, timeout=None):
        if exc is not None:
            raise exc
        return resp

    monkeypatch.setattr('app.utils.files.requests.get', fake_get)


class TestDownloadModelToLocal:
    """download_model_to_local 安全与行为"""

    def test_download_success_saves_glb(self, app, monkeypatch):
        """腾讯 COS 下载成功 → 本地 URL（UUID 文件名）+ 文件落盘"""
        from app.utils.files import download_model_to_local

        _monkeypatch_get(monkeypatch, resp=_fake_resp(_glb_bytes()))
        with app.app_context():
            local_url = download_model_to_local(
                'https://hunyuan-prod-1258344699.cos.ap-guangzhou.tencentcos.cn/3d/out/model.glb'
            )

        assert local_url.startswith('/api/static/uploads/models/')
        assert local_url.endswith('.glb')
        # UUID 文件名（纯 hex，无用户输入）
        name = local_url.rsplit('/', 1)[-1].rsplit('.', 1)[0]
        assert len(name) == 32 and all(c in '0123456789abcdef' for c in name)
        # 文件真实落盘且内容正确
        rel = local_url.replace('/api/static/uploads/', '').replace('/', os.sep)
        path = os.path.join(app.config['UPLOAD_FOLDER'], rel)
        assert os.path.isfile(path)
        with open(path, 'rb') as f:
            assert f.read() == _glb_bytes()

    def test_download_rejects_non_https(self, app, monkeypatch):
        """非 https → ValidationError"""
        from app.utils.exceptions import ValidationError
        from app.utils.files import download_model_to_local

        with app.app_context():
            with pytest.raises(ValidationError):
                download_model_to_local('http://xxx.cos.tencentcos.cn/a.glb')

    def test_download_rejects_host_not_whitelisted(self, app, monkeypatch):
        """域名不在白名单 → ValidationError（防任意 URL 下载/SSRF）"""
        from app.utils.exceptions import ValidationError
        from app.utils.files import download_model_to_local

        with app.app_context():
            with pytest.raises(ValidationError):
                download_model_to_local('https://evil.example.com/model.glb')
            with pytest.raises(ValidationError):
                download_model_to_local('https://internal.localhost/x.glb')

    def test_download_rejects_bad_extension(self, app, monkeypatch):
        """扩展名不在白名单 → ValidationError"""
        from app.utils.exceptions import ValidationError
        from app.utils.files import download_model_to_local

        with app.app_context():
            with pytest.raises(ValidationError):
                download_model_to_local('https://x.cos.tencentcos.cn/payload.exe')

    def test_download_http_error_raises(self, app, monkeypatch):
        """下载 HTTP 非 200 → AIServiceError"""
        from app.utils.exceptions import AIServiceError
        from app.utils.files import download_model_to_local

        _monkeypatch_get(monkeypatch, resp=_fake_resp(b'', status_code=403))
        with app.app_context():
            with pytest.raises(AIServiceError):
                download_model_to_local('https://x.cos.tencentcos.cn/a.glb')

    def test_download_network_error_raises(self, app, monkeypatch):
        """网络异常 → AIServiceError"""
        import requests

        from app.utils.exceptions import AIServiceError
        from app.utils.files import download_model_to_local

        _monkeypatch_get(monkeypatch, exc=requests.exceptions.Timeout('timeout'))
        with app.app_context():
            with pytest.raises(AIServiceError):
                download_model_to_local('https://x.cos.tencentcos.cn/a.glb')

    def test_download_empty_content_raises(self, app, monkeypatch):
        """空内容 → AIServiceError"""
        from app.utils.exceptions import AIServiceError
        from app.utils.files import download_model_to_local

        _monkeypatch_get(monkeypatch, resp=_fake_resp(b''))
        with app.app_context():
            with pytest.raises(AIServiceError):
                download_model_to_local('https://x.cos.tencentcos.cn/a.glb')

    def test_download_magic_mismatch_raises(self, app, monkeypatch):
        """伪造扩展名（.glb 但内容非 glTF）→ ValidationError（魔数校验）"""
        from app.utils.exceptions import ValidationError
        from app.utils.files import download_model_to_local

        _monkeypatch_get(monkeypatch, resp=_fake_resp(b'not a real glb content at all'))
        with app.app_context():
            with pytest.raises(ValidationError):
                download_model_to_local('https://x.cos.tencentcos.cn/a.glb')

    def test_download_empty_url_raises(self, app, monkeypatch):
        """空地址 → ValidationError"""
        from app.utils.exceptions import ValidationError
        from app.utils.files import download_model_to_local

        with app.app_context():
            with pytest.raises(ValidationError):
                download_model_to_local('')

# ============================================================
# 智绘锡承 - 安全图片 Base64 读取测试（阶段11-A）
# 覆盖: read_upload_image_as_base64 的路径映射/大小/MIME/魔数/Base64
# 不调用 GLM / 不联网
# ============================================================
import base64
import os

import pytest


@pytest.fixture
def app(tmp_path):
    """测试应用（UPLOAD_FOLDER 指向临时目录）"""
    from app import create_app

    app = create_app('testing')
    uploads = tmp_path / 'uploads'
    uploads.mkdir(exist_ok=True)
    app.config['UPLOAD_FOLDER'] = str(uploads)
    return app


@pytest.fixture
def uploads(app):
    """上传根目录"""
    return app.config['UPLOAD_FOLDER']


def _png_bytes():
    return (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
        b'\x1f\x15\xc4\x89\x00\x00\x00\x0aIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def _jpg_bytes():
    return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9'


def _gif_bytes():
    return b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


def _webp_bytes():
    return b'RIFF\x00\x00\x00\x00WEBPVP8 '


def _make_file(uploads, subdir, name, content):
    """在上传目录创建文件并返回相对路径"""
    d = os.path.join(uploads, subdir)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, 'wb') as f:
        f.write(content)
    return f'{subdir}/{name}'


def _url(rel):
    return f'/api/static/uploads/{rel}'


class TestBase64Image:
    """read_upload_image_as_base64 测试（函数依赖 current_app，需 app context）"""

    def _call(self, app, input_url):
        """在 app context 内调用目标函数"""
        from app.utils.files import read_upload_image_as_base64

        with app.app_context():
            return read_upload_image_as_base64(input_url)

    def test_png_base64(self, app, uploads):
        """png → data:image/png;base64,..."""
        rel = _make_file(uploads, 'images', 'a.png', _png_bytes())
        result = self._call(app, _url(rel))
        assert result.startswith('data:image/png;base64,')
        # 内容可解码且等于原文件
        b64 = result.split(',', 1)[1]
        assert base64.b64decode(b64) == _png_bytes()

    def test_jpg_mime(self, app, uploads):
        """jpg → data:image/jpeg;base64,..."""
        rel = _make_file(uploads, 'images', 'b.jpg', _jpg_bytes())
        result = self._call(app, _url(rel))
        assert result.startswith('data:image/jpeg;base64,')

    def test_gif_webp_mime(self, app, uploads):
        """gif/webp → 正确 MIME"""
        rel_gif = _make_file(uploads, 'images', 'c.gif', _gif_bytes())
        assert self._call(app, _url(rel_gif)).startswith('data:image/gif;base64,')

        rel_webp = _make_file(uploads, 'images', 'd.webp', _webp_bytes())
        assert self._call(app, _url(rel_webp)).startswith('data:image/webp;base64,')

    def test_file_not_found(self, app, uploads):
        """文件不存在 → ValidationError"""
        from app.utils.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self._call(app, '/api/static/uploads/images/nonexistent.png')

    def test_path_traversal_rejected(self, app, uploads):
        """路径穿越 → ValidationError"""
        from app.utils.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self._call(app, '/api/static/uploads/../../config.py')
        with pytest.raises(ValidationError):
            self._call(app, '/api/static/uploads/images/../../config.py')

    def test_illegal_local_path(self, app, uploads):
        """非法本地路径（绝对路径/非上传前缀）→ ValidationError"""
        from app.utils.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self._call(app, 'C:/Windows/win.ini')
        with pytest.raises(ValidationError):
            self._call(app, '/etc/passwd')
        with pytest.raises(ValidationError):
            self._call(app, '/api/other/uploads/x.png')  # 非上传前缀

    def test_oversize_file(self, app, uploads):
        """超过 GLM_MAX_IMAGE_SIZE → ValidationError"""
        from app.utils.exceptions import ValidationError

        # 设置极小大小限制
        app.config['GLM_MAX_IMAGE_SIZE'] = 10  # 10 bytes
        rel = _make_file(uploads, 'images', 'big.png', _png_bytes())  # >10 bytes
        with pytest.raises(ValidationError):
            self._call(app, _url(rel))

    def test_non_image_extension(self, app, uploads):
        """非图片类型（.txt 含 uploads 前缀）→ ValidationError"""
        from app.utils.exceptions import ValidationError

        rel = _make_file(uploads, 'images', 'evil.txt', b'not an image')
        with pytest.raises(ValidationError):
            self._call(app, _url(rel))

    def test_fake_extension_magic_mismatch(self, app, uploads):
        """伪造扩展名（.png 但内容非图片）→ 魔数校验失败"""
        from app.utils.exceptions import ValidationError

        rel = _make_file(uploads, 'images', 'fake.png', b'plain text not image')
        with pytest.raises(ValidationError):
            self._call(app, _url(rel))

    def test_empty_input_url(self, app):
        """空 input_url → ValidationError"""
        from app.utils.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self._call(app, '')
        with pytest.raises(ValidationError):
            self._call(app, '   ')

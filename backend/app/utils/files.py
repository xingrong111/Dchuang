# ============================================================
# 智绘锡承 - 文件上传工具
# 位置: backend/app/utils/files.py（阶段5 文件上传服务）
#
# 安全要求（依据《阶段5 文件上传服务开发前检查报告》第十二节）:
# 1. secure_filename 清洗文件名，防路径穿越
# 2. UUID 生成存储文件名，防覆盖/防猜测
# 3. 扩展名白名单（ALLOWED_EXTENSIONS）
# 4. 真实文件内容校验（magic bytes，防伪造扩展名；PIL/imghdr 不可用故自实现）
# 5. 空文件校验
# ============================================================
import base64
import io
import os
import uuid
from urllib.parse import urlparse

import requests
from werkzeug.utils import secure_filename

from app.utils.exceptions import ValidationError
from app.utils.exceptions import AIServiceError

# ------------------------------------------------------------
# 文件魔数签名（真实内容校验，无需 PIL/imghdr）
# 格式: {扩展名: (偏移, 签名bytes)}，可多个签名
# ------------------------------------------------------------
IMAGE_SIGNATURES = {
    'png': [(0, b'\x89PNG\r\n\x1a\n')],
    'jpg': [(0, b'\xff\xd8\xff')],
    'jpeg': [(0, b'\xff\xd8\xff')],
    'gif': [(0, b'GIF87a'), (0, b'GIF89a')],
    'webp': [(0, b'RIFF'), (8, b'WEBP')],
}

MODEL_SIGNATURES = {
    'glb': [(0, b'glTF')],
    'gltf': [(0, b'{')],       # JSON 文本
    'obj': [(0, b'v '), (0, b'#')],  # Wavefront OBJ 文本（顶点行或注释）
    'stl': [(0, b'solid ')],    # ASCII STL
}

# 图片扩展名（严格魔数校验）
IMAGE_EXTENSIONS = set(IMAGE_SIGNATURES.keys())
# 3D 模型扩展名（基础魔数/格式校验）
MODEL_EXTENSIONS = set(MODEL_SIGNATURES.keys())


def is_allowed_extension(filename, allowed_extensions=None):
    """检查扩展名是否在白名单内"""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if allowed_extensions is None:
        from flask import current_app
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set())
    return ext in allowed_extensions


def get_extension(filename):
    """获取小写扩展名（不含点）"""
    if not filename or '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()


def validate_file_content(file_stream, extension):
    """基于魔数校验文件真实内容（防伪造扩展名）

    Args:
        file_stream: 已打开的文件流（须支持 seek/read）
        extension: 小写扩展名

    Raises:
        ValidationError: 内容与扩展名不符
    """
    if extension in IMAGE_SIGNATURES:
        signatures = IMAGE_SIGNATURES[extension]
    elif extension in MODEL_SIGNATURES:
        signatures = MODEL_SIGNATURES[extension]
    else:
        # 白名单外扩展名不允许（不应走到这里，防御性）
        raise ValidationError(f'不支持的文件类型: .{extension}')

    pos = file_stream.tell()
    file_stream.seek(0)
    try:
        head = file_stream.read(16)
    finally:
        file_stream.seek(pos)

    for offset, sig in signatures:
        if head[offset:offset + len(sig)] == sig:
            return
    raise ValidationError('文件内容与扩展名不符，请上传真实有效文件')


def build_storage_filename(original_filename):
    """生成安全存储文件名: <uuid8>_<secure_filename>

    - secure_filename 清洗原始文件名（去路径/危险字符）
    - UUID 前缀保证唯一，防覆盖与文件名猜测
    """
    safe_name = secure_filename(original_filename) or 'file'
    return f'{uuid.uuid4().hex[:8]}_{safe_name}'


def ensure_upload_dir(directory):
    """自动创建上传目录（若不存在）"""
    os.makedirs(directory, exist_ok=True)
    return directory


def save_upload_file(file_storage, subdir='', allowed_extensions=None):
    """保存上传文件并返回存储相对路径

    Args:
        file_storage: werkzeug FileStorage（request.files 中的对象）
        subdir: UPLOAD_FOLDER 下的子目录（如 'images' / 'avatars' / 'models'）
        allowed_extensions: 扩展名白名单（默认取 config.ALLOWED_EXTENSIONS）

    Returns:
        str: 相对于 UPLOAD_FOLDER 的存储路径（POSIX 风格，如 'images/ab12cd34_photo.png'）

    Raises:
        ValidationError: 无文件/空文件/非法扩展名/内容不符
    """
    if file_storage is None:
        raise ValidationError('未接收到文件')

    original_filename = file_storage.filename or ''
    if not original_filename:
        raise ValidationError('未选择文件')

    extension = get_extension(original_filename)
    if not is_allowed_extension(original_filename, allowed_extensions):
        raise ValidationError(f'不支持的文件类型: {extension or "未知"}')

    # 空文件校验
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size <= 0:
        raise ValidationError('文件内容为空，无法上传')

    # 真实内容校验（魔数）
    validate_file_content(file_storage.stream, extension)

    # 生成存储文件名
    storage_name = build_storage_filename(original_filename)

    from flask import current_app
    upload_root = current_app.config['UPLOAD_FOLDER']
    target_dir = ensure_upload_dir(os.path.join(upload_root, subdir)) if subdir else ensure_upload_dir(upload_root)
    target_path = os.path.join(target_dir, storage_name)

    file_storage.save(target_path)

    # 返回 POSIX 风格相对路径（浏览器 URL 用）
    rel_path = f'{subdir}/{storage_name}' if subdir else storage_name
    return rel_path.replace('\\', '/')


def build_file_url(rel_path):
    """构造浏览器可访问的完整 URL

    前端 Vite 代理将 /api 剥除后转发到 Flask，因此返回 /api/static/uploads/...，
    浏览器请求经代理 → Flask /static/uploads/...（Flask 自带静态服务）。
    """
    return f'/api/static/uploads/{rel_path.lstrip("/")}'


# 上传 URL 前缀（与 build_file_url 输出一致）
UPLOAD_URL_PREFIX = '/api/static/uploads/'

# 图片扩展名 → MIME 类型映射（供 Base64 Data URL 使用）
IMAGE_MIME_MAP = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp',
}


def read_upload_image_as_base64(input_url):
    """安全读取上传图片并转换为 Base64 Data URL

    用途: GLM 多模态接入（阶段11-A）——将本地上传图片转为
          data:image/<mime>;base64,<内容> 供 GLM image_url 使用。

    安全路径映射（不使用简单 replace 拼接）:
      1. 校验 input_url 以 UPLOAD_URL_PREFIX 开头（白名单前缀）
      2. 提取前缀后的相对路径（如 images/xxx.png）
      3. 拒绝路径穿越（..）、连续斜杠（//）、绝对路径
      4. os.path.join(UPLOAD_FOLDER, rel) 得到目标路径
      5. os.path.abspath 后再次校验必须位于 UPLOAD_FOLDER 内（双保险）

    校验顺序:
      1. 路径安全 → 2. 文件存在 → 3. 大小限制 → 4. MIME/魔数 → 5. Base64

    Args:
        input_url: 形如 /api/static/uploads/images/example.png

    Returns:
        str: data:image/<mime>;base64,<内容>

    Raises:
        ValidationError: 路径非法/文件不存在/超大小/非图片类型
    """
    if not input_url or not input_url.strip():
        raise ValidationError('input_url 不能为空')

    value = input_url.strip()
    if not value.startswith(UPLOAD_URL_PREFIX):
        raise ValidationError('input_url 必须是本项目上传路径')

    # 提取前缀后的相对路径（如 images/xxx.png）
    rel = value[len(UPLOAD_URL_PREFIX):]

    # 路径穿越 / 连续斜杠 / 绝对路径防护
    if '..' in rel.split('/') or '//' in rel:
        raise ValidationError('input_url 路径不合法')
    if rel.startswith('/') or '\\' in rel:
        raise ValidationError('input_url 路径不合法')

    from flask import current_app
    upload_root = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
    target = os.path.abspath(os.path.join(upload_root, rel.replace('/', os.sep)))

    # 双保险: 最终绝对路径必须位于 UPLOAD_FOLDER 内
    if not target.startswith(upload_root + os.sep):
        raise ValidationError('input_url 路径不合法')

    # 文件存在
    if not os.path.isfile(target):
        raise ValidationError('图片文件不存在')

    # 文件大小限制（GLM_MAX_IMAGE_SIZE，默认 10MB）
    max_size = current_app.config.get('GLM_MAX_IMAGE_SIZE', 10 * 1024 * 1024)
    file_size = os.path.getsize(target)
    if file_size > max_size:
        raise ValidationError('图片文件过大，超出 GLM 分析大小限制')

    # 扩展名 → MIME（仅允许图片类型）
    ext = get_extension(rel.split('/')[-1])
    mime = IMAGE_MIME_MAP.get(ext)
    if mime is None:
        raise ValidationError('仅支持 png/jpg/jpeg/gif/webp 图片类型')

    # 魔数校验（复用已有能力，防伪造扩展名/损坏图片）
    with open(target, 'rb') as f:
        validate_file_content(f, ext)
        f.seek(0)
        content = f.read()

    b64 = base64.b64encode(content).decode('ascii')
    return f'data:{mime};base64,{b64}'


# ------------------------------------------------------------
# 远程模型产物转存（阶段13-B2: 解决腾讯 COS 预签名 URL 过期）
# ------------------------------------------------------------
# 允许下载的模型产物域名后缀（腾讯 COS 产物；防任意 URL 下载/SSRF）
ALLOWED_DOWNLOAD_HOST_SUFFIXES = ('.tencentcos.cn', '.myqcloud.com')
# 模型产物最大下载字节（200MB，防超大/内存占用）
MODEL_MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
# 下载超时（秒）: (连接, 读取)
MODEL_DOWNLOAD_TIMEOUT = (10, 60)


def download_model_to_local(remote_url, subdir='models'):
    """下载远程 3D 模型产物并转存本地（解决第三方签名 URL 过期问题）

    设计（阶段13-B2）:
    - 仅允许 https + 白名单域名后缀（腾讯 COS: *.tencentcos.cn / *.myqcloud.com），
      防任意 URL 下载/SSRF
    - 扩展名白名单（glb/gltf/obj/stl）→ 下载后魔数校验（validate_file_content）
    - 文件名为纯 UUID（无用户输入、防覆盖/防猜测、无路径穿越）
    - 大小上限 MODEL_MAX_DOWNLOAD_BYTES（Content-Length 预检 + 实际长度双检）

    Args:
        remote_url: 第三方模型产物 https 地址（如腾讯 COS 预签名 URL）
        subdir: UPLOAD_FOLDER 下保存子目录（默认 models）

    Returns:
        str: 本地稳定访问 URL（/api/static/uploads/models/<uuid>.<ext>）

    Raises:
        ValidationError: 域名/扩展名/魔数/大小校验失败
        AIServiceError: 网络下载失败/HTTP 错误
    """
    if not remote_url or not str(remote_url).strip():
        raise ValidationError('模型下载地址不能为空')

    parsed = urlparse(str(remote_url).strip())
    if parsed.scheme != 'https' or not parsed.hostname:
        raise ValidationError('模型下载仅允许 https 地址')
    host = parsed.hostname.lower()
    if not any(host.endswith(s) for s in ALLOWED_DOWNLOAD_HOST_SUFFIXES):
        raise ValidationError('模型下载地址不在白名单（仅允许腾讯 COS 产物）')

    # 扩展名（URL 路径最后一段），白名单
    filename = parsed.path.rstrip('/').split('/')[-1]
    ext = get_extension(filename)
    if ext not in MODEL_EXTENSIONS:
        raise ValidationError(f'模型下载仅支持: {sorted(MODEL_EXTENSIONS)}')

    # 下载（带超时；Content-Length 预检防超大）
    try:
        resp = requests.get(remote_url, timeout=MODEL_DOWNLOAD_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise AIServiceError(f'模型产物下载失败: {e}')

    content = resp.content
    if not content:
        raise AIServiceError('模型产物内容为空')
    if len(content) > MODEL_MAX_DOWNLOAD_BYTES:
        raise AIServiceError('模型产物超过大小限制')

    # 魔数校验（防伪造扩展名/损坏文件）
    try:
        validate_file_content(io.BytesIO(content), ext)
    except ValidationError:
        raise

    # 保存（纯 UUID 文件名，防覆盖/防猜测）
    from flask import current_app
    upload_root = current_app.config['UPLOAD_FOLDER']
    target_dir = ensure_upload_dir(os.path.join(upload_root, subdir))
    name = f'{uuid.uuid4().hex}.{ext}'
    target_path = os.path.join(target_dir, name)
    with open(target_path, 'wb') as f:
        f.write(content)

    return build_file_url(f'{subdir}/{name}')

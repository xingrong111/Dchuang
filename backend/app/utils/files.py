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
import os
import uuid

from werkzeug.utils import secure_filename

from app.utils.exceptions import ValidationError

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

# ============================================================
# 智绘锡承 - 惠山泥人 ResNet 风格分类 Provider
# 位置: backend/app/services/huishan_resnet.py
#
# 对接 C 同学的 model/main_api.py（FastAPI /predict 接口）
# 模型: ResNet18 双分支迁移学习（一级5分类 + 二级26多标签）
#
# 配置:
#   AI_PROVIDER=huishan_resnet
#   HUISHAN_MODEL_URL（默认 http://localhost:8001/predict）
#
# 返回结构映射:
#   C 同学返回: {primary_label:{label,confidence}, secondary_tags:[{tag,confidence}]}
#   后端统一:   {status, style, features, report, error_message}
# ============================================================
import requests

from app.services.base import BaseAIService
from app.utils.exceptions import AIServiceError
from app.utils.files import read_upload_image_as_base64

# 二级标签中置信度超过此阈值才纳入 features 列表
_MIN_TAG_CONFIDENCE = 0.5


class HuishanResNetService(BaseAIService):
    """惠山泥人 ResNet 风格分类 Provider"""

    provider_name = 'huishan_resnet'

    def __init__(self):
        from flask import current_app

        self.api_url = current_app.config.get(
            'HUISHAN_MODEL_URL',
            'http://localhost:8001/predict',
        )
        self.timeout = current_app.config.get('HUISHAN_TIMEOUT', 30)

    def generate_3d(self, task):
        """3D 生成：ResNet 分类模型不支持，委托 Mock 占位

        说明: C 同学模型只负责风格分类；3D 生成等接入真实腾讯混元 Key 后
        切换 AI_PROVIDER=hunyuan 即可。当前用 Mock 保留演示链路（不影响
        风格分析走真实模型）。
        """
        raise AIServiceError('ResNet 仅支持风格分类，请配置 AI_GENERATION_PROVIDER=hunyuan')

    def analyze_style(self, task):
        """调用 C 同学的 ResNet 模型进行风格分类

        Args:
            task: AITask 实例（含 input_url，指向本地上传图片）

        Returns:
            dict: {'status': 'SUCCESS', 'style': str, 'features': list,
                   'report': dict, 'error_message': None}
        """
        # 1) 读取本地上传图片 → base64（防 SSRF）
        try:
            image_b64 = read_upload_image_as_base64(task.input_url)
        except Exception as e:
            raise AIServiceError(f'图片读取失败: {e}')

        # 2) 调用 C 同学的 FastAPI /predict 接口
        #    localhost 本地服务显式禁用系统代理（Clash 等代理工具可能拦截）
        files = {'file': ('image.png', _decode_base64(image_b64), 'image/png')}
        no_proxy = {'http': None, 'https': None}
        try:
            resp = requests.post(
                self.api_url, files=files, timeout=self.timeout, proxies=no_proxy
            )
        except requests.exceptions.Timeout:
            raise AIServiceError('惠山泥人模型请求超时')
        except requests.exceptions.RequestException as e:
            raise AIServiceError(f'惠山泥人模型网络请求失败: {e}')

        if resp.status_code != 200:
            raise AIServiceError(
                f'惠山泥人模型返回 HTTP {resp.status_code}: {resp.text[:200]}'
            )

        # 3) 解析响应并映射到统一结构
        try:
            body = resp.json()
        except ValueError:
            raise AIServiceError('惠山泥人模型响应 JSON 解析失败')

        if body.get('code') != 0:
            raise AIServiceError(
                f"惠山泥人模型推理异常: {body.get('msg', '未知错误')}"
            )

        # 一级标签 → style
        primary = body.get('primary_label', {})
        style = primary.get('label', '未知风格')
        primary_conf = primary.get('confidence', 0)

        # 二级标签 → features（仅取置信度达标的）
        raw_tags = body.get('secondary_tags', [])
        features = [
            f"{t['tag']}({t['confidence']:.2f})"
            for t in raw_tags
            if t.get('selected', t.get('confidence', 0) >= _MIN_TAG_CONFIDENCE) is True
        ]

        # 结构化报告
        report = {
            'primary_label': style,
            'primary_confidence': round(primary_conf, 4),
            'secondary_tags': [
                {'tag': t['tag'], 'confidence': round(t['confidence'], 4)}
                for t in raw_tags
            ],
            'description': f'一级风格: {style}（置信度 {primary_conf:.2%}），'
                           f'识别到 {len(features)} 个显著二级标签',
            'model': 'ResNet18 双分支迁移学习',
        }

        return {
            'status': 'SUCCESS',
            'style': style,
            'features': features,
            'report': report,
            'error_message': None,
        }

    def query_status(self, task):
        """同步调用，无需外部轮询"""
        return 'SUCCESS' if task.status == 'SUCCESS' else 'RUNNING'


def _decode_base64(data_url):
    """将 data URL 或纯 base64 字符串解码为字节"""
    import base64

    if ',' in data_url:
        # data:image/png;base64,xxxxx → xxxxx
        data_url = data_url.split(',', 1)[1]
    return base64.b64decode(data_url)

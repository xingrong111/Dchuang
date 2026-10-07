"""本地分类与视觉大模型协作，保留双方结果和分歧，不伪造融合准确率。"""
from app.services.base import BaseAIService
from app.services.glm import GLMService
from app.services.huishan_resnet import HuishanResNetService
from app.utils.exceptions import AIServiceError


class FusionService(BaseAIService):
    provider_name = 'fusion'
    model = 'resnet18+glm'

    def __init__(self):
        self.classifier = HuishanResNetService()
        self.vision = GLMService()

    def generate_3d(self, task):
        raise AIServiceError('融合服务仅支持风格分析，请配置生成服务')

    def analyze_style(self, task):
        from app.services.factory import _check_provider_enabled
        _check_provider_enabled('huishan_resnet')
        _check_provider_enabled('glm')
        local = self.classifier.analyze_style(task)
        visual = self.vision.analyze_style(task)
        confidence = local.get('report', {}).get('primary_confidence', 0)
        # 小模型负责固定五类标签；大模型提供开放式纹样、文化及材质描述。
        features = list(dict.fromkeys([*local.get('features', []), *visual.get('features', [])]))
        return {'status': 'SUCCESS', 'style': local['style'], 'features': features,
                'report': {'classifier': local, 'vision': visual,
                           'primary_confidence': confidence,
                           'needs_review': confidence < 0.7,
                           'description': f"分类：{local['style']}；视觉大模型：{visual['style']}。两者标签体系不同，保留原始结果供人工核对。"},
                'error_message': None}

    def query_status(self, task):
        return task.status

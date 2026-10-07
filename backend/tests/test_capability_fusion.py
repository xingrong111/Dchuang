from types import SimpleNamespace
import pytest
from app import create_app
from app.extensions import db
from app.models.ai_provider import AIProviderConfig
from app.services.factory import get_ai_service
from app.utils.exceptions import AIServiceError


def test_capability_routing():
    app=create_app('testing')
    with app.app_context():
        db.create_all()
        app.config.update(AI_PROVIDER='mock',AI_GENERATION_PROVIDER='mock',AI_ANALYSIS_PROVIDER='huishan_resnet')
        assert get_ai_service(capability='generation').provider_name=='mock'
        assert get_ai_service(capability='analysis').provider_name=='huishan_resnet'
        with pytest.raises(AIServiceError):get_ai_service(capability='analysis').generate_3d(SimpleNamespace())
        db.session.remove();db.drop_all()


def test_fusion_preserves_evidence_and_provider_governance(monkeypatch):
    from app.services.fusion import FusionService
    app=create_app('testing')
    with app.app_context():
        db.create_all()
        app.config['GLM_API_KEY']='test-fake-key'
        service=FusionService()
        monkeypatch.setattr(service.classifier,'analyze_style',lambda task:{'style':'可爱稚趣','features':['圆润'], 'report':{'primary_confidence':.6}})
        monkeypatch.setattr(service.vision,'analyze_style',lambda task:{'style':'彩绘陶土','features':['圆润','牡丹纹']})
        result=service.analyze_style(SimpleNamespace())
        assert result['features']==['圆润','牡丹纹']
        assert result['report']['needs_review'] is True
        assert result['report']['vision']['style']=='彩绘陶土'
        db.session.add(AIProviderConfig(name='glm',provider_type='analysis',enabled=False));db.session.commit()
        with pytest.raises(AIServiceError):service.analyze_style(SimpleNamespace())
        db.session.remove();db.drop_all()

import torch.nn as nn
from torchvision import models

SELECT_LEVEL2_TAGS = [
    '吉祥纹饰', '大红', '神态传神', '简约线条', '金饰', '市井人物', '动态',
    '细腻肌理', '浅绛色', '山水', '无装饰', '单色釉', '花鸟', '纹饰精美',
    '米白色', '极简造型', '华丽', '色彩鲜艳', '动物元素（可爱）', '文人',
    '戏文故事', '戏文角色', '喜庆', '色彩素雅', '形态优美', '棕色',
]


class ResNetDualBranch(nn.Module):
    def __init__(self, num_l1=5, num_l2=26, pretrained=False):
        super().__init__()
        self.backbone = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
        for index, param in enumerate(self.backbone.parameters()):
            param.requires_grad = index >= 8
        size = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()
        self.head_l1 = nn.Sequential(nn.Dropout(0.7), nn.Linear(size, num_l1))
        self.head_l2 = nn.Sequential(nn.Dropout(0.7), nn.Linear(size, num_l2))

    def forward(self, x):
        feature = self.backbone(x)
        return self.head_l1(feature), self.head_l2(feature)


class CompactDualBranch(nn.Module):
    """Small student model for measured latency/quality and distillation experiments."""
    def __init__(self, num_l1=5, num_l2=26, pretrained=False):
        super().__init__()
        layers = []
        channels = 3
        for width in (24, 48, 96, 128):
            layers.extend([nn.Conv2d(channels, width, 3, stride=2, padding=1),
                           nn.BatchNorm2d(width), nn.ReLU(inplace=True)])
            channels = width
        self.backbone = nn.Sequential(*layers, nn.AdaptiveAvgPool2d(1), nn.Flatten())
        self.head_l1 = nn.Linear(channels, num_l1)
        self.head_l2 = nn.Linear(channels, num_l2)

    def forward(self, x):
        features = self.backbone(x)
        return self.head_l1(features), self.head_l2(features)

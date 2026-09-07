from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import torch
import torch.nn as nn
from torchvision import transforms, models
from torchvision.models import ResNet18_Weights
from PIL import Image
import io
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MultiLabelBinarizer

# ===================== 和训练代码保持完全一致的配置 =====================
SAVE_MODEL_PATH = r"D:\大创项目\best_cnn.pth"
EXCEL_PATH = r"D:\大创项目\惠山泥人标注表_清洗后.xlsx"

SELECT_LEVEL2_TAGS = [
    "吉祥纹饰", "大红", "神态传神",
    "简约线条", "金饰", "市井人物", "动态",
    "细腻肌理", "浅绛色", "山水",
    "无装饰", "单色釉", "花鸟",
    "纹饰精美", "米白色", "极简造型",
    "华丽", "色彩鲜艳", "动物元素（可爱）",
    "文人", "戏文故事", "戏文角色", "喜庆",
    "色彩素雅","形态优美","棕色"
]
NUM_LEVEL2 = len(SELECT_LEVEL2_TAGS)
NUM_LEVEL1 = 5

# ---------------------- 模型类，和训练代码一模一样 ----------------------
class ResNetDualBranch(nn.Module):
    def __init__(self, num_l1=5, num_l2=26):
        super().__init__()
        backbone = models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        freeze_layer_num = 8
        for idx, param in enumerate(backbone.parameters()):
            if idx < freeze_layer_num:
                param.requires_grad = False
            else:
                param.requires_grad = True
        self.backbone = backbone
        in_feature = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()

        self.head_l1 = nn.Sequential(
            nn.Dropout(0.7),
            nn.Linear(in_feature, num_l1)
        )
        self.head_l2 = nn.Sequential(
            nn.Dropout(0.7),
            nn.Linear(in_feature, num_l2)
        )

    def forward(self, x):
        feat = self.backbone(x)
        out1 = self.head_l1(feat)
        out2 = self.head_l2(feat)
        return out1, out2

# ===================== 初始化、加载标签编码器、加载模型 =====================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 读取excel重建标签编码器（必须和训练时一致）
df = pd.read_excel(EXCEL_PATH)
le_l1 = LabelEncoder()
le_l1.fit(df["一级标签"])

def filter_tags(tag_str):
    tags = str(tag_str).split(",") if pd.notna(tag_str) else []
    return [t for t in tags if t in SELECT_LEVEL2_TAGS]
df["二级标签_筛选"] = df["二级标签"].apply(filter_tags)
mlb_l2 = MultiLabelBinarizer(classes=SELECT_LEVEL2_TAGS)
mlb_l2.fit(df["二级标签_筛选"])

# 加载模型权重
model = ResNetDualBranch(num_l1=NUM_LEVEL1, num_l2=NUM_LEVEL2).to(device)
checkpoint = torch.load(SAVE_MODEL_PATH, map_location=device)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# 推理预处理，和val_transform保持一致
infer_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

app = FastAPI(title="惠山泥人双分支分类推理接口")

@app.post("/predict")
async def predict_image(file: UploadFile = File(...)):
    """
    上传图片，返回一级分类 + 二级多标签置信度
    """
    try:
        # 读取上传图片
        contents = await file.read()
        pil_img = Image.open(io.BytesIO(contents)).convert("RGB")
        img_tensor = infer_transform(pil_img).unsqueeze(0).to(device)

        with torch.no_grad():
            out1, out2 = model(img_tensor)
            # 一级标签分类
            pred_l1_idx = torch.argmax(out1, dim=1).item()
            l1_conf = torch.softmax(out1, dim=1)[0, pred_l1_idx].item()
            l1_label = le_l1.inverse_transform([pred_l1_idx])[0]

            # 二级标签 sigmoid得到0~1置信度
            l2_sigmoid = torch.sigmoid(out2)[0].cpu().numpy()
            l2_result = []
            for tag_name, score in zip(SELECT_LEVEL2_TAGS, l2_sigmoid):
                l2_result.append({"tag": tag_name, "confidence": float(score)})

        return JSONResponse({
            "code": 0,
            "msg": "success",
            "primary_label": {
                "label": l1_label,
                "confidence": round(l1_conf,4)
            },
            "secondary_tags": l2_result
        })

    except Exception as e:
        return JSONResponse({
            "code": -1,
            "msg": f"推理异常:{str(e)}"
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import torch
from torchvision import transforms
from network import ResNetDualBranch, CompactDualBranch, SELECT_LEVEL2_TAGS
import os
import logging
from PIL import Image
import io
from pathlib import Path
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MultiLabelBinarizer

# ===================== 和训练代码保持完全一致的配置 =====================
# 路径基于本脚本所在目录（model/），避免硬编码本机绝对路径
BASE_DIR = Path(__file__).resolve().parent
SAVE_MODEL_PATH = os.getenv("HUISHAN_MODEL_CHECKPOINT", str(BASE_DIR / "best_cnn.pth"))
EXCEL_PATH = str(BASE_DIR / "惠山泥人标注表_清洗后.xlsx")

NUM_LEVEL2 = len(SELECT_LEVEL2_TAGS)
NUM_LEVEL1 = 5
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000

# ===================== 初始化、加载标签编码器、加载模型 =====================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if device.type == 'cpu':
    torch.set_num_threads(max(1, min(16, int(os.getenv('HUISHAN_CPU_THREADS', '4')))))
print(f"[main_api] 推理设备: {device}")

if not Path(SAVE_MODEL_PATH).exists():
    raise FileNotFoundError(
        f"模型权重不存在: {SAVE_MODEL_PATH}\n"
        f"请先运行 train.py 训练，或将 best_cnn.pth 放到 model/ 目录下。"
    )
if not Path(EXCEL_PATH).exists():
    raise FileNotFoundError(f"标注表不存在: {EXCEL_PATH}")

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
checkpoint = torch.load(SAVE_MODEL_PATH, map_location=device, weights_only=True)
architecture = checkpoint.get('architecture', 'resnet18')
if architecture not in ('resnet18', 'compact'):
    raise ValueError('权重网络结构未知')
model = (CompactDualBranch if architecture == 'compact' else ResNetDualBranch)(num_l1=NUM_LEVEL1, num_l2=NUM_LEVEL2).to(device)
if checkpoint.get("primary_labels", le_l1.classes_.tolist()) != le_l1.classes_.tolist():
    raise ValueError("权重一级标签顺序与标注表不一致")
if checkpoint.get("secondary_tags", SELECT_LEVEL2_TAGS) != SELECT_LEVEL2_TAGS:
    raise ValueError("权重二级标签顺序与推理服务不一致")
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()
thresholds = checkpoint.get('secondary_thresholds', [.5] * NUM_LEVEL2)
if not isinstance(thresholds, list) or len(thresholds) != NUM_LEVEL2 or any(
        not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in thresholds):
    raise ValueError('二级标签阈值配置非法')

# 推理预处理，和val_transform保持一致
infer_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

app = FastAPI(title="惠山泥人双分支分类推理接口")

@app.get("/health")
def health():
    return {"status": "ok", "device": str(device), "checkpoint": Path(SAVE_MODEL_PATH).name,
            "architecture": architecture, "primary_labels": le_l1.classes_.tolist(), "secondary_tag_count": NUM_LEVEL2}


@app.post("/predict")
def predict_image(file: UploadFile = File(...)):
    """
    上传图片，返回一级分类 + 二级多标签置信度
    """
    try:
        # 读取上传图片
        contents = file.file.read(MAX_IMAGE_BYTES + 1)
        if len(contents) > MAX_IMAGE_BYTES:
            return JSONResponse({"code": -1, "msg": "图片不能超过 10MB"}, status_code=413)
        try:
            with Image.open(io.BytesIO(contents)) as uploaded:
                if uploaded.width * uploaded.height > MAX_IMAGE_PIXELS:
                    return JSONResponse({"code": -1, "msg": "图片像素不能超过 1600 万"}, status_code=413)
                pil_img = uploaded.convert("RGB")
        except (OSError, ValueError, Image.DecompressionBombError):
            return JSONResponse({"code": -1, "msg": "无法读取图片，请上传有效图像"}, status_code=400)
        img_tensor = infer_transform(pil_img).unsqueeze(0).to(device)

        with torch.inference_mode():
            out1, out2 = model(img_tensor)
            # 一级标签分类
            pred_l1_idx = torch.argmax(out1, dim=1).item()
            l1_conf = torch.softmax(out1, dim=1)[0, pred_l1_idx].item()
            l1_label = le_l1.inverse_transform([pred_l1_idx])[0]

            # 二级标签 sigmoid得到0~1置信度
            l2_sigmoid = torch.sigmoid(out2)[0].cpu().numpy()
            l2_result = []
            for tag_name, score, threshold in zip(SELECT_LEVEL2_TAGS, l2_sigmoid, thresholds):
                l2_result.append({"tag": tag_name, "confidence": float(score), "selected": bool(score >= threshold)})

        return JSONResponse({
            "code": 0,
            "msg": "success",
            "primary_label": {
                "label": l1_label,
                "confidence": round(l1_conf,4)
            },
            "secondary_tags": l2_result
        })

    except Exception:
        logging.exception("分类模型推理失败")
        return JSONResponse({"code": -1, "msg": "模型推理失败，请查看服务日志"}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

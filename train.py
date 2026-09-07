import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from PIL import Image
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from torchvision.models import ResNet18_Weights
# =====================【配置区 不用改动，和你原来一致】=====================
EXCEL_PATH = r"D:\大创项目\惠山泥人标注表_清洗后.xlsx"
SAVE_MODEL_PATH = r"D:\大创项目\best_cnn.pth"
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
print(f"二级标签总数：{NUM_LEVEL2}")
# =========================================================================

# ---------------------- 1. 数据集类（完全复用你原来的，无需修改） ----------------------
class HuishanDataset(Dataset):
    def __init__(self, df, transform, le_l1, mlb_l2):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.le_l1 = le_l1
        self.mlb_l2 = mlb_l2

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img_path = row["图片路径"]
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)

        label_l1 = self.le_l1.transform([row["一级标签"]])[0]
        tag_list = str(row["二级标签"]).split(",") if pd.notna(row["二级标签"]) else []
        vec_l2 = self.mlb_l2.transform([tag_list])[0]

        return image, torch.tensor(label_l1, dtype=torch.long), torch.tensor(vec_l2, dtype=torch.float32)

# ---------------------- 2. ResNet18 双分支迁移学习模型【核心改动】 ----------------------
class ResNetDualBranch(nn.Module):
    def __init__(self, num_l1=5, num_l2=26):
        super().__init__()
        # 加载预训练ResNet18
        backbone = models.resnet18(pretrained=True)
        # 冻结前8层基础卷积，只微调高层与分类头，缓解小样本过拟合
        freeze_layer_num = 8
        for idx, param in enumerate(backbone.parameters()):
            if idx < freeze_layer_num:
                param.requires_grad = False
            else:
                param.requires_grad = True

        self.backbone = backbone
        in_feature = self.backbone.fc.in_features
        # 替换原ResNet全连接层，构建双分支
        self.backbone.fc = nn.Identity()  # 去掉原始分类层，只输出特征

        # 双任务分支
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

# ---------------------- 3. 数据预处理（顺序已修正，无需改动） ----------------------
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(10),
    transforms.RandomAffine(degrees=15, translate=(0.05, 0.05)),
    transforms.ColorJitter(brightness=0.2, contrast=0.15, saturation=0.1),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# ---------------------- 4. 数据加载、编码、划分（完全不变） ----------------------
df = pd.read_excel(EXCEL_PATH)

le_l1 = LabelEncoder()
le_l1.fit(df["一级标签"])

def filter_tags(tag_str):
    tags = str(tag_str).split(",") if pd.notna(tag_str) else []
    return [t for t in tags if t in SELECT_LEVEL2_TAGS]
df["二级标签_筛选"] = df["二级标签"].apply(filter_tags)

mlb_l2 = MultiLabelBinarizer(classes=SELECT_LEVEL2_TAGS)
mlb_l2.fit(df["二级标签_筛选"])

train_df, val_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["一级标签"])

train_set = HuishanDataset(train_df, train_transform, le_l1, mlb_l2)
val_set = HuishanDataset(val_df, val_transform, le_l1, mlb_l2)

train_loader = DataLoader(train_set, batch_size=8, shuffle=True)
val_loader = DataLoader(val_set, batch_size=8, shuffle=False)

# ---------------------- 5. 训练配置（学习率改为5e-5适配预训练模型） ----------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = ResNetDualBranch(num_l1=NUM_LEVEL1, num_l2=NUM_LEVEL2).to(device)

criterion_l1 = nn.CrossEntropyLoss()
criterion_l2 = nn.BCEWithLogitsLoss()
# 预训练模型用更小学习率，避免破坏预训练特征
optimizer = optim.Adam(model.parameters(), lr=5e-5, weight_decay=1.5e-4)
epochs = 40
train_acc_list = []
val_acc_list = []
train_loss_list = []
val_loss_list = []
# 早停参数
best_val_acc = 0.0
patience = 8
early_stop_counter = 0

print(f"训练集：{len(train_set)} 张，验证集：{len(val_set)} 张")
print("开始训练……")

# ---------------------- 6. 训练循环（含早停，格式和你原来一致） ----------------------
for epoch in range(epochs):
    # 训练阶段
    model.train()
    train_loss_sum = 0.0
    correct_l1 = 0
    total = 0

    for imgs, label1, vec2 in train_loader:
        imgs, label1, vec2 = imgs.to(device), label1.to(device), vec2.to(device)
        out1, out2 = model(imgs)

        loss1 = criterion_l1(out1, label1)
        loss2 = criterion_l2(out2, vec2)
        loss = loss1 + 0.9 * loss2

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        train_loss_sum += loss.item()
        pred1 = torch.argmax(out1, dim=1)
        correct_l1 += (pred1 == label1).sum().item()
        total += imgs.size(0)

    train_acc_l1 = correct_l1 / total


    # 验证阶段
    model.eval()
    val_loss_sum = 0.0
    val_correct_l1 = 0
    val_total = 0
    with torch.no_grad():
        for imgs, label1, vec2 in val_loader:
            imgs, label1, vec2 = imgs.to(device), label1.to(device), vec2.to(device)
            out1, out2 = model(imgs)
            loss1 = criterion_l1(out1, label1)
            loss2 = criterion_l2(out2, vec2)
            loss = loss1 + 0.9 * loss2
            val_loss_sum += loss.item()

            pred1 = torch.argmax(out1, dim=1)
            val_correct_l1 += (pred1 == label1).sum().item()
            val_total += imgs.size(0)
    val_acc_l1 = val_correct_l1 / val_total

    train_acc_list.append(train_acc_l1)
    val_acc_list.append(val_acc_l1)
    train_loss_list.append(train_loss_sum / len(train_loader))
    val_loss_list.append(val_loss_sum / len(val_loader))

    print(f"【Epoch {epoch+1:2d}/{epochs}】"
          f" TrainLoss:{train_loss_sum/len(train_loader):.3f} TrainAcc:{train_acc_l1:.3f} | "
          f" ValLoss:{val_loss_sum/len(val_loader):.3f} ValAcc:{val_acc_l1:.3f}")

    # 早停逻辑 + 保存最优模型
    if val_acc_l1 > best_val_acc:
        best_val_acc = val_acc_l1
        early_stop_counter = 0
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'best_acc': best_val_acc,
        }, SAVE_MODEL_PATH)
        print(f"✅ 保存最优模型，验证集一级准确率：{best_val_acc:.3f}")
    else:
        early_stop_counter += 1
        print(f"⏸ 验证准确率未提升，早停计数 {early_stop_counter}/{patience}\n")
        if early_stop_counter >= patience:
            print(f"\n🛑 连续{patience}轮验证准确率无新高，触发早停，训练终止！")
            break

# 训练全部结束后，保存训练日志（用于绘制曲线）
import numpy as np
np.save(r"D:\大创项目\train_log.npy", {
    "train_acc": train_acc_list,
    "val_acc": val_acc_list,
    "train_loss": train_loss_list,
    "val_loss": val_loss_list
})

print("\n训练结束！最优模型已保存")
print(f"🏆 全程最高验证一级准确率 = {best_val_acc:.3f}")
print("📄 训练日志 train_log.npy 已生成，可运行 evaluate.py 绘制曲线")
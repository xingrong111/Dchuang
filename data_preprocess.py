import os
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer
import joblib

# -------------------------- 1. 配置参数（可根据需求调整） --------------------------
CONFIG = {
    "annotation_path": "D:\大创项目\惠山泥人标注表_清洗后.xlsx",  # 标注表路径
    "image_root": "D:\大创项目\惠山泥人图片标识\惠山泥人图片标识",  # 图片根文件夹（若路径是绝对路径，可删此参数）
    "img_size": 224,  # CNN输入尺寸
    "batch_size": 8,  # 批次大小（GPU≥8，CPU=4）
    "test_ratio": 0.2,  # 测试集比例
    "random_seed": 42,  # 随机种子（保证结果可复现）
    "save_dir": "./model_assets"  # 编码器/数据加载器保存路径
}

# 创建保存文件夹
os.makedirs(CONFIG["save_dir"], exist_ok=True)


# -------------------------- 2. 数据增强策略（适配惠山泥人风格特征） --------------------------
def get_transforms():
    """区分训练集/测试集的增强策略，避免破坏泥人关键特征（如纹样、角色形态）"""
    # 训练集：轻度增强（保留核心特征，扩充样本多样性）
    train_transform = transforms.Compose([
        transforms.Resize((CONFIG["img_size"], CONFIG["img_size"])),  # 统一尺寸
        transforms.RandomHorizontalFlip(p=0.5),  # 50%水平翻转（不影响对称纹样）
        transforms.RandomRotation(degrees=10),  # 随机±10°旋转（避免过度倾斜）
        transforms.ColorJitter(brightness=0.2, contrast=0.1),  # 亮度/对比度微调（不改变色彩基调）
        transforms.ToTensor(),  # 转张量（0-255→0-1）
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],  # ImageNet均值（通用CNN适配）
            std=[0.229, 0.224, 0.225]  # ImageNet标准差
        )
    ])

    # 测试集：仅标准化（无增强，保证评估真实性）
    test_transform = transforms.Compose([
        transforms.Resize((CONFIG["img_size"], CONFIG["img_size"])),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    return train_transform, test_transform


# -------------------------- 3. 标注表解析与标签编码 --------------------------
def parse_annotations():
    """解析标注表，生成一级标签（单分类）和二级标签（多分类）的编码器"""
    # 读取标注表
    df = pd.read_excel(CONFIG["annotation_path"])
    # 处理图片路径（若标注表是相对路径，拼接根文件夹）
    df["图片路径"] = df["图片路径"].apply(
        lambda x: os.path.join(CONFIG["image_root"], x) if not os.path.isabs(x) else x
    )

    # 3.1 一级标签编码（单标签：如"传统喜庆"→0）
    le_primary = LabelEncoder()
    df["一级标签编码"] = le_primary.fit_transform(df["一级标签"])
    # 保存一级标签编码器
    joblib.dump(le_primary, os.path.join(CONFIG["save_dir"], "primary_label_encoder.pkl"))
    print(f"一级标签：{le_primary.classes_}（共{len(le_primary.classes_)}类）")

    # 3.2 二级标签编码（多标签：如"大红,纹饰精美"→[1,1,0,...]）
    # 拆分所有二级标签（英文逗号分隔）
    all_secondary = []
    for labels in df["二级标签"]:
        if pd.notna(labels) and str(labels).strip() != "":
            all_secondary.extend([label.strip() for label in str(labels).split(",") if label.strip()])
    # 步骤2：初始化并fit MultiLabelBinarizer
    mlb_secondary = MultiLabelBinarizer(classes=sorted(list(set(all_secondary))))
    mlb_secondary.fit([all_secondary])  # 关键：先fit所有标签类别
    # 步骤3：生成二级标签向量
    df["二级标签向量"] = df["二级标签"].apply(
        lambda x: mlb_secondary.transform([[l.strip() for l in str(x).split(",") if l.strip()]])[0]
        if pd.notna(x) and str(x).strip() != ""
        else np.zeros(len(mlb_secondary.classes_), dtype=int)
    )
    # 保存二级标签编码器
    joblib.dump(mlb_secondary, os.path.join(CONFIG["save_dir"], "secondary_label_encoder.pkl"))
    print(f"二级标签：{mlb_secondary.classes_}（共{len(mlb_secondary.classes_)}类）")

    # 3.3 分层拆分训练集/测试集（保证每类风格分布一致）
    train_df, test_df = train_test_split(
        df,
        test_size=CONFIG["test_ratio"],
        stratify=df["一级标签编码"],  # 按一级标签分层
        random_state=CONFIG["random_seed"]
    )
    print(f"\n数据拆分完成：训练集{len(train_df)}张 | 测试集{len(test_df)}张")

    return train_df, test_df, le_primary, mlb_secondary


# -------------------------- 4. 自定义数据集类 --------------------------
class HuishanDataset(Dataset):
    def __init__(self, df, transform=None):
        self.df = df
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        # 读取图片（确保RGB格式，避免灰度图报错）
        img_path = self.df.iloc[idx]["图片路径"]
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            raise ValueError(f"图片读取失败：{img_path}，错误：{str(e)}")

        # 读取标签
        primary_label = torch.tensor(self.df.iloc[idx]["一级标签编码"], dtype=torch.long)
        secondary_vec = torch.tensor(self.df.iloc[idx]["二级标签向量"], dtype=torch.float32)

        # 图片预处理
        if self.transform:
            img = self.transform(img)

        return img, primary_label, secondary_vec  # 返回：图片张量+一级标签+二级标签向量


# -------------------------- 5. 构建数据加载器（对外接口） --------------------------
def get_data_loaders():
    """主函数：生成训练集/测试集数据加载器，可直接用于模型训练"""
    # 获取增强策略
    train_transform, test_transform = get_transforms()
    # 解析标注表
    train_df, test_df, _, _ = parse_annotations()

    # 构建数据集
    train_dataset = HuishanDataset(train_df, transform=train_transform)
    test_dataset = HuishanDataset(test_df, transform=test_transform)

    # 构建数据加载器（shuffle=True打乱训练集，pin_memory加速GPU读取）
    train_loader = DataLoader(
        train_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=True,
        pin_memory=True,
        num_workers=2  # CPU线程数（根据硬件调整，0=单线程）
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=False,
        pin_memory=True,
        num_workers=2
    )

    print(f"\n数据加载器构建完成：")
    print(f"- 训练集：{len(train_loader)}个批次（每批{CONFIG['batch_size']}张）")
    print(f"- 测试集：{len(test_loader)}个批次（每批{CONFIG['batch_size']}张）")

    return train_loader, test_loader


# -------------------------- 6. 测试脚本（运行此脚本验证数据是否正常） --------------------------
if __name__ == "__main__":
    # 构建数据加载器
    train_loader, test_loader = get_data_loaders()

    # 随机抽取1个批次验证
    for imgs, primary_labels, secondary_vecs in train_loader:
        print(f"\n批次验证：")
        print(f"- 图片张量形状：{imgs.shape}（batch_size, C, H, W）")
        print(f"- 一级标签形状：{primary_labels.shape} | 示例标签：{primary_labels[:3]}")
        print(f"- 二级标签向量形状：{secondary_vecs.shape} | 示例向量：{secondary_vecs[:1]}")
        break  # 仅验证1个批次
    print("\n数据增强与加载脚本运行成功！")
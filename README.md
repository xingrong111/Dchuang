# 惠山泥人图像风格分类
大创项目：基于ResNet18双分支迁移学习，实现惠山泥人一级风格分类 + 二级多标签风格识别。

## 项目文件说明
| 文件 | 功能 |
|------|------|
| data_preprocess.py | 标注Excel数据清洗，同义标签合并、无效样本过滤 |
| train.py | ResNet18双分支模型训练、5折交叉验证、早停、混淆矩阵、Loss/Acc曲线生成 |
| main_api.py | FastAPI推理接口，上传图片返回一级、二级标签预测结果 |
| update.py | 项目辅助脚本 |
| 惠山泥人标注表_清洗后.xlsx | 清洗完成标签标注表 |

## 环境部署
1. 创建python虚拟环境
python -m venv .venv
# windows激活
.venv\Scripts\activate

2.安装全部依赖
pip install -r requirements.txt

3.运行步骤
数据清洗
修改 data_preprocess.py 内 Excel 输入输出路径，执行：
python data_preprocess.py

4.模型训练
修改 train.py 内部图片、标注表本地路径
python train.py
训练会本地生成 model_assets/标签编码器 pkl 文件，以及 best.pth 模型权重。
best.pth 权重文件体积大，不存放在 GitHub，需要手动放置到项目目录。
启动推理接口
python main_api.py
访问： http://127.0.0.1:8000/docs 打开接口调试页面，上传图片进行预测。

注意事项
仓库不包含原始数据集图片，使用者需要自行准备惠山泥人图片文件夹；
model_assets文件夹、模型权重best.pth均为训练本地产出，不会提交至 Git；
所有脚本内文件路径，需要修改为使用者本机实际路径。
# 惠山泥人风格分类

ResNet18 双分支：五类一级风格与 26 个二级标签。训练/推理共用 network.py，路径由 dataset_paths.py 及脚本目录解析。

```powershell
.\.venv\Scripts\python.exe main_api.py
```

监听 8001；GET /health 验证权重加载，POST /predict 使用 multipart file 上传图片。输入限制 10MB、1600 万像素；非法图片返回 400，超限返回 413。默认读取 best_cnn.pth，可通过 HUISHAN_MODEL_CHECKPOINT 选择实验权重，新权重的标签顺序会校验。

后端调用配置：HUISHAN_MODEL_URL=http://localhost:8001/predict，AI_ANALYSIS_PROVIDER=huishan_resnet；需要 GLM 描述时选择 fusion 并配置 GLM_API_KEY。

## 可复现实验

```powershell
.\.venv\Scripts\python.exe experiment.py evaluate --checkpoint best_cnn.pth --output reports/evaluation.json
.\.venv\Scripts\python.exe experiment.py train --folds 5 --epochs 40 --output runs/new-experiment
```

输出目录存在折次权重时拒绝覆盖，请使用新目录。训练保存标签、样本索引、种子和各折 history。验证集用于选模，不是独立测试集。--scratch 禁用 ImageNet 初始化下载；不代表与预训练版本效果相同。

现有旧权重报告：23 个重建验证样本一级 accuracy 0.8261、macro-F1 0.6866；二级 micro-F1 0.1111。旧权重无原始划分清单，不能证明无泄漏，不能把这份报告当成完整独立泛化评估。

默认推理权重 best_cnn.pth 随 Git LFS 提供，克隆后请执行 git lfs pull。训练过程生成的新权重及本机运行目录不上传。完整不足项见 ../PROJECT_AUDIT.md。


## 2026-10-02 完成的实验

完整5折汇总：runs/2026-10-02-cv-completion/cross_validation.json。前三折复核已有完整 history，第四/五折在新目录重训至早停；原目录保留。

固定去重留出划分：reports/independent-split-v1.json。113张原图，近重复保留一个代表后112张，89张用于训练/验证、23张用于测试。此为同一来源数据集留出，不是新采集的外部测试集。

五组相同测试集实测结果见 reports/研究结果.md：ResNet双任务、紧凑小模型、蒸馏、验证集阈值校准、仅一级损失消融。小模型、蒸馏和阈值校准都没有证明优于教师，因此不替换 best_cnn.pth。GLM/融合缺少凭据未执行。

```powershell
python audit_dataset.py --output reports/new-split.json
python experiment.py train --folds 1 --epochs 40 --split-manifest reports/new-split.json --output runs/new-teacher
python experiment.py train --folds 1 --epochs 40 --architecture compact --scratch --split-manifest reports/new-split.json --output runs/new-student
python experiment.py train --folds 1 --epochs 40 --architecture compact --scratch --teacher runs/new-teacher/fold_1.pth --split-manifest reports/new-split.json --output runs/new-distilled
python experiment.py evaluate --checkpoint runs/new-teacher/fold_1.pth --split-manifest reports/new-split.json --output reports/new-teacher.json
python smoke_inference.py
```

阈值校准使用 calibrate 命令和新输出.pth，仅从保存的验证集选阈值；已有历史权重若接触了测试图像，独立评估拒绝运行。推理服务兼容 compact 与经校准权重，默认仍加载原ResNet。Blender安装后可运行 build_blender_sources.py 生成三个可编辑场景；本机没有Blender，当前只有转换源脚本，没有伪造.blend文件。

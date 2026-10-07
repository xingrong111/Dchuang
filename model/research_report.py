"""Re-evaluate saved experiments with a common held-out set and write a factual comparison."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
split = root/'reports/independent-split-v1.json'
experiments = [
    ('teacher','2026-10-02-independent-teacher','fold_1.pth','ResNet18 双任务'),
    ('student','2026-10-02-independent-student','fold_1.pth','小模型，无蒸馏'),
    ('distilled','2026-10-02-independent-distilled','fold_1.pth','小模型，蒸馏'),
    ('calibrated','2026-10-02-independent-teacher','calibrated.pth','教师，验证集阈值校准'),
    ('ablation','2026-10-02-independent-ablation','fold_1.pth','ResNet18，仅一级损失'),
]
rows = []
for name, run, filename, label in experiments:
    checkpoint = root/'runs'/run/filename
    report = root/'reports'/f'independent-{name}.json'
    subprocess.run([sys.executable,str(root/'experiment.py'),'evaluate','--checkpoint',str(checkpoint),
                    '--split-manifest',str(split),'--output',str(report)],check=True)
    data = json.loads(report.read_text(encoding='utf-8'))
    rows.append({'name':name,'label':label,**{key:data[key] for key in ['accuracy','macro_f1','multilabel_micro_f1','multilabel_macro_f1','parameters','cpu_single_image_ms','sample_count']}})
(root/'reports/comparison.json').write_text(json.dumps({'protocol':'相同23张去重后固定留出图像；CPU串行批量1推理；单种子实验', 'models':rows},ensure_ascii=False,indent=2),encoding='utf-8')
lines = ['# 固定留出测试与模型对比','',
         '数据集共113张，近重复分组排除1张，89张进入训练/验证、23张留出测试；训练内部再划出18张验证用于早停/选模。',
         '测试图像未参与新模型训练、蒸馏或阈值调节，但来自同一小数据集，不等于独立外部采集数据。','',
         '| 模型 | 一级准确率 | macro-F1 | 二级 micro-F1 | 二级 macro-F1 | 参数量 | CPU ms/图 |',
         '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
for row in rows:
    lines.append(f'| {row["label"]} | {row["accuracy"]:.4f} | {row["macro_f1"]:.4f} | {row["multilabel_micro_f1"]:.4f} | {row["multilabel_macro_f1"]:.4f} | {row["parameters"]:,} | {row["cpu_single_image_ms"]:.2f} |')
lines += ['', '蒸馏没有稳定提升：一级准确率略高于无蒸馏小模型，但 macro-F1 与二级标签效果下降；验证集阈值校准也未提升二级 micro-F1，因此不替换生产权重。单任务消融的二级头未监督训练，该列只作诊断。',
          'CPU耗时包含本机负载影响，只是当前环境观测；没有报告GPU、公网或真实云服务吞吐。',
          '完整5折报告见 runs/2026-10-02-cv-completion/cross_validation.json；该实验延续原有划分，未做本轮近重复分组，验证集用于选模，不等于本次去重留出测试。',
          'GLM/融合同样本对照缺少账户凭据，尚未执行；不能用Mock结果填入研究表格。',
          '现有 best_cnn.pth 保留，新权重可通过 HUISHAN_MODEL_CHECKPOINT 显式选择。每次实验保留图像索引、标签顺序、history 和 checkpoint。']
(root/'reports/研究结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

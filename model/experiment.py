"""可复现训练与评估工具；分折验证结果与训练集诊断明确分开。"""
import argparse
import json
import random
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, classification_report, confusion_matrix
from dataset_paths import load_annotations, BASE_DIR
from network import ResNetDualBranch, CompactDualBranch, SELECT_LEVEL2_TAGS


def model_for(architecture, primary, secondary, pretrained=False):
    if architecture not in ('resnet18', 'compact'):
        raise ValueError('未知网络结构')
    return (CompactDualBranch if architecture == 'compact' else ResNetDualBranch)(primary, secondary, pretrained)


def checked_manifest(path, frame):
    document = json.loads(Path(path).read_text(encoding='utf-8'))
    ids = [str(Path(p).relative_to(BASE_DIR)) for p in frame['图片路径']]
    if document['image_ids'] != ids:
        raise ValueError('划分清单与当前数据集顺序不一致')
    from audit_dataset import image_key
    if document['image_sha256'] != [image_key(p)[0] for p in frame['图片路径']]:
        raise ValueError('图片内容已改变，拒绝沿用旧划分')
    if set(document['training_ids']) & set(document['test_ids']):
        raise ValueError('训练/测试样本重叠')
    return document


def seed_everything(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


class Images(Dataset):
    def __init__(self, frame, indices, labels, tags, augment=False):
        self.frame, self.indices, self.labels, self.tags = frame, indices, labels, tags
        steps = [transforms.Resize((224, 224))]
        if augment:
            steps += [transforms.RandomHorizontalFlip(), transforms.RandomRotation(10),
                      transforms.ColorJitter(brightness=0.2, contrast=0.15, saturation=0.1)]
        self.transform = transforms.Compose(steps + [transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

    def __len__(self): return len(self.indices)

    def __getitem__(self, index):
        i = self.indices[index]
        with Image.open(self.frame.iloc[i]['图片路径']) as image:
            x = self.transform(image.convert('RGB'))
        return x, torch.tensor(self.labels[i], dtype=torch.long), torch.tensor(self.tags[i], dtype=torch.float32)


def prepare():
    frame = load_annotations()
    encoder = LabelEncoder().fit(frame['一级标签'])
    labels = encoder.transform(frame['一级标签'])
    mlb = MultiLabelBinarizer(classes=SELECT_LEVEL2_TAGS)
    tags = mlb.fit_transform([[t.strip() for t in str(s).replace('，', ',').split(',') if t.strip() in SELECT_LEVEL2_TAGS]
                              for s in frame['二级标签']])
    return frame, labels, tags, encoder


def metrics(model, loader, device, names, thresholds=None):
    model.eval(); actual, predicted, tags, tag_predictions = [], [], [], []
    with torch.inference_mode():
        for x, y, z in loader:
            a, b = model(x.to(device))
            actual.extend(y.tolist()); predicted.extend(a.argmax(1).cpu().tolist())
            cutoff = torch.tensor(thresholds if thresholds is not None else .5, device=device)
            tags.extend(z.tolist()); tag_predictions.extend((b.sigmoid() >= cutoff).int().cpu().tolist())
    return {'sample_count': len(actual), 'accuracy': accuracy_score(actual, predicted),
            'balanced_accuracy': balanced_accuracy_score(actual, predicted),
            'macro_f1': f1_score(actual, predicted, average='macro', zero_division=0),
            'multilabel_micro_f1': f1_score(tags, tag_predictions, average='micro', zero_division=0),
            'multilabel_macro_f1': f1_score(tags, tag_predictions, average='macro', zero_division=0),
            'per_secondary_tag': classification_report(tags, tag_predictions, target_names=SELECT_LEVEL2_TAGS, output_dict=True, zero_division=0),
            'per_class': classification_report(actual, predicted, labels=list(range(len(names))), target_names=names, output_dict=True, zero_division=0),
            'confusion_matrix': confusion_matrix(actual, predicted, labels=list(range(len(names)))).tolist()}


def train(args):
    seed_everything(args.seed)
    frame, labels, tags, encoder = prepare()
    manifest = checked_manifest(args.split_manifest, frame) if args.split_manifest else None
    indices = np.array(manifest['training_ids']) if manifest else np.arange(len(frame))
    counts = np.bincount(labels[indices])
    if args.folds != 1 and not 2 <= args.folds <= counts.min():
        raise ValueError('折数需为 1 或不超过最小类别样本数')
    splits = [train_test_split(indices, test_size=.2, random_state=args.seed, stratify=labels[indices])] if args.folds == 1 else [(indices[a], indices[b]) for a, b in StratifiedKFold(args.folds, shuffle=True, random_state=args.seed).split(indices, labels[indices])]
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    if any(output.glob('fold_*.pth')) and not args.resume:
        raise FileExistsError('输出目录已有实验权重，请使用新目录，避免覆盖实验')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    teacher = None
    if args.teacher:
        if args.architecture != 'compact' or not manifest:
            raise ValueError('蒸馏要求 compact 学生与独立划分清单')
        checkpoint = torch.load(args.teacher, map_location=device, weights_only=True)
        if not checkpoint.get('training_ids') or set(checkpoint['training_ids']) & set(manifest['test_ids']):
            raise ValueError('教师训练清单缺失或接触了独立测试样本')
        if checkpoint.get('primary_labels') != encoder.classes_.tolist() or checkpoint.get('secondary_tags') != SELECT_LEVEL2_TAGS:
            raise ValueError('教师标签顺序不一致')
        teacher = model_for(checkpoint.get('architecture', 'resnet18'), len(encoder.classes_), len(SELECT_LEVEL2_TAGS)).to(device)
        teacher.load_state_dict(checkpoint['model_state_dict']); teacher.eval()
    reports = []
    image_ids = [str(Path(p).relative_to(BASE_DIR)) if Path(p).is_relative_to(BASE_DIR) else str(p) for p in frame['图片路径']]
    for fold, (training, validation) in enumerate(splits, 1):
        seed_everything(args.seed + fold)
        model = model_for(args.architecture, len(encoder.classes_), len(SELECT_LEVEL2_TAGS), pretrained=not args.scratch).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=5e-5, weight_decay=1.5e-4)
        train_loader = DataLoader(Images(frame, training, labels, tags, not args.no_augment), batch_size=8, shuffle=True)
        val_loader = DataLoader(Images(frame, validation, labels, tags), batch_size=8)
        best, stale, history = -1., 0, []
        positive = torch.tensor(tags[training].sum(axis=0), dtype=torch.float32, device=device)
        positive_weight = ((len(training) - positive) / positive.clamp(min=1)).clamp(min=1, max=8)
        path = output / f'fold_{fold}.pth'
        history_path = output / f'fold_{fold}_history.json'
        if args.resume and path.exists() and history_path.exists():
            saved = torch.load(path, map_location=device, weights_only=True)
            if saved.get('image_ids') != image_ids or saved.get('training_ids') != training.tolist() or saved.get('validation_ids') != validation.tolist() or saved.get('seed') != args.seed or saved.get('architecture', 'resnet18') != args.architecture:
                raise ValueError('已有折次的数据/划分/种子不匹配，拒绝续汇总')
            model.load_state_dict(saved['model_state_dict'])
            reports.append(metrics(model, val_loader, device, encoder.classes_.tolist()))
            print(f'fold={fold} 已完成，复核权重和指标', flush=True)
            continue
        for epoch in range(args.epochs):
            model.train(); loss_sum = 0.
            for x, y, z in train_loader:
                optimizer.zero_grad(); a,b = model(x.to(device))
                loss = nn.functional.cross_entropy(a, y.to(device)) + args.secondary_weight * nn.functional.binary_cross_entropy_with_logits(b,z.to(device), pos_weight=positive_weight)
                if teacher is not None:
                    with torch.no_grad(): ta, tb = teacher(x.to(device))
                    soft = nn.functional.kl_div((a/3).log_softmax(1), (ta/3).softmax(1), reduction='batchmean') * 9
                    soft += nn.functional.binary_cross_entropy_with_logits(b, tb.sigmoid())
                    loss = .5 * loss + .5 * soft
                loss.backward(); optimizer.step(); loss_sum += loss.item()
            report = metrics(model, val_loader, device, encoder.classes_.tolist())
            history.append({'epoch':epoch,'train_loss':loss_sum/len(train_loader),**report})
            print(f'fold={fold} epoch={epoch+1} accuracy={report["accuracy"]:.4f} macro_f1={report["macro_f1"]:.4f}',flush=True)
            score = report['macro_f1'] + .3 * report['multilabel_micro_f1']
            if score > best:
                best, stale = score, 0
                torch.save({'model_state_dict':model.state_dict(), 'epoch':epoch,'best_acc':report['accuracy'],
                    'primary_labels':encoder.classes_.tolist(), 'secondary_tags':SELECT_LEVEL2_TAGS,
                    'training_ids':training.tolist(),'validation_ids':validation.tolist(),'seed':args.seed,
                    'image_ids':image_ids, 'architecture':args.architecture,
                    'independent_test_ids':manifest['test_ids'] if manifest else [],
                    'teacher':Path(args.teacher).name if args.teacher else None}, path)
            else:
                stale += 1
                if stale >= 8: break
        model.load_state_dict(torch.load(path,map_location=device,weights_only=True)['model_state_dict'])
        reports.append(metrics(model,val_loader,device,encoder.classes_.tolist()))
        history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'protocol':'分层交叉验证；验证集用于早停与选模，非独立测试集', 'seed':args.seed,'folds':reports,
        'mean_accuracy':float(np.mean([r['accuracy'] for r in reports])),
        'std_accuracy':float(np.std([r['accuracy'] for r in reports])),
        'mean_macro_f1':float(np.mean([r['macro_f1'] for r in reports]))}
    (output/'cross_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')


def evaluate(args):
    seed_everything(args.seed)
    frame, labels, tags, encoder = prepare()
    checkpoint = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    if checkpoint.get('primary_labels', encoder.classes_.tolist()) != encoder.classes_.tolist():
        raise ValueError('权重标签顺序与数据集不一致')
    if checkpoint.get('secondary_tags', SELECT_LEVEL2_TAGS) != SELECT_LEVEL2_TAGS:
        raise ValueError('二级标签顺序不一致')
    if 'image_ids' in checkpoint and checkpoint['image_ids'] != [str(Path(p).relative_to(BASE_DIR)) if Path(p).is_relative_to(BASE_DIR) else str(p) for p in frame['图片路径']]:
        raise ValueError('数据集顺序已变化，不能沿用原验证索引')
    if args.split_manifest:
        manifest = checked_manifest(args.split_manifest, frame)
        seen = set(checkpoint.get('training_ids', [])) | set(checkpoint.get('validation_ids', []))
        if not seen or seen & set(manifest['test_ids']):
            raise ValueError('权重接触了测试集或无训练清单，不能作为独立测试')
        indices=np.array(manifest['test_ids']); protocol='预先固定、去重后的独立测试集；仅评估，不用于选模'
    elif args.all:
        indices=np.arange(len(frame)); protocol='全数据集诊断，含训练样本，不代表泛化能力'
    elif 'validation_ids' in checkpoint:
        indices=np.array(checkpoint['validation_ids']); protocol='权重保存的验证样本；用于选模，非独立测试集'
    else:
        _,indices=train_test_split(np.arange(len(frame)),test_size=.2,random_state=args.seed,stratify=labels)
        protocol='按旧训练脚本 seed=42 重建的 20% 验证划分；原权重未记录样本清单，不能证明训练无泄漏'
    model=model_for(checkpoint.get('architecture', 'resnet18'),len(encoder.classes_),len(SELECT_LEVEL2_TAGS))
    model.load_state_dict(checkpoint['model_state_dict'])
    import time
    model.eval(); sample = torch.zeros(1,3,224,224)
    with torch.inference_mode():
        for _ in range(3): model(sample)
        started=time.perf_counter()
        for _ in range(20): model(sample)
    report={'protocol':protocol,'checkpoint':Path(args.checkpoint).name,'checkpoint_epoch':checkpoint.get('epoch'),
            'architecture':checkpoint.get('architecture', 'resnet18'),
            'parameters':sum(p.numel() for p in model.parameters()),
            'cpu_single_image_ms':(time.perf_counter()-started)/20*1000,
            'primary_labels':encoder.classes_.tolist(),'secondary_tags':SELECT_LEVEL2_TAGS,
            **metrics(model,DataLoader(Images(frame,indices,labels,tags),batch_size=8),'cpu',encoder.classes_.tolist(),checkpoint.get('secondary_thresholds'))}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k in ['protocol','sample_count','accuracy','macro_f1','multilabel_micro_f1']},ensure_ascii=False))


def calibrate(args):
    seed_everything(args.seed)
    frame, labels, tags, encoder = prepare()
    if not args.split_manifest: raise ValueError('校准要求独立划分清单')
    manifest = checked_manifest(args.split_manifest, frame)
    checkpoint = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    validation = checkpoint.get('validation_ids', [])
    if not validation or (set(validation) | set(checkpoint.get('training_ids', []))) & set(manifest['test_ids']):
        raise ValueError('校准只能使用未接触独立测试集的验证样本')
    model = model_for(checkpoint.get('architecture', 'resnet18'), len(encoder.classes_), len(SELECT_LEVEL2_TAGS))
    model.load_state_dict(checkpoint['model_state_dict']); model.eval()
    actual, probabilities = [], []
    with torch.inference_mode():
        for x, _, z in DataLoader(Images(frame, validation, labels, tags), batch_size=8):
            _, logits = model(x); actual.extend(z.tolist()); probabilities.extend(logits.sigmoid().tolist())
    actual, probabilities = np.array(actual), np.array(probabilities)
    thresholds = []
    for tag in range(len(SELECT_LEVEL2_TAGS)):
        # Sparse labels cannot support reliable threshold tuning.
        if actual[:,tag].sum() < 2: thresholds.append(.5); continue
        options = [(.5, f1_score(actual[:,tag], probabilities[:,tag] >= .5, zero_division=0))]
        options += [(float(cutoff), f1_score(actual[:,tag], probabilities[:,tag] >= cutoff, zero_division=0)) for cutoff in np.arange(.1,.91,.1)]
        thresholds.append(max(options, key=lambda option: (option[1], -abs(option[0]-.5)))[0])
    checkpoint['secondary_thresholds'] = thresholds
    checkpoint['calibration_protocol'] = '只用保存的验证样本，每标签至少2个阳性；测试集未参与'
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists(): raise FileExistsError('拒绝覆盖已有校准权重')
    torch.save(checkpoint, output)
    print('已保存验证集校准权重；请单独运行独立测试评估')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['train','evaluate','calibrate'])
    parser.add_argument('--folds',type=int,default=5);parser.add_argument('--epochs',type=int,default=40)
    parser.add_argument('--seed',type=int,default=42);parser.add_argument('--scratch',action='store_true')
    parser.add_argument('--resume', action='store_true', help='只复用含完整 history 且划分匹配的已完成折次')
    parser.add_argument('--split-manifest', help='去重后的独立训练/测试划分清单')
    parser.add_argument('--architecture', choices=['resnet18','compact'], default='resnet18')
    parser.add_argument('--teacher', help='蒸馏教师权重；只允许未接触独立测试集的教师')
    parser.add_argument('--secondary-weight', type=float, default=.9, help='二级损失权重；0用于单任务消融')
    parser.add_argument('--no-augment', action='store_true', help='关闭图像增广用于消融')
    parser.add_argument('--checkpoint',default=str(BASE_DIR/'best_cnn.pth'));parser.add_argument('--all',action='store_true')
    parser.add_argument('--output');args=parser.parse_args()
    args.output=args.output or str(BASE_DIR/('runs/latest' if args.command=='train' else 'reports/evaluation.json'))
    if args.epochs < 1: parser.error('epochs 必须为正整数')
    if not 0 <= args.secondary_weight <= 10: parser.error('secondary-weight 需为 0..10')
    {'train':train,'evaluate':evaluate,'calibrate':calibrate}[args.command](args)

"""Create a reproducible split after exact/near-duplicate image grouping."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from PIL import Image
from sklearn.model_selection import train_test_split
from dataset_paths import load_annotations, BASE_DIR


def image_key(path):
    with Image.open(path) as original:
        image = original.convert('RGB')
        digest = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
        gray = image.convert('L').resize((9, 8))
        pixels = [gray.getpixel((x,y)) for y in range(8) for x in range(9)]
        bits = sum((pixels[y*9+x] > pixels[y*9+x+1]) << (y*8+x) for y in range(8) for x in range(8))
    return digest, bits


def audit(output, seed=42):
    frame = load_annotations()
    keys = [image_key(path) for path in frame['图片路径']]
    parents = list(range(len(frame)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]; i = parents[i]
        return i
    pairs = []
    for i in range(len(keys)):
        for j in range(i):
            distance = bin(keys[i][1] ^ keys[j][1]).count('1')
            if keys[i][0] == keys[j][0] or distance <= 4:
                parents[find(i)] = find(j)
                pairs.append({'a': i, 'b': j, 'exact': keys[i][0] == keys[j][0], 'dhash_distance': distance})
    groups = defaultdict(list)
    for i in range(len(frame)): groups[find(i)].append(i)
    conflicts = [indices for indices in groups.values() if len(set(frame.iloc[indices]['一级标签'])) > 1]
    # Ambiguous groups are excluded entirely; similar groups retain one representative.
    valid = [indices[0] for indices in groups.values() if indices not in conflicts]
    labels = frame.iloc[valid]['一级标签'].tolist()
    training, testing = train_test_split(valid, test_size=.2, random_state=seed, stratify=labels)
    document = {'version': 1, 'seed': seed,
                'protocol': '像素 SHA256 / dHash 距离<=4 分组后保留代表样本；冲突组排除；固定分层20%测试集，仅适用于随后新训练的权重',
                'image_ids': [str(Path(path).relative_to(BASE_DIR)) for path in frame['图片路径']],
                'image_sha256': [key[0] for key in keys], 'training_ids': sorted(training), 'test_ids': sorted(testing),
                'duplicate_pairs': pairs, 'conflicting_groups': conflicts,
                'counts': dict(Counter(frame['一级标签'])), 'training_counts': dict(Counter(frame.iloc[training]['一级标签'])),
                'test_counts': dict(Counter(frame.iloc[testing]['一级标签']))}
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): raise FileExistsError('划分清单已存在，拒绝覆盖')
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'samples':len(frame), 'training':len(training), 'testing':len(testing), 'duplicate_pairs':len(pairs), 'conflicting_groups':len(conflicts)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(BASE_DIR/'reports/independent-split-v1.json'))
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args(); audit(args.output, args.seed)

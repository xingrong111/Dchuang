"""Validate real anonymous JSONL responses and summarize without fabricating samples."""
import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
import statistics


def analyze(source):
    rows, ids = [], set()
    for number, line in enumerate(Path(source).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip(): continue
        row = json.loads(line)
        if not isinstance(row, dict) or row.get('consent') is not True:
            raise ValueError(f'第{number}行未提供同意记录')
        identifier = row.get('response_id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
            raise ValueError(f'第{number}行编号缺失或重复')
        ids.add(identifier)
        date.fromisoformat(row['session_date'])
        if row.get('mode') not in ('demo', 'live'): raise ValueError('mode 必须为 demo/live')
        for field in ('familiarity','ease','understanding','satisfaction'):
            if type(row.get(field)) is not int or not 1 <= row[field] <= 5: raise ValueError(f'{field} 必须为1..5整数')
        for field in ('browse_completed','assembly_completed','reuse'):
            if type(row.get(field)) is not bool: raise ValueError(f'{field} 必须为布尔值')
        rows.append(row)
    if not rows: raise ValueError('没有真实有效答卷，拒绝生成空样本满意度')
    return {'sample_count':len(rows), 'modes':dict(Counter(row['mode'] for row in rows)),
            'scales':{field:{'mean':statistics.mean(row[field] for row in rows),
                             'distribution':dict(Counter(row[field] for row in rows))}
                      for field in ('familiarity','ease','understanding','satisfaction')},
            'rates':{field:sum(row[field] for row in rows)/len(rows) for field in ('browse_completed','assembly_completed','reuse')},
            'limitations':'便利样本与自报体验；不能推断总体满意度；demo/live 不混作真实AI效果'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('source'); parser.add_argument('--output',required=True)
    args=parser.parse_args(); result=analyze(args.source); path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(f'已分析 {result["sample_count"]} 份答卷')

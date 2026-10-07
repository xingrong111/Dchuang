"""从项目图片库解析旧机器的标注路径，不依赖原电脑目录。"""
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = BASE_DIR / '惠山泥人标注表_清洗后.xlsx'


def load_annotations(excel_path=EXCEL_PATH):
    frame = pd.read_excel(excel_path)
    required = {'图片路径', '一级标签', '二级标签'}
    if not required.issubset(frame.columns):
        raise ValueError(f'标注缺少字段: {sorted(required - set(frame.columns))}')
    resolved = []
    for _, row in frame.iterrows():
        original = str(row['图片路径']).replace('\\', '/')
        name = original.rsplit('/', 1)[-1]
        candidate = BASE_DIR / '惠山泥人图片标识' / str(row['一级标签']) / name
        if not candidate.is_file():
            # 优先使用项目图片；兼容显式指向项目外的新增样本。
            candidate = Path(original)
        if not candidate.is_file():
            raise FileNotFoundError(f'标注图片不存在: {row["一级标签"]}/{name}')
        resolved.append(str(candidate.resolve()))
    frame = frame.copy()
    frame['图片路径'] = resolved
    return frame

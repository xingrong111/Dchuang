import pandas as pd
import numpy as np
from collections import Counter

# ===================== 配置区（按需修改路径） =====================
INPUT_EXCEL = r"D:\大创项目\惠山泥人标注表.xlsx"    # 原始标注表路径
OUTPUT_EXCEL = r"D:\大创项目\惠山泥人标注表_清洗后.xlsx" # 清洗后输出路径

# 同义标签映射：key=待替换旧标签，value=统一标准标签
TAG_REPLACE_MAP = {
    "大红色": "大红",
    "纹饰精细": "纹饰精美",
    "纹饰精致": "纹饰精美",
    "花纹细致": "纹饰精美",
    "纹理精致": "纹饰精美",
    "动态感": "动态",
    "喜庆": "喜庆",
    "节庆": "喜庆",
    "婚庆": "喜庆",
    "吉祥": "吉祥纹饰"
}
# =================================================================

def clean_single_tag(tag_text):
    """单条二级标签清洗逻辑"""
    if pd.isna(tag_text) or str(tag_text).strip() == "":
        return ""
    # 1. 中文逗号替换英文逗号
    text = str(tag_text).replace("，", ",")
    # 2. 分割标签、去除每个标签前后空格
    tag_list = [t.strip() for t in text.split(",") if t.strip()]
    # 3. 同义标签替换
    clean_tags = []
    for t in tag_list:
        std_tag = TAG_REPLACE_MAP.get(t, t)
        clean_tags.append(std_tag)
    # 去重后重新拼接英文逗号
    clean_tags = list(set(clean_tags))
    clean_tags.sort()
    return ",".join(clean_tags)


# 1. 读取表格
df = pd.read_excel(INPUT_EXCEL)
print("原始表格行数：", len(df))

# 2. 清洗二级标签列
df["二级标签"] = df["二级标签"].apply(clean_single_tag)

# 3. 统计标签分布
# 一级标签统计
level1_counter = Counter(df["一级标签"])
print("\n===== 清洗后一级标签样本分布 =====")
for tag, cnt in level1_counter.most_common():
    print(f"{tag}: {cnt}张")

# 二级标签拆分统计
all_level2 = []
for tags in df["二级标签"]:
    if tags == "":
        continue
    all_level2.extend(tags.split(","))
level2_counter = Counter(all_level2)
print("\n===== 清洗后二级标签样本分布 =====")
for tag, cnt in level2_counter.most_common():
    print(f"{tag}: {cnt}张")

# 4. 保存清洗后的文件
df.to_excel(OUTPUT_EXCEL, index=False)
print(f"\n清洗完成！文件已保存至：{OUTPUT_EXCEL}")
print("提示：检查分布，样本极少的标签可后续补充图片或合并删除")
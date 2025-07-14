import json
import os
import argparse
from collections import defaultdict
import re

def group_by_continuous_prefix(mapping, min_group_size=2):
    """
    按照 original 中的前缀进行分组。
    1. 优先按照第一个数字前的所有字符为分组前缀
    2. 如果没有数字，则按照下划线分割后的前两个部分作为前缀
    3. 无法分组的条目（小于min_group_size）会单独成组
    例如：WEAPSwrd_Weapon 01 Unequip_JSE_MW, WEAPSwrd_Weapon 02 Unequip_JSE_MW -> WEAPSwrd_Weapon
    例如：WEAPArmr_Hybrid Shield Drops_JSE_MW, WEAPArmr_Metal Shield Drops_JSE_MW -> WEAPArmr_
    """
    items = [(k, v["original"]) for k, v in mapping.items() if not v.get("translation") and v.get("original")]
    if not items:
        return []
    items.sort(key=lambda x: x[1])
    groups = {}
    for k, original in items:
        # 首先尝试匹配第一个数字出现前的所有内容作为分组前缀
        m = re.match(r'^(.*?)(?=\d)', original)
        if m and m.group(0):
            prefix = m.group(0)
        else:
            # 如果没有数字，按照下划线分割后的前两个部分作为前缀
            parts = original.split('_')
            if len(parts) >= 2:
                prefix = parts[0] + '_'
            else:
                prefix = original
        groups.setdefault(prefix, []).append((k, original))
    
    # 分离大分组和小分组
    result = []
    for group in groups.values():
        if len(group) >= min_group_size:
            result.append(group)
        else:
            # 小于min_group_size的分组，每个条目单独成组
            for item in group:
                result.append([item])
    
    return result

def main():
    parser = argparse.ArgumentParser(description="将 mapping.json 中 translation 为空的条目按连续前缀分组")
    parser.add_argument('--mapping', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'json', 'mapping.json'))
    parser.add_argument('--min-group-size', type=int, default=2, help='最小分组条数，默认2')
    parser.add_argument('--output', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'json', 'group.json'), help='输出分组文件')
    args = parser.parse_args()
    with open(args.mapping, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    groups = group_by_continuous_prefix(mapping, min_group_size=args.min_group_size)
    # 输出为 [{"group": [id, ...], "originals": [original, ...]}]
    result = [
        {"ids": [k for k, _ in group], "originals": [o for _, o in group]} for group in groups
    ]
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"已分组 {len(result)} 组，输出到 {args.output}")

if __name__ == '__main__':
    main()

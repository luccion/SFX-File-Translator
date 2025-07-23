import json
import os
import argparse
from collections import defaultdict
import re

def group_by_continuous_prefix(mapping, min_group_size=2, max_group_items=100):
    """
    按照 original 中的前缀进行分组。
    1. 优先按照第一个数字前的所有字符为分组前缀
    2. 如果没有数字，则按照下划线分割后的前两个部分作为前缀
    3. 无法分组的条目（小于min_group_size）会单独成组
    4. 如果单个分组的条目数量超过max_group_items，会将该分组拆分成多个子分组
    例如：WEAPSwrd_Weapon 01 Unequip_JSE_MW, WEAPSwrd_Weapon 02 Unequip_JSE_MW -> WEAPSwrd_Weapon
    例如：WEAPArmr_Hybrid Shield Drops_JSE_MW, WEAPArmr_Metal Shield Drops_JSE_MW -> WEAPArmr_
    """
    items = [(k, v["original"]) for k, v in mapping.items() if not v.get("translation") and v.get("original")]
    if not items:
        return []
    items.sort(key=lambda x: x[1])
    
    # 使用详细策略进行分组
    groups = {}
    for k, original in items:
        prefix = _get_prefix_by_strategy(original, "detailed")
        groups.setdefault(prefix, []).append((k, original))
    
    # 分离大分组和小分组，并处理超过max_group_items的分组
    result = []
    for group in groups.values():
        if len(group) >= min_group_size:
            # 如果分组条目数量超过max_group_items，将其拆分成多个子分组
            if len(group) > max_group_items:
                # 按照max_group_items拆分成多个子分组
                for i in range(0, len(group), max_group_items):
                    subgroup = group[i:i + max_group_items]
                    result.append(subgroup)
            else:
                result.append(group)
        else:
            # 小于min_group_size的分组，每个条目单独成组
            for item in group:
                result.append([item])
    
    return result

def _get_prefix_by_strategy(original, strategy):
    """根据策略获取前缀"""
    if strategy == "detailed":
        # 原始策略：第一个数字前的所有字符
        m = re.match(r'^(.*?)(?=\d)', original)
        if m and m.group(0) and len(m.group(0)) > 0:
            return m.group(0)
        else:
            # 如果没有数字，按照下划线分割后的前两个部分作为前缀
            parts = original.split('_')
            if len(parts) >= 2:
                return parts[0] + '_'
            else:
                return original
    elif strategy == "first_underscore":
        # 第一个下划线前的部分
        parts = original.split('_')
        return parts[0] + '_' if len(parts) > 1 else original
    elif strategy == "first_word":
        # 第一个单词或连续字符块
        m = re.match(r'^([A-Za-z]+)', original)
        if m:
            return m.group(0)
        else:
            return original[:3] if len(original) > 3 else original
    elif strategy == "single_char":
        # 单个字符前缀
        return original[0] if original else ""
    else:
        return original

def main():
    parser = argparse.ArgumentParser(description="将 mapping.json 中 translation 为空的条目按连续前缀分组")
    parser.add_argument('--mapping', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'json', 'mapping.json'))
    parser.add_argument('--min-group-size', type=int, default=2, help='最小分组条数，默认2')
    parser.add_argument('--max-group-items', type=int, default=100, help='每个分组的最大条目数量，默认100')
    parser.add_argument('--output', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'json', 'group.json'), help='输出分组文件')
    args = parser.parse_args()
    with open(args.mapping, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        groups = group_by_continuous_prefix(mapping, min_group_size=args.min_group_size, max_group_items=args.max_group_items)
    # 输出为 [{"group": [id, ...], "originals": [original, ...]}]
    result = [
        {"ids": [k for k, _ in group], "originals": [o for _, o in group]} for group in groups
    ]
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"已分组 {len(result)} 组，输出到 {args.output}")
    
    # 检查是否有超过限制的分组
    oversized_groups = [group for group in result if len(group["ids"]) > args.max_group_items]
    if oversized_groups:
        print(f"警告：有 {len(oversized_groups)} 个分组超过了最大条目数量限制 {args.max_group_items}")
    else:
        print(f"所有分组的条目数量都符合限制要求（≤{args.max_group_items}）")

if __name__ == '__main__':
    main()

import os
import json
import time
import requests
import argparse
import sys
from dotenv import load_dotenv
import importlib.util

# 加载.env配置
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# 配置区（全部从环境变量读取，提供默认值）
API_URL = os.getenv("SFX_API_URL")
API_KEY = os.getenv("SFX_API_KEY") or "your-api-key-here"
SOURCE_LANG = os.getenv("SFX_SOURCE_LANG", "en")
DEFAULT_TARGET_LANG = os.getenv("SFX_TARGET_LANG")
MODEL = os.getenv("SFX_MODEL")
TEMPERATURE = float(os.getenv("SFX_TEMPERATURE", "1.3"))
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# 文件路径
MAPPING_PATH = os.path.join(os.path.dirname(__file__), "..", "json", "mapping.json")

def batch_translate_block(block, source=SOURCE_LANG, target=DEFAULT_TARGET_LANG, max_retries=3):
    """
    block: [(id, original), ...]
    返回 {id: translation, ...}
    """
    # 构造批量输入
    items = [{"id": k, "text": v} for k, v in block]
    user_content = (
        "请将以下音效条目的text字段从英文翻译为中文，保持同类条目风格一致。\n"
        "翻译为中文。保证翻译后的中文的每一个词汇用下划线分割，不使用空格。如遇某些无法翻译的词语或缩写，就保留\n"
        "输出格式：JSON字典，key为id，value为翻译后的中文\n"
        "示例输入：[{\"id\": \"123\", \"text\": \"WeaponSword_Wooden Hit_JSE\"}]\n"
        "示例输出：{\"123\": \"武器_剑_木制_击打_JSE\"}\n\n"
        "请翻译以下条目：\n" +
        json.dumps(items, ensure_ascii=False)
    )
    
    payload = {
        "model": MODEL,
        "temperature": TEMPERATURE,
        "messages": [
            {"role": "system", "content": "你是专业的音效术语翻译助手，请将英文音效术语翻译为中文。"},
            {"role": "user", "content": user_content}
        ],
        "response_format": {"type": "json_object"}
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            result_json = json.loads(data["choices"][0]["message"]["content"])
            return result_json
        except Exception as e:
            print(f"[警告] 批量翻译失败: {e}")
            time.sleep(2 + attempt * 2)
    print("[错误] 批量翻译失败，跳过该块。内容：", block)
    return {}

def get_grouped_blocks(mapping, min_group_size=2):
    """
    直接import group_mapping_blocks.py的分组函数，避免子进程和临时文件。
    """
    code_path = os.path.join(os.path.dirname(__file__), 'group_mapping_blocks.py')
    spec = importlib.util.spec_from_file_location("group_mapping_blocks", code_path)
    group_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(group_mod)
    return group_mod.group_by_continuous_prefix(mapping, min_group_size=min_group_size)

def main():
    parser = argparse.ArgumentParser(description="自动批量翻译 mapping.json 中的 original 字段，分块保证风格统一")
    parser.add_argument("--target", type=str, default=DEFAULT_TARGET_LANG, help="目标语言代码, 默认zh-CN")
    parser.add_argument("--min-group-size", type=int, default=2, help="分组最小条数，默认2")
    args = parser.parse_args()
    target_lang = args.target
    min_group_size = args.min_group_size
    
    if not API_KEY or API_KEY == "your-api-key-here":
        print("请设置 API_KEY 环境变量或在代码中填写 API_KEY")
        sys.exit(1)
        
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    
    # 调用 group_mapping_blocks.py 生成分组
    groups = get_grouped_blocks(mapping, min_group_size=min_group_size)
    total = sum(len(g) for g in groups)
    print(f"待翻译条目数: {total}, 分为 {len(groups)} 组")
    
    done = 0
    for block in groups:
        prefix = block[0][1].split('_')[0] if block else ''
        print(f"正在翻译分组: {prefix}，共{len(block)}条")
        
        result = batch_translate_block(block, target=target_lang)
        
        # 更新翻译结果到 mapping
        updated_count = 0
        if isinstance(result, dict):
            # 检查是否有 "result" 键（AI可能返回 {"result": {...}} 格式）
            if "result" in result:
                translations = result["result"]
            else:
                translations = result
            
            # 检查translations是否为字典类型
            if isinstance(translations, dict):
                for k, v in translations.items():
                    if k in mapping:
                        mapping[k]["translation"] = v
                        updated_count += 1
                        print(f"  更新翻译: {k} -> {v}")
                    else:
                        print(f"[警告] 条目 {k} 在mapping中不存在")
            else:
                print(f"[错误] 翻译结果不是字典类型: {type(translations)}, 内容: {translations}")
        else:
            print(f"[错误] 翻译结果不是字典类型: {result}")
        
        print(f"  成功更新 {updated_count} 条翻译")
        done += len(block)
        
        # 立即保存到文件
        with open(MAPPING_PATH, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"已完成: {done}/{total}")
        time.sleep(2)  # 防止API限流
    print("全部批量翻译完成！")

if __name__ == "__main__":
    main()

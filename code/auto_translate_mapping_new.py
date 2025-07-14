import os
import json
import time
import argparse
import sys
from dotenv import load_dotenv
import importlib.util
import tiktoken
from api_clients import APIClientFactory, get_client_by_provider, load_provider_config

# 加载.env配置
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# 配置区（全部从环境变量读取，提供默认值）
SOURCE_LANG = os.getenv("SFX_SOURCE_LANG", "en")
DEFAULT_TARGET_LANG = os.getenv("SFX_TARGET_LANG")
DEFAULT_PROVIDER = os.getenv("SFX_DEFAULT_PROVIDER", "openai")

# 全局API客户端
primary_client = None
fallback_client = None

# 文件路径
MAPPING_PATH = os.path.join(os.path.dirname(__file__), "..", "json", "mapping.json")

def select_provider():
    """让用户选择服务商"""
    available_providers = APIClientFactory.get_available_providers()
    
    print("\n=== 可用的API服务商 ===")
    for i, provider in enumerate(available_providers, 1):
        print(f"{i}. {provider}")
    
    print(f"\n默认服务商: {DEFAULT_PROVIDER}")
    choice = input("请选择服务商 (直接回车使用默认): ").strip()
    
    if not choice:
        return DEFAULT_PROVIDER
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(available_providers):
            return available_providers[idx]
        else:
            print("无效选择，使用默认服务商")
            return DEFAULT_PROVIDER
    except ValueError:
        print("无效输入，使用默认服务商")
        return DEFAULT_PROVIDER

def initialize_clients(primary_provider, fallback_provider=None):
    """初始化API客户端"""
    global primary_client, fallback_client
    
    print(f"正在初始化主要服务商: {primary_provider}")
    try:
        primary_client = get_client_by_provider(primary_provider)
        print(f"✓ 主要服务商 {primary_provider} 初始化成功")
    except Exception as e:
        print(f"✗ 主要服务商 {primary_provider} 初始化失败: {e}")
        return False
    
    # 初始化备用服务商
    if fallback_provider and fallback_provider != primary_provider:
        print(f"正在初始化备用服务商: {fallback_provider}")
        try:
            fallback_client = get_client_by_provider(fallback_provider)
            print(f"✓ 备用服务商 {fallback_provider} 初始化成功")
        except Exception as e:
            print(f"✗ 备用服务商 {fallback_provider} 初始化失败: {e}")
            fallback_client = None
    
    return True

def estimate_tokens(text, model="gpt-3.5-turbo"):
    """
    估算文本的token数量
    """
    try:
        # 尝试使用对应的编码器
        if "qwen" in model.lower():
            # 通义千问模型使用类似GPT的编码方式
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        else:
            encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except:
        # 如果模型不支持，使用默认编码器
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))

def calculate_batch_tokens(block, model="gpt-3.5-turbo"):
    """
    计算一个批次的token消耗预算
    """
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
    
    system_content = "你是专业的音效术语翻译助手，请将英文音效术语翻译为中文。"
    
    # 计算输入token
    input_tokens = estimate_tokens(system_content, model) + estimate_tokens(user_content, model)
    
    # 估算输出token（假设每个条目平均生成20个token）
    estimated_output_tokens = len(block) * 20
    
    return {
        "input_tokens": input_tokens,
        "estimated_output_tokens": estimated_output_tokens,
        "total_estimated_tokens": input_tokens + estimated_output_tokens
    }

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
    
    messages = [
        {"role": "system", "content": "你是专业的音效术语翻译助手，请将英文音效术语翻译为中文。"},
        {"role": "user", "content": user_content}
    ]
    
    # 首先尝试主API
    if primary_client:
        try:
            print(f"  尝试主API ({primary_client.get_name()})")
            result = primary_client.call_api(messages, max_retries)
            return result
        except Exception as e:
            print(f"  [警告] 主API失败: {e}")
    
    # 主API失败，尝试备用API
    if fallback_client:
        try:
            print(f"  尝试备用API ({fallback_client.get_name()})")
            result = fallback_client.call_api(messages, max_retries)
            return result
        except Exception as e:
            print(f"  [警告] 备用API失败: {e}")
    
    print("[错误] 所有API都失败，跳过该块。内容：", block)
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
    parser.add_argument("--dry-run", action="store_true", help="仅计算token预算，不执行翻译")
    parser.add_argument("--provider", type=str, help="指定服务商，不指定则交互式选择")
    args = parser.parse_args()
    
    target_lang = args.target
    min_group_size = args.min_group_size
    
    # 选择服务商
    if args.provider:
        primary_provider = args.provider
    else:
        primary_provider = select_provider()
    
    # 设置备用服务商（与主服务商不同）
    available_providers = APIClientFactory.get_available_providers()
    fallback_provider = None
    for provider in available_providers:
        if provider != primary_provider:
            fallback_provider = provider
            break
    
    # 初始化API客户端
    if not initialize_clients(primary_provider, fallback_provider):
        print("API客户端初始化失败")
        sys.exit(1)
    
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    
    # 调用 group_mapping_blocks.py 生成分组
    groups = get_grouped_blocks(mapping, min_group_size=min_group_size)
    total = sum(len(g) for g in groups)
    print(f"待翻译条目数: {total}, 分为 {len(groups)} 组")
    
    # 计算token预算
    total_input_tokens = 0
    total_estimated_output_tokens = 0
    total_estimated_tokens = 0
    
    print("\n=== Token 预算计算 ===")
    model = primary_client.model if primary_client else "gpt-3.5-turbo"
    for i, block in enumerate(groups, 1):
        prefix = block[0][1].split('_')[0] if block else ''
        token_info = calculate_batch_tokens(block, model)
        total_input_tokens += token_info["input_tokens"]
        total_estimated_output_tokens += token_info["estimated_output_tokens"]
        total_estimated_tokens += token_info["total_estimated_tokens"]
        
        print(f"分组 {i}: {prefix} ({len(block)}条)")
        print(f"  输入token: {token_info['input_tokens']}")
        print(f"  预计输出token: {token_info['estimated_output_tokens']}")
        print(f"  总计token: {token_info['total_estimated_tokens']}")
    
    print(f"\n=== 总计 ===")
    print(f"总输入token: {total_input_tokens}")
    print(f"总预计输出token: {total_estimated_output_tokens}")
    print(f"总预计token: {total_estimated_tokens}")
    print(f"预估费用 (以1000token=0.001元计算): {total_estimated_tokens * 0.001 / 1000:.4f} 元")
    
    if args.dry_run:
        print("\n--dry-run 模式，不执行翻译")
        return
    
    # 询问用户是否继续
    confirm = input(f"\n是否继续执行翻译？(y/N): ").strip().lower()
    if confirm != 'y':
        print("已取消翻译")
        return
    
    print("\n开始翻译...")
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
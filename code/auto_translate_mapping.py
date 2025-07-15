import os
import json
import time
import argparse
from dotenv import load_dotenv
import importlib.util
import tiktoken
from api_clients import APIClientFactory, get_client_by_provider, ProvidersConfig

# 加载.env配置
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# 配置管理器
providers_config = ProvidersConfig()

# 全局API客户端
selected_client = None

# 文件路径
MAPPING_PATH = os.path.join(os.path.dirname(__file__), "..", "json", "mapping.json")

def select_provider():
    """让用户选择服务商"""
    providers = providers_config.list_providers()
    default_provider = providers_config.get_default_provider()
    
    print("\n=== 可用的API服务商 ===")
    for i, (provider_id, provider_name) in enumerate(providers, 1):
        print(f"{i}. {provider_name} ({provider_id})")
    
    print(f"\n默认服务商: {default_provider}")
    choice = input("请选择服务商 (直接回车使用默认): ").strip()
    
    if not choice:
        return default_provider
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(providers):
            return providers[idx][0]  # 返回provider_id
        else:
            print("无效选择，使用默认服务商")
            return default_provider
    except ValueError:
        print("无效输入，使用默认服务商")
        return default_provider

def select_model(provider_id):
    """让用户选择模型"""
    models = providers_config.get_provider_models(provider_id)
    default_model = providers_config.get_default_model(provider_id)
    
    if not models:
        print(f"服务商 {provider_id} 没有可用的模型")
        return None
    
    print(f"\n=== 可用的模型 ({provider_id}) ===")
    for i, model in enumerate(models, 1):
        model_id = model.get('id')
        model_name = model.get('name', model_id)
        model_desc = model.get('description', '')
        default_mark = " (默认)" if model_id == default_model else ""
        print(f"{i}. {model_name}{default_mark}")
        if model_desc:
            print(f"   {model_desc}")
    
    print(f"\n默认模型: {default_model}")
    choice = input("请选择模型 (直接回车使用默认): ").strip()
    
    if not choice:
        return default_model
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            return models[idx]['id']
        else:
            print("无效选择，使用默认模型")
            return default_model
    except ValueError:
        print("无效输入，使用默认模型")
        return default_model

def initialize_client(provider_id, model_id=None):
    """初始化API客户端"""
    global selected_client
    
    print(f"正在初始化服务商: {provider_id}")
    if model_id:
        print(f"使用模型: {model_id}")
    
    try:
        selected_client = get_client_by_provider(provider_id, model_id)
        print(f"✓ 服务商 {selected_client.get_name()} 初始化成功")
        return True
    except Exception as e:
        print(f"✗ 服务商 {provider_id} 初始化失败: {e}")
        return False

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

def batch_translate_block(block, max_retries=3):
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
    
    # 使用选定的客户端
    if selected_client:
        try:
            print(f"  使用API: {selected_client.get_name()}")
            result = selected_client.call_api(messages, max_retries)
            return result
        except Exception as e:
            print(f"  [错误] API调用失败: {e}")
    
    print("[错误] 没有可用的API客户端，跳过该块。内容：", block)
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
    parser.add_argument("--min-group-size", type=int, default=2, help="分组最小条数，默认2")
    parser.add_argument("--dry-run", action="store_true", help="仅计算token预算，不执行翻译")
    parser.add_argument("--provider", type=str, help="指定服务商，不指定则交互式选择")
    parser.add_argument("--model", type=str, help="指定模型，不指定则交互式选择")
    args = parser.parse_args()
    
    min_group_size = args.min_group_size
    
    # 选择服务商
    if args.provider:
        provider_id = args.provider
    else:
        provider_id = select_provider()
    
    # 选择模型
    if args.model:
        model_id = args.model
    else:
        model_id = select_model(provider_id)
    
    # 初始化API客户端
    if not initialize_client(provider_id, model_id):
        print("API客户端初始化失败")
        sys.exit(1)
    
    # ...existing code...
    
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
    model = selected_client.model if selected_client else "gpt-3.5-turbo"
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
        
        result = batch_translate_block(block)
        
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
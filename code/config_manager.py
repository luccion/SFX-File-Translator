#!/usr/bin/env python3
"""
服务商配置管理工具
用于管理 providers.json 中的服务商配置
"""

import os
import json
import argparse
from api_clients import ProvidersConfig

def list_providers():
    """列出所有服务商"""
    config = ProvidersConfig()
    providers = config.list_providers()
    default_provider = config.get_default_provider()
    
    print("=== 可用的服务商 ===")
    for provider_id, provider_name in providers:
        default_mark = " (默认)" if provider_id == default_provider else ""
        print(f"ID: {provider_id:<15} 名称: {provider_name}{default_mark}")
    
    print(f"\n当前默认服务商: {default_provider}")

def show_provider_config(provider_id):
    """显示指定服务商的配置"""
    config = ProvidersConfig()
    try:
        provider_config = config.get_provider_config(provider_id)
        models = config.get_provider_models(provider_id)
        default_model = config.get_default_model(provider_id)
        
        print(f"=== 服务商配置: {provider_id} ===")
        print(f"名称: {provider_config.get('name', provider_id)}")
        print(f"API地址: {provider_config.get('api_url')}")
        
        # 隐藏API密钥的中间部分
        api_key = provider_config.get('api_key', '')
        if api_key:
            masked_key = api_key[:6] + "***" + api_key[-4:] if len(api_key) > 10 else "***"
            print(f"API密钥: {masked_key}")
        
        print(f"客户端类型: {provider_config.get('client_type')}")
        print(f"默认模型: {default_model}")
        
        if models:
            print(f"\n可用模型:")
            for i, model in enumerate(models, 1):
                model_id = model.get('id')
                model_name = model.get('name', model_id)
                model_desc = model.get('description', '')
                default_mark = " (默认)" if model_id == default_model else ""
                print(f"  {i}. {model_name}{default_mark}")
                if model_desc:
                    print(f"     {model_desc}")
        
    except ValueError as e:
        print(f"错误: {e}")

def list_models(provider_id):
    """列出指定服务商的所有模型"""
    config = ProvidersConfig()
    try:
        models = config.get_provider_models(provider_id)
        default_model = config.get_default_model(provider_id)
        
        print(f"=== 服务商 {provider_id} 的可用模型 ===")
        if not models:
            print("没有可用的模型")
            return
        
        for i, model in enumerate(models, 1):
            model_id = model.get('id')
            model_name = model.get('name', model_id)
            model_desc = model.get('description', '')
            default_mark = " (默认)" if model_id == default_model else ""
            print(f"{i}. {model_name}{default_mark}")
            print(f"   ID: {model_id}")
            if model_desc:
                print(f"   描述: {model_desc}")
            print()
        
    except ValueError as e:
        print(f"错误: {e}")

def set_default_provider(provider_id):
    """设置默认服务商"""
    config = ProvidersConfig()
    try:
        # 验证服务商是否存在
        config.get_provider_config(provider_id)
        
        # 更新配置文件
        config.config['default_provider'] = provider_id
        with open(config.config_file, 'w', encoding='utf-8') as f:
            json.dump(config.config, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 默认服务商已设置为: {provider_id}")
    except ValueError as e:
        print(f"错误: {e}")

def set_default_model(provider_id, model_id):
    """设置服务商的默认模型"""
    config = ProvidersConfig()
    try:
        # 验证服务商和模型是否存在
        models = config.get_provider_models(provider_id)
        model_ids = [m.get('id') for m in models]
        
        if model_id not in model_ids:
            print(f"错误: 模型 {model_id} 在服务商 {provider_id} 中不存在")
            return
        
        # 更新配置文件
        config.config['providers'][provider_id]['default_model'] = model_id
        with open(config.config_file, 'w', encoding='utf-8') as f:
            json.dump(config.config, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 服务商 {provider_id} 的默认模型已设置为: {model_id}")
        
    except ValueError as e:
        print(f"错误: {e}")

def add_provider(provider_id, name, api_url, api_key, default_model, client_type="openai"):
    """添加新服务商"""
    config = ProvidersConfig()
    
    # 检查是否已存在
    if provider_id in config.get_providers():
        print(f"服务商 {provider_id} 已存在，使用 update 命令来更新配置")
        return
    
    # 添加新服务商
    new_provider = {
        "name": name,
        "api_url": api_url,
        "api_key": api_key,
        "models": [{"id": default_model, "name": default_model}],
        "default_model": default_model,
        "client_type": client_type
    }
    
    config.config['providers'][provider_id] = new_provider
    
    # 保存配置
    with open(config.config_file, 'w', encoding='utf-8') as f:
        json.dump(config.config, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 服务商 {provider_id} 已添加")

def remove_provider(provider_id):
    """删除服务商"""
    config = ProvidersConfig()
    
    if provider_id not in config.get_providers():
        print(f"服务商 {provider_id} 不存在")
        return
    
    # 不能删除默认服务商
    if provider_id == config.get_default_provider():
        print(f"不能删除默认服务商 {provider_id}，请先设置其他默认服务商")
        return
    
    # 删除服务商
    del config.config['providers'][provider_id]
    
    # 保存配置
    with open(config.config_file, 'w', encoding='utf-8') as f:
        json.dump(config.config, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 服务商 {provider_id} 已删除")

def test_provider(provider_id, model_id=None):
    """测试服务商和模型配置"""
    from api_clients import get_client_by_provider
    
    try:
        client = get_client_by_provider(provider_id, model_id)
        model_name = model_id if model_id else "默认模型"
        print(f"正在测试服务商: {client.get_name()} (模型: {model_name})")
        
        # 发送测试消息
        test_messages = [
            {"role": "system", "content": "你是一个测试助手。"},
            {"role": "user", "content": "请回复一个简单的JSON: {\"status\": \"ok\", \"message\": \"测试成功\"}"}
        ]
        
        result = client.call_api(test_messages, max_retries=1)
        print(f"✓ 测试成功: {result}")
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="服务商配置管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # list 命令
    subparsers.add_parser('list', help='列出所有服务商')
    
    # show 命令
    show_parser = subparsers.add_parser('show', help='显示服务商配置')
    show_parser.add_argument('provider_id', help='服务商ID')
    
    # models 命令
    models_parser = subparsers.add_parser('models', help='列出服务商的所有模型')
    models_parser.add_argument('provider_id', help='服务商ID')
    
    # default 命令
    default_parser = subparsers.add_parser('default', help='设置默认服务商')
    default_parser.add_argument('provider_id', help='服务商ID')
    
    # set-model 命令
    set_model_parser = subparsers.add_parser('set-model', help='设置服务商的默认模型')
    set_model_parser.add_argument('provider_id', help='服务商ID')
    set_model_parser.add_argument('model_id', help='模型ID')
    
    # add 命令
    add_parser = subparsers.add_parser('add', help='添加新服务商')
    add_parser.add_argument('provider_id', help='服务商ID')
    add_parser.add_argument('name', help='服务商名称')
    add_parser.add_argument('api_url', help='API地址')
    add_parser.add_argument('api_key', help='API密钥')
    add_parser.add_argument('default_model', help='默认模型名称')
    add_parser.add_argument('--client-type', default='openai', help='客户端类型 (默认: openai)')
    
    # remove 命令
    remove_parser = subparsers.add_parser('remove', help='删除服务商')
    remove_parser.add_argument('provider_id', help='服务商ID')
    
    # test 命令
    test_parser = subparsers.add_parser('test', help='测试服务商配置')
    test_parser.add_argument('provider_id', help='服务商ID')
    test_parser.add_argument('--model', help='指定模型ID')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_providers()
    elif args.command == 'show':
        show_provider_config(args.provider_id)
    elif args.command == 'models':
        list_models(args.provider_id)
    elif args.command == 'default':
        set_default_provider(args.provider_id)
    elif args.command == 'set-model':
        set_default_model(args.provider_id, args.model_id)
    elif args.command == 'add':
        add_provider(args.provider_id, args.name, args.api_url, 
                    args.api_key, args.default_model, args.client_type)
    elif args.command == 'remove':
        remove_provider(args.provider_id)
    elif args.command == 'test':
        test_provider(args.provider_id, getattr(args, 'model', None))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
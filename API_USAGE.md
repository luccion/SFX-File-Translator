# SFXRenamer API 服务商选择示例

## 使用方法

### 1. 交互式选择服务商
```bash
python auto_translate_mapping_new.py
```
运行后会显示可用的服务商列表，让您选择：
```
=== 可用的API服务商 ===
1. openai
2. siliconflow

默认服务商: openai
请选择服务商 (直接回车使用默认): 
```

### 2. 命令行指定服务商
```bash
# 使用OpenAI兼容服务
python auto_translate_mapping_new.py --provider openai

# 使用硅基流动服务
python auto_translate_mapping_new.py --provider siliconflow
```

### 3. 只查看token预算
```bash
python auto_translate_mapping_new.py --dry-run
```

### 4. 自定义参数
```bash
python auto_translate_mapping_new.py --provider siliconflow --min-group-size 5 --target zh-CN
```

## 服务商配置

### OpenAI兼容服务
- 使用环境变量：`SFX_API_URL`, `SFX_API_KEY`, `SFX_MODEL`
- 支持：通义千问、硅基流动OpenAI兼容接口等

### 硅基流动服务
- 使用环境变量：`SFX_FALLBACK_API_URL`, `SFX_FALLBACK_API_KEY`, `SFX_FALLBACK_MODEL`
- 直接使用HTTP请求调用API

## 特性

1. **自动备用切换** - 主服务商失败时自动切换到备用服务商
2. **Token预算计算** - 执行前预估token消耗和费用
3. **统一的API接口** - 不同服务商使用相同的调用方式
4. **灵活的配置** - 通过环境变量配置不同服务商的参数
5. **错误处理** - 完整的重试机制和错误处理
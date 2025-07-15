# SFX File Translator

一个用于批量翻译重命名音效文件的Python工具集，支持AI自动翻译和多服务商API配置。

效果取决于选择的模型，笔者使用Qwen3-30B-A3B测试，准确率约为90%，可能会有5%遗漏。遗漏部分只需再执行一遍就可以了。

效果如下：

```json
 "5": { 
    "original": "WEAPArmr_Hybrid Shield Drops_JSE_MW",
    "translation": "武器_盔甲_混合_盾牌_掉落_JSE_MW" 
  },
```

## 功能特性

- **音频文件扫描**: 自动扫描目录结构并生成文件树
- **AI自动翻译**: 支持多服务商API（通义千问、硅基流动等）
- **智能分组**: 按照命名规则分组，使翻译风格基本一致
- **批量重命名**: 基于翻译映射批量重命名文件
- **配置管理**: 完整的配置管理工具
- **JSON Schema验证**: 提供完整的数据结构验证

## 项目结构

```
SFX File Translator/
├── code/                          # 核心脚本
│   ├── generate_sfx_json.py       # 扫描音频文件并生成结构树
│   ├── auto_translate_mapping.py  # AI翻译
│   ├── group_mapping_blocks.py    # 自动分组处理
│   ├── rename_by_map.py           # 批量重命名文件
│   ├── create_placeholders.py     # 创建占位文件
│   ├── api_clients.py             # API客户端管理
│   └── config_manager.py      # 配置管理工具
├── config/                        # 配置文件
│   ├── providers.json             # 服务商配置（包含API密钥）
│   └── providers.json.example     # 服务商配置示例
├── json/                          # 数据文件
│   ├── structure.json             # 音频文件结构树
│   └── mapping.json               # ID到翻译的映射表
├── schema/                        # JSON Schema定义
│   ├── structure.schema.json      # 结构文件验证模式
│   └── mapping.schema.json        # 映射文件验证模式
├── .env                           # 环境变量配置（需要自己配置）
├── .env.example                   # 环境变量配置模板
└── README.md                      # 项目说明文档
```

## 快速开始

### 1. 环境准备

确保您的系统已安装Python 3.7+，然后安装依赖：

```bash
pip install requests python-dotenv openai tiktoken
```

### 2. 配置设置

#### 环境变量配置

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 基础配置
SFX_SOURCE_LANG=en          # 源语言
SFX_TARGET_LANG=zh-CN       # 目标语言
SFX_TEMPERATURE=1.3         # AI创造性程度

# 音频文件路径
SFX_DIR=your-audio-files-directory
SFX_PLACEHOLDER_DIR=./placeholder
```

#### 服务商配置

复制 `config/providers.json.example` 为 `config/providers.json` 并填写API密钥：

```bash
cp config/providers.json.example config/providers.json
```

支持的服务商：

- **通义千问** (dashscope)
  - 获取API密钥：[阿里云DashScope](https://dashscope.aliyun.com/)
  - 支持模型：`qwen-turbo-latest`, `qwen-turbo`, `qwen-max`

- **硅基流动** (siliconflow)
  - 获取API密钥：[硅基流动](https://siliconflow.cn/)
  - 支持模型：`Qwen/Qwen2.5-7B-Instruct`, `Qwen/QwQ-32B`, `Qwen/Qwen2.5-72B-Instruct`

可以自己手动添加额外的模型，取决于你自己的用量。

### 3. 使用流程

##### 步骤1: 扫描音频文件

```bash
cd code
python generate_sfx_json.py
```

这将扫描 `SFX_DIR` 目录下的所有音频文件，生成：
- `json/structure.json`: 文件结构树
- `json/mapping.json`: 文件ID映射表

##### 步骤2: AI自动翻译

```bash
python auto_translate_mapping.py
```

**交互式选择**：
- 先选择服务商（通义千问/硅基流动）
- 再选择对应的模型
- 显示token预算和费用估算

**命令行参数**：
```bash
# 指定服务商和模型
python auto_translate_mapping.py --provider siliconflow --model "Qwen/QwQ-32B"

# 只查看token预算
python auto_translate_mapping.py --dry-run

# 自定义分组大小
python auto_translate_mapping.py --min-group-size 5
```
#### 步骤3: 校对

手动调整`mapping.json`以达到最佳效果。

#### 步骤4: 批量重命名

```bash
python rename_by_map.py
```

根据翻译映射批量重命名音频文件。

#### 可选: 创建占位文件（用于测试）

```bash
python create_placeholders.py
```
如果你担心摧毁源文件，可以在 `SFX_PLACEHOLDER_DIR` 目录创建占位文件，用于测试重命名逻辑。

## 配置管理

### 服务商配置格式

`config/providers.json` 文件结构：

```json
{
    "providers": {
        "provider_id": {
            "name": "显示名称",
            "api_url": "API地址",
            "api_key": "your-api-key-here",
            "models": [
                {
                    "id": "模型ID",
                    "name": "模型名称",
                    "description": "模型描述"
                }
            ],
            "default_model": "默认模型ID",
            "client_type": "客户端类型"
        }
    },
    "default_provider": "默认服务商ID",
    "common_settings": {
        "temperature": 1.3,
        "max_retries": 3,
        "source_lang": "en",
        "target_lang": "zh-CN"
    }
}
```

### 客户端类型

- `openai`: 兼容OpenAI接口的服务商（如通义千问）
- `siliconflow`: 硅基流动专用客户端

你可以手动添加其他的服务商和需要的模型。

### 配置管理工具

使用 `config_manager.py` 管理配置：

```bash
# 列出所有服务商
python config_manager.py list

# 显示服务商配置
python config_manager.py show siliconflow

# 列出某个服务商的所有模型
python config_manager.py models siliconflow

# 设置默认服务商
python config_manager.py default dashscope

# 设置默认模型
python config_manager.py set-model siliconflow "Qwen/QwQ-32B"

# 测试配置
python config_manager.py test siliconflow --model "Qwen/QwQ-32B"

# 添加新服务商，还不如手动改config/providers.json
python config_manager.py add custom_provider "自定义服务商" "https://api.example.com/v1" "sk-xxx" "model-name"

# 删除服务商
python config_manager.py remove custom_provider
```

## 详细功能说明

### 音频文件扫描 (`generate_sfx_json.py`)

- 支持的音频格式：`.wav`, `.mp3`, `.flac`, `.ogg`, `.aac`, `.m4a`, `.wma`
- 为每个文件生成唯一UUID作为标识
- 保持目录结构完整性

### AI自动翻译 (`auto_translate_mapping.py`)

- 智能分组确保同类音效翻译风格一致
- 支持批量翻译提高效率
- 自动重试机制确保翻译成功率
- 中文翻译采用下划线分隔词汇

### 自动分组 (`group_mapping_blocks.py`)
自动翻译的辅助功能，保证上下文统一和降低请求次数。
将条目自动分割、分组处理，可以有效增强返回词条的连贯性。

分组规则：
1. 优先按第一个数字前的所有字符分组
2. 无数字时按下划线分割的前两部分分组
3. 小于最小分组大小的条目单独处理

### 批量重命名 (`rename_by_map.py`)

- 安全的文件重命名操作
- 自动跳过已存在的目标文件
- 详细的操作日志输出
- 异常处理确保操作安全

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

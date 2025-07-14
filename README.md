# SFXRenamer

一个用于批量重命名音效文件的Python工具集，支持AI自动翻译。

效果取决于选择的模型，笔者使用Qwen/Qwen3-30B-A3B测试，准确率约为90%，可能会有一些遗漏（5%左右）。
遗漏部分只需再执行一遍就可以了。

效果大概像这样：

```json
 "889b92f1-223c-4d5c-ba22-9eefbc0d5372": {              //UUID
    "original": "WEAPArmr_Hybrid Shield Drops_JSE_MW",  //原名
    "translation": "武器_盔甲_混合_盾牌_掉落_JSE_MW"    //AI翻译
  },
```


## 功能特性

- **音频文件扫描**: 自动扫描目录结构并生成文件树
- **AI自动翻译**: 使用AI模型自动翻译音效文件名称
- **智能分组**: 按照命名规则智能分组，确保翻译风格一致
- **批量重命名**: 基于翻译映射批量重命名文件
- **占位文件**: 创建占位文件用于测试和预览
- **JSON Schema验证**: 提供完整的数据结构验证

## 项目结构

```
SFXRenamer/
├── code/                          # 核心脚本
│   ├── generate_sfx_json.py       # 扫描音频文件并生成结构树
│   ├── auto_translate_mapping.py  # AI翻译
│   ├── group_mapping_blocks.py    # 自动分组处理
│   ├── rename_by_map.py           # 批量重命名文件
│   └── create_placeholders.py     # 创建占位文件
├── json/                          # 数据文件
│   ├── structure.json             # 音频文件结构树
│   └── mapping.json               # ID到翻译的映射表
├── schema/                        # JSON Schema定义
│   ├── structure.schema.json      # 结构文件验证模式
│   └── mapping.schema.json        # 映射文件验证模式
├── .env.example                   # 环境变量配置模板
└── README.md                      # 项目说明文档
```

## 快速开始

### 1. 环境准备

确保您的系统已安装Python 3.7+，然后安装依赖：

```bash
pip install requests python-dotenv
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下变量：

### 3. 使用流程

#### 步骤1: 扫描音频文件

```bash
cd code
python generate_sfx_json.py
```

这将扫描 `SFX_DIR` 目录下的所有音频文件，生成：
- `json/structure.json`: 文件结构树
- `json/mapping.json`: 文件ID映射表

#### 步骤2: AI自动翻译

```bash
python auto_translate_mapping.py
```

可选参数：
- `--target zh-CN`: 目标语言（默认中文）
- `--min-group-size 2`: 最小分组大小

#### 步骤3: 批量重命名

```bash
python rename_by_map.py
```

根据翻译映射批量重命名音频文件。

#### 可选: 创建占位文件（用于测试）

```bash
python create_placeholders.py
```

在 `SFX_PLACEHOLDER_DIR` 目录创建占位文件，用于测试重命名逻辑。

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

## 数据格式

使用过程无需关心数据格式，如有必要可以在schema中自行查询。

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
import os
import json
from dotenv import load_dotenv

def create_placeholders(base_dir, tree):
    for name, value in tree.items():
        if isinstance(value, dict) and 'id' in value:
            # 文件节点
            path = os.path.join(base_dir, name)
            if not os.path.exists(path):
                with open(path, 'wb') as f:
                    pass
                print(f"创建占位音频: {path}")
        elif isinstance(value, dict):
            # 文件夹节点
            path = os.path.join(base_dir, name)
            if not os.path.exists(path):
                os.makedirs(path)
            create_placeholders(path, value)

def main():
    load_dotenv()
    # 读取结构
    with open("./json/structure.json", "r", encoding="utf-8") as f:
        tree = json.load(f)
    base_dir = os.environ.get("SFX_PLACEHOLDER_DIR")
    if not base_dir:
        raise RuntimeError("请在 .env 文件中设置 SFX_PLACEHOLDER_DIR 环境变量！")
    create_placeholders(base_dir, tree)
    print("占位音频文件创建完成。")

if __name__ == "__main__":
    main()

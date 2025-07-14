import os
import json
import uuid
from dotenv import load_dotenv

# 支持的音频文件后缀
AUDIO_EXTS = ['.wav', '.mp3', '.flac', '.ogg', '.aac', '.m4a', '.wma']

def is_audio_file(filename):
    return any(filename.lower().endswith(ext) for ext in AUDIO_EXTS)

def scan_folder(folder):
    tree = {}
    for entry in sorted(os.listdir(folder)):
        path = os.path.join(folder, entry)
        if os.path.isdir(path):
            subtree = scan_folder(path)
            if subtree:
                tree[entry] = subtree
        elif is_audio_file(entry):
            # 为每个文件生成唯一id，并提取扩展名
            file_id = str(uuid.uuid4())
            name, ext = os.path.splitext(entry)
            tree[entry] = {"id": file_id, "ext": ext}
    return tree

def build_mapping(tree, mapping, parent_path=""):
    for key, value in tree.items():
        if isinstance(value, dict) and 'id' in value:
            name, _ = os.path.splitext(key)
            mapping[value['id']] = {
                "original": name,  # 只保留无扩展名部分                
                "translation": ""
            }
        elif isinstance(value, dict):
            build_mapping(value, mapping, os.path.join(parent_path, key))

def main():
    load_dotenv()
    target_dir = os.environ.get("SFX_DIR")
    if not target_dir:
        raise RuntimeError("请在 .env 文件中设置 SFX_DIR 环境变量！")
    tree = scan_folder(target_dir)
    mapping = {}
    build_mapping(tree, mapping)
    with open("./json/structure.json", "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)
    with open("./json/mapping.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print("已生成带id的 structure.json 和 i18n风格的 mapping.json")

if __name__ == "__main__":
    main()

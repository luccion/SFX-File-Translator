import os
import json
import shutil
from dotenv import load_dotenv

def find_file_by_id(tree, target_id, parent_path=""):
    for key, value in tree.items():
        if isinstance(value, dict) and 'id' in value:
            if value['id'] == target_id:
                return os.path.join(parent_path, key), value['ext']
        elif isinstance(value, dict):
            result = find_file_by_id(value, target_id, os.path.join(parent_path, key))
            if result:
                return result
    return None

def main():
    load_dotenv()
    # 读取结构和映射文件
    with open("./json/structure.json", "r", encoding="utf-8") as f:
        tree = json.load(f)
    with open("./json/mapping.json", "r", encoding="utf-8") as f:
        mapping = json.load(f)
    base_dir = os.environ.get("SFX_DIR")
    if not base_dir:
        raise RuntimeError("请在 .env 文件中设置 SFX_DIR 环境变量！")
    rename_count = 0
    for file_id, info in mapping.items():
        translation = info.get("translation", "").strip()
        if not translation:
            continue  # 跳过未填写翻译的
        result = find_file_by_id(tree, file_id)
        if not result:
            print(f"未找到id: {file_id}")
            continue
        rel_path, ext_from_tree = result
        abs_path = os.path.normpath(os.path.join(base_dir, rel_path))
        if not os.path.isfile(abs_path):
            print(f"未找到文件: {abs_path}")
            continue
        dir_name = os.path.dirname(abs_path)
        new_path = os.path.join(dir_name, translation + ext_from_tree)
        if abs_path == new_path:
            continue  # 已是目标名
        if os.path.exists(new_path):
            print(f"目标已存在，跳过: {new_path}")
            continue
        try:
            shutil.move(abs_path, new_path)
            print(f"重命名: {abs_path} -> {new_path}")
            rename_count += 1
        except Exception as e:
            print(f"重命名失败: {abs_path} -> {new_path}, 错误: {e}")
    print(f"完成，成功重命名 {rename_count} 个文件。")

if __name__ == "__main__":
    main()

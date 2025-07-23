import os
import json
import shutil
from dotenv import load_dotenv

def find_file_by_id(tree, target_id, parent_path=""):
    """根据ID在结构树中查找文件的原始路径和扩展名"""
    for key, value in tree.items():
        if isinstance(value, dict) and 'id' in value:
            if value['id'] == target_id:
                return os.path.join(parent_path, key), value['ext']
        elif isinstance(value, dict):
            result = find_file_by_id(value, target_id, os.path.join(parent_path, key))
            if result:
                return result
    return None

def find_id_by_translation(mapping, translation):
    """根据翻译名称查找对应的ID"""
    for file_id, info in mapping.items():
        if info.get("translation", "").strip() == translation:
            return file_id
    return None

def extract_original_name_from_path(file_path):
    """从文件路径中提取原始文件名（不含扩展名）"""
    return os.path.splitext(os.path.basename(file_path))[0]

def scan_directory_and_build_mapping(base_dir, tree, old_mapping):
    """扫描目录，构建新的mapping"""
    new_mapping = {}
    
    def scan_tree_node(node, current_path=""):
        for key, value in node.items():
            full_path = os.path.join(current_path, key) if current_path else key
            abs_path = os.path.join(base_dir, full_path)
            
            if isinstance(value, dict) and 'id' in value:
                # 这是一个文件节点
                file_id = value['id']
                ext = value['ext']
                
                # 查找实际存在的文件
                dir_path = os.path.dirname(abs_path)
                if os.path.exists(dir_path):
                    # 扫描目录中的所有文件
                    for filename in os.listdir(dir_path):
                        file_path = os.path.join(dir_path, filename)
                        if os.path.isfile(file_path):
                            name_without_ext = os.path.splitext(filename)[0]
                            file_ext = os.path.splitext(filename)[1]
                            
                            # 检查扩展名是否匹配
                            if file_ext == ext:
                                # 检查这个文件名是否在旧mapping中作为translation存在
                                matched_id = find_id_by_translation(old_mapping, name_without_ext)
                                if matched_id == file_id:
                                    # 找到匹配的文件
                                    original_name = extract_original_name_from_path(key)
                                    new_mapping[file_id] = {
                                        "original": original_name,
                                        "translation": name_without_ext
                                    }
                                    break
                            elif name_without_ext == extract_original_name_from_path(key):
                                # 文件名已经是原始名称
                                new_mapping[file_id] = {
                                    "original": name_without_ext,
                                    "translation": ""
                                }
                                break
                else:
                    # 目录不存在，使用原始信息
                    original_name = extract_original_name_from_path(key)
                    old_info = old_mapping.get(file_id, {})
                    new_mapping[file_id] = {
                        "original": original_name,
                        "translation": old_info.get("translation", "")
                    }
            elif isinstance(value, dict):
                # 这是一个目录节点，递归处理
                scan_tree_node(value, full_path)
    
    scan_tree_node(tree)
    return new_mapping

def restore_files_to_original_names(base_dir, tree, mapping):
    """将文件恢复为原始名称"""
    restore_count = 0
    
    for file_id, info in mapping.items():
        translation = info.get("translation", "").strip()
        if not translation:
            continue  # 跳过没有翻译的文件
        
        # 从结构树中找到原始路径
        result = find_file_by_id(tree, file_id)
        if not result:
            print(f"未找到ID对应的原始路径: {file_id}")
            continue
        
        original_rel_path, ext = result
        original_abs_path = os.path.normpath(os.path.join(base_dir, original_rel_path))
        
        # 当前文件的路径（使用翻译名称）
        dir_name = os.path.dirname(original_abs_path)
        current_path = os.path.join(dir_name, translation + ext)
        
        if not os.path.isfile(current_path):
            print(f"未找到当前文件: {current_path}")
            continue
        
        if current_path == original_abs_path:
            continue  # 已经是原始名称
        
        if os.path.exists(original_abs_path):
            print(f"原始文件已存在，跳过: {original_abs_path}")
            continue
        
        try:
            shutil.move(current_path, original_abs_path)
            print(f"恢复: {current_path} -> {original_abs_path}")
            restore_count += 1
        except Exception as e:
            print(f"恢复失败: {current_path} -> {original_abs_path}, 错误: {e}")
    
    return restore_count

def main():
    load_dotenv()
    
    # 读取结构和映射文件
    with open("./json/structure.json", "r", encoding="utf-8") as f:
        tree = json.load(f)
    with open("./json/mapping.json", "r", encoding="utf-8") as f:
        old_mapping = json.load(f)
    
    base_dir = os.environ.get("SFX_DIR")
    if not base_dir:
        raise RuntimeError("请在 .env 文件中设置 SFX_DIR 环境变量！")
    
    print("开始恢复文件名...")
    
    # 恢复文件为原始名称
    restore_count = restore_files_to_original_names(base_dir, tree, old_mapping)
    print(f"恢复完成，成功恢复 {restore_count} 个文件。")
    
    print("\n开始重新生成mapping.json...")
    
    # 重新扫描并生成新的mapping
    new_mapping = scan_directory_and_build_mapping(base_dir, tree, old_mapping)
    
    # 备份原始mapping文件
    backup_path = "./json/mapping.json.backup"
    shutil.copy("./json/mapping.json", backup_path)
    print(f"原始mapping.json已备份到: {backup_path}")
    
    # 保存新的mapping文件
    with open("./json/mapping.json", "w", encoding="utf-8") as f:
        json.dump(new_mapping, f, ensure_ascii=False, indent=2)
    
    print(f"新的mapping.json已生成，包含 {len(new_mapping)} 个条目")
    
    # 统计信息
    with_translation = sum(1 for info in new_mapping.values() if info.get("translation", "").strip())
    without_translation = len(new_mapping) - with_translation
    
    print(f"统计信息:")
    print(f"  - 有翻译的条目: {with_translation}")
    print(f"  - 无翻译的条目: {without_translation}")

if __name__ == "__main__":
    main()

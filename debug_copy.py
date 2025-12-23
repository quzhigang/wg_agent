import shutil
import os
import sys

# 设置源和目标路径
source = os.path.join(os.getcwd(), "开发资料", "web页面模板")
destination = os.path.join(os.getcwd(), "web_templates")

print(f"Source: {source}")
print(f"Destination: {destination}")

# 检查源目录是否存在
if not os.path.exists(source):
    print(f"Error: Source directory {source} does not exist.")
    sys.exit(1)

# 清理目标目录
if os.path.exists(destination):
    print("Cleaning destination directory...")
    shutil.rmtree(destination)

# 复制目录
try:
    print("Copying files...")
    shutil.copytree(source, destination)
    print(f"Successfully copied files to {destination}")
    
    # 验证复制结果
    files = os.listdir(destination)
    print(f"Files in destination: {files}")
except Exception as e:
    print(f"Error copying files: {e}")
    sys.exit(1)

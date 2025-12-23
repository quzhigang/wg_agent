import shutil
import os

source = r"开发资料/web页面模板"
destination = r"web_templates"

# Ensure destination directory is clean if it exists, or create it
if os.path.exists(destination):
    shutil.rmtree(destination)

try:
    shutil.copytree(source, destination)
    print(f"Successfully copied {source} to {destination}")
except Exception as e:
    print(f"Error copying files: {e}")

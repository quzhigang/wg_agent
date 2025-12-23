import shutil
import os

source_dir = r"开发资料\web页面模板"
target_dir = r"web_templates"

if not os.path.exists(target_dir):
    os.makedirs(target_dir)

for item in os.listdir(source_dir):
    s = os.path.join(source_dir, item)
    d = os.path.join(target_dir, item)
    if os.path.isdir(s):
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(s, d)
    else:
        shutil.copy2(s, d)
        
print("Copy completed")

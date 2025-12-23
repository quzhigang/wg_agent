import shutil
import os

source = r"开发资料\web页面模板\res_module\js\echarts.min.js"
destination = r"web_templates\res_module\js\echarts.min.js"

try:
    if os.path.exists(source):
        shutil.copy2(source, destination)
        print("Copied echarts.min.js")
    else:
        print("Source file not found")
except Exception as e:
    print(f"Error: {e}")

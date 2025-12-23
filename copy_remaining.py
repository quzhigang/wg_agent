import shutil
import os

def safe_copy(src, dst):
    try:
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print(f"Copied {src} -> {dst}")
    except Exception as e:
        print(f"Failed to copy {src}: {e}")

# Copy res_module
safe_copy(
    r"开发资料/web页面模板/res_module", 
    r"web_templates/res_module"
)

# Copy img
safe_copy(
    r"开发资料/web页面模板/img",
    r"web_templates/img"
)

# Copy main.js
if not os.path.exists(r"web_templates/js"):
    os.makedirs(r"web_templates/js")
safe_copy(
    r"开发资料/web页面模板/js/main.js",
    r"web_templates/js/main.js"
)

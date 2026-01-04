"""
PageIndex 服务启动脚本

同时启动：
- Streamlit 前端页面 (端口 8501)
- FastAPI 接口服务 (端口 8502)
"""

import subprocess
import sys
import os
import time
import signal

# 切换到 PageIndex 目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

processes = []

def cleanup(signum=None, frame=None):
    """清理所有子进程"""
    print("\n正在停止所有服务...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except:
            p.kill()
    print("所有服务已停止")
    sys.exit(0)

# 注册信号处理
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

if __name__ == "__main__":
    print("=" * 50)
    print("PageIndex 服务启动中...")
    print("=" * 50)
    
    # 启动 Streamlit 前端 (端口 8501)
    print("\n[1] 启动 Streamlit 前端页面 (端口 8501)...")
    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ]
    p1 = subprocess.Popen(streamlit_cmd)
    processes.append(p1)
    
    # 等待 Streamlit 启动
    time.sleep(2)
    
    # 启动 FastAPI 接口 (端口 8502)
    print("\n[2] 启动 FastAPI 接口服务 (端口 8502)...")
    api_cmd = [sys.executable, "api.py"]
    p2 = subprocess.Popen(api_cmd)
    processes.append(p2)
    
    print("\n" + "=" * 50)
    print("服务启动完成！")
    print("=" * 50)
    print(f"\n前端页面: http://localhost:8501")
    print(f"API 接口: http://localhost:8502")
    print(f"\nAPI 文档: http://localhost:8502/docs")
    print("\n按 Ctrl+C 停止所有服务")
    print("=" * 50)
    
    # 等待进程
    try:
        while True:
            # 检查进程状态
            for p in processes:
                if p.poll() is not None:
                    print(f"\n警告: 进程 {p.pid} 已退出")
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

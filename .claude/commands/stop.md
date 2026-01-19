# 停止项目所有服务

停止本项目的所有服务和应用。

## 需要停止的服务

1. **主服务** (端口 8000) - 卫共流域数字孪生智能体
2. **PageIndex Streamlit** (端口 8501) - 知识库管理界面
3. **PageIndex FastAPI** (端口 8502) - 知识库检索 API

## 停止方法

使用 bash 命令停止所有相关端口的进程：

```bash
netstat -ano | grep -E ":(8000|8501|8502)" | grep LISTENING | awk '{print $5}' | sort -u | xargs -r -I {} taskkill //F //PID {}
```

## 停止完成后显示

```
所有服务已停止！

已停止的服务:
  - 主服务 (端口 8000)
  - PageIndex Streamlit (端口 8501)
  - PageIndex API (端口 8502)
```

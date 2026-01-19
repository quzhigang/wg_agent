对习惯追踪 (Habit Tracker) 项目进行全面验证。

按顺序执行以下命令并报告结果：

## 1. 后端 Lint 检查

```bash
cd backend && uv run ruff check .
```

**预期结果：** 显示 "All checks passed!" 或无输出 (表示干净通过)

## 2. 后端单元测试

```bash
cd backend && uv run pytest -v
```

**预期结果：** 所有测试均通过，执行时间少于 5 秒

## 3. 后端测试及覆盖率

```bash
cd backend && uv run pytest --cov=app --cov-report=term-missing
```

**预期结果：** 覆盖率 >= 80% (在 `pyproject.toml` 中配置)

## 4. 前端构建

```bash
cd frontend && npm run build
```

**预期结果：** 构建成功完成，并输出到 `dist/` 目录

## 5. 本地服务器验证 (可选)

如果后端尚未运行，请启动它：

```bash
cd backend && uv run uvicorn app.main:app --port 8000 &
```

等待 2 秒启动时间，然后进行测试：

```bash
# 测试 habits 终端节点 (Endpoint)
curl -s http://localhost:8000/api/habits | head -c 200

# 检查 API 文档 (Docs)
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/docs
```

**预期结果：** 从 habits 终端节点获得 JSON 响应，文档页面返回 HTTP 200

如果是刚才启动的服务器，请将其停止：

```bash
# Windows
taskkill /F /IM uvicorn.exe 2>nul || true

# Linux/Mac
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
```

## 6. 总结报告 (Summary Report)

所有验证项完成后，提供一份总结报告，包含：

- Lint 检查状态
- 测试通过/失败数量
- 覆盖率百分比
- 前端构建状态
- 遇到的任何错误或警告
- 整体健康状况评估 (通过/失败)

**使用分节和状态指示符清晰地排版报告**

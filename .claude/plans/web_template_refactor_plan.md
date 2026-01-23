# Web模板数据注入与展示逻辑重构方案 (最终版)

## 1. 核心理念 (Core Philosophy)

* **轻量化传递**：工作流仅向模板传递“钥匙”（Token, ID, Path），而非“货物”（海量数据）。
* **配置驱动**：使用 JSON 配置显式定义数据提取规则，解耦工作流代码与模板代码。
* **前端自治**：Web 模板利用“钥匙”自行获取重型数据（通过 API 或 静态 JS 文件），实现前后端分离。
* **零侵入性**：不需要 LLM 在“搬运数据”环节介入，保持确定性和高性能。

## 2. 架构设计 (Architecture)

### 2.1 全量上下文 (The Context)

工作流执行过程中，维护一个不断增长的 Context 字典，它包含所有步骤的产出。

* **Inputs**: 用户原始输入（如 Query）。
* **Steps**: 各工具执行结果（如 `login.token`, `query_stcd.stcd`）。
* **State**: 全局状态。

数据传递原则：**Context 中只保留轻量级数据（IDs, Tokens, URLs, Paths）**。GB级的计算结果不进入 Context，只传递其存储路径。

### 2.2 数据库变更 (Database Schema)

在 `web_templates` 表中增加 **`replacement_config`** (JSON) 字段，作为模板的“数据映射说明书”。

### 2.3 模板配置器 (TemplateConfigurator)

一个纯 Python 工具类 `src/utils/template_configurator.py`，充当“翻译官”角色。

* **输入**：全量 Context + 模板的 `replacement_config`。
* **提取**：根据配置路径（如 `steps.login.result.token`）从 Context 中抓取数据。
* **输出**：
  * **预定义模板**：物理修改 `main.js` 等源文件（正则替换）。
  * **动态模板**：生成纯净的 `data.js` 文件。

## 3. 数据流向 (Data Flow)

### 3.1 场景 A：预定义模板 (以单一水库预报为例)

1. **WorkFlow Execution**:
    * Intent Agent: 识别目标为“盘石头水库”。
    * Tool A (Login): 获取 `token` -> 存入 Context。
    * Tool B (Query): 获取 `stcd` -> 存入 Context。
    * Context 准备就绪：包含 `token`, `stcd`, `planCode`。

2. **Configuration (DB)**:
    * `replacement_config` 定义：
        * 将 `steps.login.result.token` 映射到 `main.js / DEFAULT_PARAMS.token`。
        * 将 `steps.query.stcd` 映射到 `main.js / DEFAULT_PARAMS.stcd`。

3. **Injection (Runtime)**:
    * `TemplateConfigurator` 执行正则替换，直接将 `main.js` 中的 `token: 'OLD_VALUE'` 更新为真实Token。

4. **Frontend Rendering**:
    * 用户浏览器加载 `index.html` -> `main.js` (已含真实Token)。
    * `main.js` 执行 `fetchFloodResult()` -> **前端直接调用后端 API** 获取 50MB 洪水数据。

### 3.2 场景 B：动态生成模板

1. **WorkFlow Execution**:
    * Tool X (GIS Analysis): 生成淹没分析图，路径为 `/data/flood_map.png`。
    * Context 包含：`{"map_path": "/data/flood_map.png", "area": 500}`。

2. **Configuration**:
    * `replacement_config` 定义模式为 `json_injection`，并指定导出 `map_path` 和 `area`。

3. **Generation**:
    * `TemplateConfigurator` 生成 `web/pages/xxx/data.js`:

        ```javascript
        window.PAGE_DATA = { map_path: "/data/flood_map.png", area: 500 };
        ```

    * 生成 `index.html`，头部引用 `<script src="data.js"></script>`。

4. **Frontend Rendering**:
    * 页面 JS 读取 `window.PAGE_DATA`，将图片加载到 `<img>` 标签中。

## 4. 关键决策点 (Key Decisions)

1. **Token 限制及性能**：
    * **决策**：不在 Context 中传递重型数据实体。
    * **方案**：只传递 API URL、文件路径或 ID。

2. **安全性**：
    * **决策**：动态页面不直接嵌入 Token 或敏感数据到 HTML 源码。
    * **方案**：数据分离为 `.js` 文件。

3. **并发冲突**：
    * **风险**：预定义模板直接修改源文件，若两用户同时访问？
    * **方案（当前阶段）**：由于是单用户桌面 Agent，直接修改无风险且最简单。未来可扩展为复制副本模式。

## 5. 待执行任务清单 (Task List)

* [ ] **DB**: 确认 `web_templates` 表已包含 `replacement_config` 字段。
* [ ] **Code**: 实现 `TemplateConfigurator`，重点支持点号 (`.`) 路径提取。
* [ ] **Refactor**: 修改 `src/output/page_generator.py`，使其接收全量 `Context` 并调用 Configurator。
* [ ] **Config**: 为“盘石头水库模板”编写并录入 JSON 配置数据。

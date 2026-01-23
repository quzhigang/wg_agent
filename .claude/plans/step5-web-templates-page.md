# 步骤5: 模板管理页面实施计划

## 一、概述

**目标文件**: `web/main/web_templates.html`

**参考页面**: `web/main/saved_workflows.html` (工作流管理页面)

**功能**: 提供Web模板的可视化管理界面，支持查看、编辑、删除模板，以及向量索引管理。

---

## 二、页面结构设计

### 2.1 整体布局

```
┌─────────────────────────────────────────────────────────────┐
│  标题: Web模板管理                                           │
├─────────────────────────────────────────────────────────────┤
│  工具栏:                                                     │
│  [子意图过滤▼] [模板类型过滤▼] [刷新] [重建索引] [索引统计]   │
├─────────────────────────────────────────────────────────────┤
│  表格:                                                       │
│  序号 | 模板名称 | 模板ID | 路径 | 子意图 | 特性 | 优先级 |   │
│       | 使用次数 | 状态 | 操作                               │
├─────────────────────────────────────────────────────────────┤
│  分页: [« 上一页] [1] [2] [3] [下一页 »]                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模态框

1. **详情模态框** - 查看模板完整信息
2. **编辑模态框** - 编辑模板元数据
3. **索引统计模态框** - 显示向量索引统计信息

---

## 三、实施任务清单

### 任务1: 创建HTML基础结构

**内容**:
- DOCTYPE声明和HTML头部
- 引入与 saved_workflows.html 一致的样式变量
- 页面容器结构

**样式要点** (复用 saved_workflows.html):
- 背景渐变: `linear-gradient(135deg, #e3f2fd 0%, #f5f5f5 50%, #e8eaf6 100%)`
- 主色调: `#1976d2` (蓝色系)
- 容器圆角: `16px`
- 阴影: `0 4px 24px rgba(33,150,243,0.1)`

---

### 任务2: 工具栏区域

**HTML结构**:
```html
<div class="toolbar">
    <!-- 子意图过滤 -->
    <select id="filterSubIntent">
        <option value="">全部子意图</option>
        <option value="flood_forecast">洪水预报</option>
        <option value="data_query">数据查询</option>
        ...
    </select>

    <!-- 模板类型过滤 -->
    <select id="filterType">
        <option value="">全部类型</option>
        <option value="full_page">完整页面</option>
        <option value="component">组件</option>
        <option value="chart">图表</option>
    </select>

    <!-- 操作按钮 -->
    <button class="btn btn-refresh" onclick="loadData()">刷新</button>
    <button class="btn btn-index" onclick="rebuildIndex()">重建索引</button>
    <button class="btn btn-stats" onclick="showIndexStats()">索引统计</button>
</div>
```

---

### 任务3: 数据表格

**表格列定义**:

| 列名 | 字段 | 宽度 | 说明 |
|------|------|------|------|
| 序号 | - | 70px | 自动计算的行号 |
| 模板名称 | display_name | 150px | 中文显示名称 |
| 模板ID | name | 180px | 英文标识，等宽字体 |
| 模板路径 | template_path | 200px | 相对路径 |
| 支持子意图 | supported_sub_intents | 200px | 彩色徽章，多个 |
| 特性标签 | features | 150px | 彩色徽章，多个 |
| 优先级 | priority | 80px | 数字 |
| 使用次数 | use_count | 80px | 带图标 |
| 状态 | is_active | 80px | 开关切换 |
| 操作 | - | 200px | 详情/编辑/预览/删除 |

**子意图徽章样式** (复用 saved_workflows.html):
```css
.intent-badge { ... }
.intent-flood_forecast { background: #fce4ec; color: #c2185b; }
.intent-data_query { background: #e3f2fd; color: #1565c0; }
...
```

**特性标签样式** (新增):
```css
.feature-badge {
    display: inline-flex;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin-right: 4px;
}
.feature-map { background: #e8f5e9; color: #2e7d32; }
.feature-chart { background: #fff3e0; color: #e65100; }
.feature-realtime { background: #e3f2fd; color: #1565c0; }
.feature-reservoir { background: #ede7f6; color: #5e35b1; }
```

---

### 任务4: 详情模态框

**显示内容**:
- 基本信息: 模板ID、显示名称、模板类型
- 路径信息: 模板路径
- 描述: 详细描述文本
- 支持的子意图: 徽章列表
- 触发模式: 关键词文本
- 特性标签: 徽章列表
- 数据要求: JSON格式展示 (data_schema)
- 统计信息: 优先级、使用次数、成功次数
- 创建/更新时间

**布局**: 使用 detail-grid 两列布局，与 saved_workflows.html 一致

---

### 任务5: 编辑模态框

**可编辑字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| display_name | input | 中文名称 |
| name | input (只读) | 模板ID不可修改 |
| description | textarea | 详细描述 |
| template_path | input | 模板文件路径 |
| supported_sub_intents | 多选 | 支持的子意图 |
| template_type | select | 模板类型 |
| trigger_pattern | textarea | 触发关键词 |
| features | 多选/输入 | 特性标签 |
| priority | number | 优先级 |
| is_active | checkbox | 是否激活 |

**子意图多选实现**:
```html
<div class="checkbox-group">
    <label><input type="checkbox" value="flood_forecast"> 洪水预报</label>
    <label><input type="checkbox" value="data_query"> 数据查询</label>
    ...
</div>
```

---

### 任务6: 索引统计模态框

**显示内容**:
- 总模板数
- 已索引模板数
- 向量维度
- 最后更新时间

**API**: `GET /web-templates/vector-index/stats`

---

### 任务7: JavaScript 功能实现

**7.1 API 常量**:
```javascript
const API = '/web-templates';
```

**7.2 核心函数**:

| 函数 | 功能 |
|------|------|
| `loadData()` | 加载模板列表 |
| `renderTable(items)` | 渲染表格 |
| `renderPagination(total, page, size)` | 渲染分页 |
| `viewDetail(id)` | 查看详情 |
| `openEdit(id)` | 打开编辑 |
| `saveEdit()` | 保存编辑 |
| `deleteTemplate(id)` | 删除模板 |
| `toggleStatus(id)` | 切换状态 |
| `previewTemplate(id)` | 预览模板 |
| `rebuildIndex()` | 重建向量索引 |
| `showIndexStats()` | 显示索引统计 |
| `closeModal(id)` | 关闭模态框 |

**7.3 子意图映射**:
```javascript
const SUB_INTENT_MAP = {
    'flood_forecast': '洪水预报',
    'data_query': '数据查询',
    'flood_simulation': '洪水预演',
    'emergency_plan': '应急预案',
    'damage_assessment': '灾损评估',
    'other': '其他'
};
```

**7.4 特性标签映射**:
```javascript
const FEATURE_MAP = {
    'map': '地图',
    'chart': '图表',
    'realtime': '实时',
    'reservoir': '水库',
    'table': '表格',
    'export': '导出'
};
```

---

### 任务8: 操作按钮

**每行操作按钮**:
```html
<div class="action-btns">
    <button class="btn btn-view" onclick="viewDetail('${tpl.id}')">
        <svg>...</svg> 详情
    </button>
    <button class="btn btn-edit" onclick="openEdit('${tpl.id}')">
        <svg>...</svg> 编辑
    </button>
    <button class="btn btn-preview" onclick="previewTemplate('${tpl.id}')">
        <svg>...</svg> 预览
    </button>
    <button class="btn btn-del" onclick="deleteTemplate('${tpl.id}')">
        <svg>...</svg> 删除
    </button>
</div>
```

**新增预览按钮样式**:
```css
.btn-preview { background: #00897b; color: white; }
```

---

## 四、API 调用说明

| 操作 | 方法 | 端点 | 说明 |
|------|------|------|------|
| 获取列表 | GET | `/web-templates?page=1&size=10&sub_intent=xxx` | 分页+过滤 |
| 获取详情 | GET | `/web-templates/{id}` | 单个模板 |
| 更新模板 | PUT | `/web-templates/{id}` | 编辑保存 |
| 删除模板 | DELETE | `/web-templates/{id}` | 删除 |
| 切换状态 | PATCH | `/web-templates/{id}/toggle` | 启用/禁用 |
| 预览模板 | GET | `/web-templates/{id}/preview` | 返回预览URL |
| 重建索引 | POST | `/web-templates/vector-index/rebuild` | 重建 |
| 索引统计 | GET | `/web-templates/vector-index/stats` | 统计信息 |

---

## 五、与 saved_workflows.html 的差异点

| 项目 | saved_workflows.html | web_templates.html |
|------|---------------------|-------------------|
| API路径 | `/saved-workflows` | `/web-templates` |
| 主要字段 | plan_steps (步骤列表) | supported_sub_intents (多值) |
| 特有功能 | 步骤编辑 | 预览、索引管理 |
| 过滤条件 | 单个子意图 | 子意图 + 模板类型 |
| 状态切换 | 无 | 有 (is_active) |

---

## 六、实施顺序

1. **创建文件** - 复制 saved_workflows.html 作为基础
2. **修改标题和API** - 更新页面标题、API路径
3. **调整表格列** - 按模板字段修改列定义
4. **添加工具栏按钮** - 索引管理相关按钮
5. **修改详情模态框** - 适配模板字段
6. **修改编辑模态框** - 子意图多选、特性标签
7. **添加预览功能** - 新增预览按钮和函数
8. **添加索引管理** - 重建索引、统计信息
9. **测试验证** - 确保所有功能正常

---

## 七、预计代码量

- HTML结构: ~300行
- CSS样式: ~200行 (大部分复用)
- JavaScript: ~400行

**总计**: ~900行 (saved_workflows.html 约1040行)

---

## 八、依赖项

- 步骤4的API已实现 (`src/api/web_templates.py`)
- 数据库中有模板数据
- 向量索引服务可用

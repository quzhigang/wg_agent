---
description: 在提交前运行的代码质量与漏洞技术评审
---

对最近修改的文件进行技术性代码评审。

## 核心原则 (Core Principles)

评审理念：

- 至简即至臻 (Simplicity is the ultimate sophistication) —— 每一行代码都应有其存在的理由。
- 代码被阅读的次数远多于被编写的次数 —— 优先考虑可读性。
- 最好的代码往往是那些你没有写的代码。
- 优雅源于意图的清晰和表达的精炼。

## 评审内容 (What to Review)

首先，搜集代码库上下文，以了解项目的规范和模式。

首先检视：

- `CLAUDE.md`
- `README.md`
- `/core` 模块中的关键文件
- `/docs` 目录中记录的标准说明

在有了深入了解之后，运行以下命令：

```bash
git status
git diff HEAD
git diff --stat HEAD
```

然后检查新文件列表：

```bash
git ls-files --others --exclude-standard
```

阅读每一个新文件的全部内容。阅读每一个修改后的文件（不只是 diff 部分），以了解完整的上下文。

针对每一个修改后的文件或新文件，分析其是否存在：

1. **逻辑错误 (Logic Errors)**
   - 差一错误 (Off-by-one errors)
   - 错误的条件判断
   - 缺失错误处理
   - 竞态条件

2. **安全问题 (Security Issues)**
   - SQL 注入漏洞
   - XSS 漏洞
   - 不安全的数据处理
   - 泄露的密钥 (Secrets) 或 API keys

3. **性能问题 (Performance Problems)**
   - N+1 查询
   - 低效的算法
   - 内存泄漏
   - 不必要的计算

4. **代码质量 (Code Quality)**
   - 违反 DRY (Don't Repeat Yourself) 原则
   - 函数过于复杂
   - 命名不佳
   - 缺失类型提示/注解 (Type hints/annotations)

5. **对代码库标准和现有模式的遵循情况**
   - 是否遵循了 `/docs` 目录中记录的标准
   - Lint、类型检查及代码格式化标准
   - 日志记录标准
   - 测试标准

## 验证问题是否真实存在

- 针对发现的问题运行特定的测试
- 确认类型错误 (Type errors) 是真实合理的
- 结合上下文验证安全疑虑

## 输出格式 (Output Format)

将结果保存为新文件：`.agents/code-reviews/[适当的名称].md`

**统计信息 (Stats):**

- 修改文件数: 0
- 新增文件数: 0
- 删除文件数: 0
- 新增行数: 0
- 删除行数: 0

**针对发现的每个问题：**

```
severity: critical|high|medium|low
file: path/to/file.py
line: 42
issue: [一句话描述]
detail: [解释为什么这是一个问题]
suggestion: [如何修复它]
```

如果未发现任何问题：“代码评审已通过。未检测到技术性问题。”

## 重要注意事项 (Important)

- 必须具体（指出具体行号，而非空泛的指责）
- 专注于真实的 Bug，而非风格细节
- 提出修复建议，而非仅仅是抱怨
- 将安全问题标记为 **致命 (CRITICAL)**

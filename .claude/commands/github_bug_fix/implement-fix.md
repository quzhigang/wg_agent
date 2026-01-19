---
description: 根据 GitHub 问题的 RCA 文档实施修复
argument-hint: [github-问题-id]
allowed-tools: Read, Write, Edit, Bash(ruff:*), Bash(mypy:*), Bash(pytest:*), Bash(npm:*), Bash(bun:*)
---

# 实施修复 (Implement Fix): GitHub Issue #$ARGUMENTS

## 前提条件 (Prerequisites)

**本命令根据 RCA (根本原因分析) 文档实施 GitHub 问题的修复：**

- 在具有 GitHub 源 (origin) 的本地 Git 仓库中工作
- 根本原因分析文档位于 `docs/rca/issue-$ARGUMENTS.md`
- 已安装并验证 GitHub CLI (可选，用于状态更新)

## 参考 RCA 文档 (RCA Document to Reference)

阅读 RCA：`docs/rca/issue-$ARGUMENTS.md`

**可选 - 查看 GitHub 问题以获取背景信息：**

```bash
gh issue view $ARGUMENTS
```

## 实施指令 (Implementation Instructions)

### 1. 阅读并理解 RCA (Read and Understand RCA)

- 彻底阅读整个 RCA 文档
- 审查 GitHub 问题的详细信息 (问题 #$ARGUMENTS)
- 理解根本原因 (Root Cause)
- 审查建议的修复策略
- 记录所有待修改的文件
- 审查测试要求

### 2. 验证当前状态 (Verify Current State)

在进行更改前：

- 确认问题仍然存在
- 检查受影响文件的当前状态
- 审查这些文件最近的任何更改

### 3. 实施修复 (Implement the Fix)

遵循 RCA 中的 "建议修复 (Proposed Fix)" 章节：

**针对每个待修改的文件：**

#### a. 阅读现有文件

- 理解当前的实现方式
- 定位 RCA 中提到的具体代码

#### b. 执行修复

- 按照 RCA 中的描述实施更改
- 严格遵循修复策略
- 保持代码风格和规范的一致性
- 如果修复不够直观，请添加注释

#### c. 处理相关的更改

- 更新受该修复影响的任何相关代码
- 确保整个代码库的一致性
- 根据需要更新导入 (Imports)

### 4. 添加/更新测试 (Add/Update Tests)

遵循 RCA 中的 "测试要求 (Testing Requirements)"：

**创建测试用例以：**

1. 验证修复确实解决了问题
2. 测试与该 Bug 相关的边缘情况
3. 确保相关功能没有出现回归
4. 测试引入的所有新代码路径

**测试文件位置：**

- 遵循项目的测试结构
- 效仿源文件的存放位置
- 使用具有描述性的测试名称

**测试实施：**

```python
def test_issue_$ARGUMENTS_fix():
    """测试问题 #$ARGUMENTS 是否已修复。"""
    # Arrange - 设置导致该 Bug 的场景
    # Act - 执行之前失败的代码
    # Assert - 验证它现在能否正确工作
```

### 5. 运行验证 (Run Validation)

执行 RCA 中的验证命令：

```bash
# 运行 linter
[参考 RCA 验证命令]

# 运行类型检查
[参考 RCA 验证命令]

# 运行测试
[参考 RCA 验证命令]
```

**如果验证失败：**

- 修复发现的问题
- 重新运行验证
- 在全部通过之前，请勿继续

### 6. 验证修复 (Verify Fix)

**手动验证：**

- 遵循 RCA 中的复现步骤
- 确认问题不再发生
- 测试边缘情况
- 检查是否存在非预期的副作用

### 7. 更新文档 (Update Documentation)

如有需要：

- 更新代码注释
- 更新 API 文档
- 如果该功能面向用户，请更新 README
- 添加关于此次修复的备注

## 输出报告 (Output Report)

### 修复实施摘要 (Fix Implementation Summary)

**GitHub Issue #$ARGUMENTS**: [简短标题]

**问题 URL**: [GitHub 问题的 URL]

**根本原因** (源自 RCA):
[关于根本原因的一行总结]

### 所做的更改 (Changes Made)

**修改的文件：**

1. **[文件路径]**
   - 更改内容：[做了哪些改动]
   - 行号：[受影响的行号]

2. **[文件路径]**
   - 更改内容：[做了哪些改动]
   - 行号：[受影响的行号]

### 已添加的测试 (Tests Added)

**已创建/修改的测试文件：**

1. **[测试文件路径]**
   - 测试用例：[列出添加的测试函数]

**测试覆盖率：**

- ✅ 修复验证测试
- ✅ 边缘情况测试
- ✅ 回归预防测试

### 验证结果 (Validation Results)

```bash
# Linter 输出
[显示 lint 结果]

# 类型检查输出
[显示类型检查结果]

# 测试输出
[显示测试结果 - 全部通过]
```

### 验证情况 (Verification)

**手动测试：**

- ✅ 已遵循复现步骤 - 问题解决
- ✅ 已测试边缘情况 - 全部通过
- ✅ 未引入新问题
- ✅ 原始功能得以保留

### 文件摘要 (Files Summary)

**更改统计：**

- 修改了 X 个文件
- 创建了 Y 个文件 (测试)
- 添加了 Z 行代码
- 删除了 W 行代码

### 准备好提交 (Ready for Commit)

所有更改均已完成且已通过验证。准备执行：

```bash
/commit
```

**建议的 commit 消息：**

```
fix(scope): resolve GitHub issue #$ARGUMENTS - [简短描述]

[关于修复内容和方式的总结]

Fixes #$ARGUMENTS
```

**注意：** 在 commit 消息中使用 `Fixes #$ARGUMENTS` 会在合并到默认分支时自动关闭对应的 GitHub 问题。

### 可选：更新 GitHub 问题 (Update GitHub Issue)

**在问题中添加实施评论：**

```bash
gh issue comment $ARGUMENTS --body "修复已在 commit [commit-hash] 中实施。准备好进行评审。"
```

**更新问题标签 (如有需要)：**

```bash
gh issue edit $ARGUMENTS --add-label "fixed" --remove-label "bug"
```

**手动关闭问题 (如果不使用 commit 消息的自动关闭功能)：**

```bash
gh issue close $ARGUMENTS --comment "已修复并合并。"
```

## 备注 (Notes)

- 如果 RCA 文档缺失或不完整，请先要求使用 `/rca $ARGUMENTS` 创建该文档
- 如果在实施过程中发现 RCA 分析有误，请记录发现的问题并更新 RCA
- 如果在实施过程中发现了额外的问题，请记录下来，以便另行提交 GitHub 问题和 RCA
- 严格遵循项目的编码标准
- 在声明完成前，确保所有验证均已通过
- commit 消息 `Fixes #$ARGUMENTS` 将把该 commit 与对应的 GitHub 问题关联起来

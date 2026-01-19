---
description: 让代理预热理解代码库
---

# 预热 (Prime): 加载项目上下文

## 目标 (Objective)

通过分析结构、文档和关键文件，建立对代码库的全面理解。

## 流程 (Process)

### 1. 分析项目结构

列出所有已跟踪的文件：
!`git ls-files`

### 2. 阅读核心文档

- 阅读 `CLAUDE.md` 或类似的全局规则文件
- 阅读项目根目录及主要目录下的 `README` 文件
- 阅读任何架构文档

### 3. 识别关键文件

根据结构识别并阅读：

- 主要入口点 (main.py, index.ts, app.py 等)
- 核心配置文件 (pyproject.toml, package.json, tsconfig.json)
- 关键的模型 (Model)/模式 (Schema) 定义
- 重要的服务 (Service) 或控制器 (Controller) 文件

### 4. 了解当前状态

检查最近的活动：
!`git log -10 --oneline`

检查当前分支及状态：
!`git status`

## 输出报告 (Output Report)

提供一份简明扼要的摘要，涵盖以下内容：

### 项目概览 (Project Overview)

- 应用程序的用途和类型
- 主要技术和框架
- 当前版本/状态

### 架构 (Architecture)

- 整体结构和组织方式
- 已识别的关键架构模式
- 重要目录及其用途

### 技术栈 (Tech Stack)

- 编程语言及版本
- 框架和主要库
- 构建工具和包管理器
- 测试框架

### 核心原则 (Core Principles)

- 观察到的代码风格和规范
- 文档标准
- 测试方法

### 当前状态 (Current State)

- 活跃分支
- 最近的更改或开发重点
- 任何即时的观察或疑虑

**这份摘要力求易于扫描——请使用项目符号和清晰的标题。**

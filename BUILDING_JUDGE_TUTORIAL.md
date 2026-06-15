# Building 机评模块使用教程

## 目录

1. [模块概述](#模块概述)
2. [功能特性](#功能特性)
3. [API Key 配置](#api-key-配置)
4. [单条测试使用指南](#单条测试使用指南)
   - [Building 测试](#building-测试)
   - [Dashboard 测试](#dashboard-测试)
   - [Workflow 测试](#workflow-测试)
   - [Block 测试](#block-测试)
   - [Table 测试](#table-测试)
   - [Permission 测试](#permission-测试)
5. [批量测试使用指南](#批量测试使用指南)
6. [CSV/Excel 文件格式说明](#csvexcel-文件格式说明)
7. [常见问题](#常见问题)

---

## 模块概述

Building 机评模块是一个用于测试和评估不同类型 Agent 能力的工具。支持多种 Agent 类型、单条测试和批量测试功能。

**入口文件位置：**
- UI 界面：[building_judge_panel.py](file:///c:/Users/Admin/base/base_mrtadata/ui/building_ui/building_judge_panel.py)
- 业务逻辑：[building_spec/](file:///c:/Users/Admin/base/base_mrtadata/building_spec/)

---

## 功能特性

### 支持的 Agent 类型

| Agent 类型 | 说明 | 是否需要评估模式 |
|-----------|------|-----------------|
| **building** | 通用 Building 机评 | ✅ 是 |
| **dashboard** | 仪表盘测试 | ❌ 否 |
| **workflow** | 工作流测试 | ❌ 否 |
| **block** | 区块测试 | ❌ 否 |
| **table** | 表格测试 | ❌ 否 |
| **permission** | 权限测试 | ❌ 否 |

### 主要功能

- ✅ 单条测试：快速测试单个用例
- ✅ 批量测试：支持 CSV/Excel 文件批量导入
- ✅ 多轮对话：支持多轮对话场景测试
- ✅ 结果展示：详细的 API 响应结果
- ✅ API Key 配置：用户可配置和保存 JUDGE_API_KEY

---

## API Key 配置

在使用 Building 机评模块前，您需要先配置 `JUDGE_API_KEY`。

### 配置步骤

1. 在 Building 机评页面的 **「配置」** 区域顶部，找到 **「JUDGE_API_KEY（必填）」** 输入框
2. 在输入框中填写您的 JUDGE_API_KEY
3. （可选）点击 **「显示」** 按钮可以查看或隐藏输入的 API Key
4. 点击 **「保存」** 按钮保存配置

### 配置说明

- API Key 会自动保存到 `config/user_config.json` 文件中
- 该文件已被添加到 `.gitignore` 中，不会被提交到 Git 仓库
- 配置保存后，下次打开应用会自动加载
- 如果未配置 API Key，测试时会提示错误

---

## 单条测试使用指南

### Building 测试

**适用场景：** 通用 Building 机评，需要评估模式和评估维度。

**操作步骤：**

1. 在左侧功能模块中选择 **"Building 机评"**
2. 在 **"Agent 类型"** 下拉框中选择 **"building"**
3. 在 **"评估模式"** 中选择模式（可选：`spec` / `freeform`）
4. 在 **"评估维度"** 中勾选需要评估的维度（可选：table、permission、workflow、formula、dashboard）
5. 在 **"单条测试"** 区域：
   - **Query**：输入测试查询内容
   - **Base Token**：输入基础 Token
6. 点击 **"运行单条测试"** 按钮
7. 在 **"评测结果"** 区域查看 API 响应

---

### Dashboard 测试

**适用场景：** 仪表盘场景测试，支持多轮对话。

**操作步骤：**

1. 在左侧功能模块中选择 **"Building 机评"**
2. 在 **"Agent 类型"** 下拉框中选择 **"dashboard"**
3. 在 **"单条测试"** 区域：
   - **Queries**：输入查询内容（多轮对话每轮占一行）
     ```
     第一轮用户查询
     第二轮用户查询
     ```
   - **Before Base Token**：输入前置的 Base Token
   - **After Base Tokens**：输入后置的 Base Token（可选，多轮每轮占一行）
4. 点击 **"运行单条测试"** 按钮
5. 在 **"评测结果"** 区域查看 API 响应

**示例：**
```
Queries:
显示今年的销售额
按月份分组展示

Before Base Token:
[前置的 Base Token]

After Base Tokens:
[第一轮后 Base Token]
[第二轮后 Base Token]
```

---

### Workflow 测试

**适用场景：** 工作流测试，支持多轮对话。

**操作步骤：**

与 **Dashboard 测试** 完全相同，只需将 **"Agent 类型"** 选择为 **"workflow"**。

---

### Block 测试

**适用场景：** 区块测试，支持多轮对话。

**操作步骤：**

与 **Dashboard 测试** 完全相同，只需将 **"Agent 类型"** 选择为 **"block"**。

---

### Table 测试

**适用场景：** 表格和公式相关能力测试，支持多轮对话。

**操作步骤：**

1. 在左侧功能模块中选择 **"Building 机评"**
2. 在 **"Agent 类型"** 下拉框中选择 **"table"**
3. 在 **"单条测试"** 区域：
   - **Query**：输入查询内容（多轮对话每轮占一行）
   - **Before Base Token**：输入前置的 Base Token
   - **Base Tokens**：输入后置的 Base Token（可选，多轮每轮占一行）
4. 点击 **"运行单条测试"** 按钮
5. 在 **"评测结果"** 区域查看 API 响应

---

### Permission 测试

**适用场景：** 高级权限配置测试，支持多轮对话。

**操作步骤：**

1. 在左侧功能模块中选择 **"Building 机评"**
2. 在 **"Agent 类型"** 下拉框中选择 **"permission"**
3. 在 **"单条测试"** 区域：
   - **Query**：输入查询内容（多轮对话每轮占一行）
   - **Source Base Token**：输入前置的 Source Base Token
   - **Base Tokens**：输入后置的 Base Token（可选，多轮每轮占一行）
4. 点击 **"运行单条测试"** 按钮
5. 在 **"评测结果"** 区域查看 API 响应

---

## 批量测试使用指南

### 操作步骤

1. 在 Building 机评页面，点击右下角的 **"批量调用"** 按钮
2. 在弹出的 **"批量测试"** 对话框中：
   - 选择 **"Agent 类型"**
   - 选择测试用例文件（支持 CSV 和 Excel 格式）
   - 配置 **"并发数"**（默认 5）
3. 点击 **"开始批量测试"** 按钮
4. 在下方的结果区域查看执行结果

---

## CSV/Excel 文件格式说明

### Building 测试文件格式

| 列名 | 说明 | 必填 |
|-----|------|------|
| `query` | 查询内容 | ✅ 是 |
| `baseToken` | Base Token | ✅ 是 |
| `id` | 用例 ID | ❌ 否（自动生成） |

**CSV 示例：**
```csv
query,baseToken,id
查询2023年的销售额,XXX_TOKEN_001,case_001
显示最近30天的数据,XXX_TOKEN_002,case_002
```

**Excel 示例：**
| query | baseToken | id |
|-------|-----------|----|
| 查询2023年的销售额 | XXX_TOKEN_001 | case_001 |
| 显示最近30天的数据 | XXX_TOKEN_002 | case_002 |

---

### Dashboard/Workflow/Block/Table/Permission 测试文件格式

| 列名 | 说明 | 必填 |
|-----|------|------|
| `query` | 查询内容（多轮用换行分隔） | ✅ 是 |
| `beforeBaseToken` 或 `before_base_token` | 前置 Base Token | ✅ 是 |
| `afterBaseToken` 或 `after_base_token` | 后置 Base Token（多轮用换行分隔） | ❌ 否 |

**CSV 示例（多轮对话）：**
```csv
query,beforeBaseToken,afterBaseToken
第一轮查询
第二轮查询,XXX_BEFORE_TOKEN,第一轮后Token
第二轮后Token
```

**Excel 示例（多轮对话）：**
| query | beforeBaseToken | afterBaseToken |
|-------|-----------------|----------------|
| 第一轮查询<br/>第二轮查询 | XXX_BEFORE_TOKEN | 第一轮后Token<br/>第二轮后Token |

### 重要提示

1. **编码格式：** CSV 文件推荐使用 **UTF-8 with BOM** 或 **GBK** 编码
2. **多轮对话：** 使用 **换行符** 分隔多轮内容
3. **表头名称：** 支持以下变体：
   - `beforeBaseToken` 或 `before_base_token`
   - `afterBaseToken` 或 `after_base_token`

---

## 常见问题

### Q1: 单条测试和批量测试的区别是什么？

**A:** 
- **单条测试**：快速测试单个用例，适合调试和验证
- **批量测试**：一次性运行多个测试用例，适合回归测试和批量验证

### Q2: 为什么有些 Agent 类型不需要评估模式？

**A:** 
- **building** Agent 需要评估维度和模式，因为它是通用测试
- **dashboard/workflow/block/table/permission** Agent 是专用场景，不需要评估模式

### Q3: 如何处理多轮对话？

**A:** 
在输入框中，**每轮对话占一行**即可。例如：
```
第一轮用户查询
第二轮用户查询
第三轮用户查询
```

### Q4: CSV 文件打开乱码怎么办？

**A:** 
推荐使用以下编码格式保存 CSV 文件：
- **UTF-8 with BOM**（推荐）
- **GBK**（Windows 系统常用）

### Q5: 测试结果在哪里查看？

**A:** 
- **单条测试**：结果直接显示在页面下方的"评测结果"区域
- **批量测试**：结果显示在批量测试对话框的"结果"标签页中

### Q6: 支持哪些评估维度？

**A:** 
Building Agent 支持以下评估维度：
- table（表格）
- permission（权限）
- workflow（工作流）
- formula（公式）
- dashboard（仪表盘）

---

## 补充说明

### API 配置信息

- **API URL：** `https://sszy6ucc.fn-boe.bytedance.net/v1/judge`（统一使用）
- **API Key：** 在 UI 界面中配置和保存

### 响应结果说明

测试结果会显示以下信息：
- 请求是否成功
- 状态码
- 请求时间戳
- 请求 ID（用于追踪）
- 完整的响应 JSON
- 请求体

---

如有问题，请联系开发团队。

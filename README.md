# 飞书多维表格数据管理工具

一个基于 PyQt5 的图形界面工具，用于获取飞书（Lark）多维表格的完整数据，包括表结构、字段配置、记录内容、仪表盘、工作流、高级权限和表单配置等，同时集成了全面的 Building 机评功能。

## ✨ 功能特性

### 📊 五大核心模块
- **数据表**: 获取表结构、字段配置和记录内容
- **仪表盘**: 提取仪表盘配置快照
- **工作流**: 获取工作流配置信息
- **高级权限**: 提取角色和权限配置
- **表单**: 提取表单配置和字段信息

### 🏗️ Building 机评功能
- **支持全量 Agent**: table、dashboard、permission、workflow、block、formula、building
- **单条测试**: 可视化输入测试用例，快速验证
- **批量测试**: 从 CSV/Excel 批量读取用例，支持并发测试
- **多轮对话支持**: dashboard、permission、workflow、block 支持多轮对话格式

### 📝 生成标注列（v2.12 新增）
- **按模式匹配配置表**：支持 小白/Lite、Standard、Pro 三种模式，4 级匹配策略定位模板表
- **读取字段模板**：从模板表中读取完整的字段配置（字段名、类型、单选/多选的 options）
- **保留原始字段类型**：单选、多选字段的选项、颜色等配置会完整保留，而非退化为纯文本
- **一键追加到目标表**：将模板列追加到指定的飞书多维表格，自动跳过已存在的字段
- **多级回落机制**：复杂字段类型创建失败时自动回落，确保流程稳定

### 🔐 多种认证方式
- **Token 方式**（推荐，支持所有模块）
- **OAuth 2.0 授权**（一键浏览器授权）
- **Cookie 方式**（支持自动获取或手动输入）

### 📄 附加功能
- 内置文本对比工具，支持并排显示差异
- 所有结果可导出为 JSON 格式文件
- 窗口自动居中显示
- 现代化飞书风格界面设计
- 跨平台支持：Windows、macOS、Linux

## 📁 项目结构

```
base_mrtadata/
├── main.py                          # 程序主入口
├── icon.ico / icon.png              # 应用图标
├── build.bat                        # Windows 打包脚本
├── build.sh                         # macOS/Linux 打包脚本
├── requirements.txt                 # 依赖包列表
├── BUILDING_JUDGE_TUTORIAL.md       # Building 机评使用教程
├── config/                          # 配置模块
│   ├── __init__.py
│   ├── settings.py                  # 配置参数和 API Key 管理
│   └── user_config.json             # 用户配置（自动生成，不上传）
├── api/                             # API 接口模块
│   ├── __init__.py
│   ├── feishu_api.py                # 开放 API 接口（数据表、字段元数据提取）
│   ├── feishu_cookie_api.py         # Cookie 方式接口
│   ├── feishu_dashboard_api.py      # 仪表盘接口
│   ├── feishu_workflow_api.py       # 工作流接口
│   ├── feishu_permission_api.py     # 高级权限接口
│   └── feishu_form_api.py           # 表单接口
├── ui/                              # 用户界面模块
│   ├── __init__.py
│   ├── styles.py                    # 界面样式（飞书风格）
│   ├── main_window.py               # 主窗口（支持自动居中）
│   ├── table_panel.py               # 数据表面板
│   ├── simple_panel.py              # 通用面板（仪表盘、工作流、表单）
│   ├── permission_panel.py          # 高级权限面板
│   ├── result_panel.py              # 结果显示面板
│   ├── text_diff_dialog.py          # 文本对比对话框
│   ├── search_logic.py              # 搜索功能逻辑
│   ├── search_widget.py             # 搜索组件
│   └── building_ui/                 # Building 机评界面
│       ├── __init__.py
│       ├── building_judge_panel.py  # 机评主面板（含「生成标注列」按钮）
│       ├── annotation_column_dialog.py # 生成标注列对话框
│       ├── batch_judge_dialog.py    # 批量测试对话框（支持所有 agent）
│       ├── table_judge_panel.py     # 数据表机评面板
│       ├── dashboard_judge_panel.py # 仪表盘机评面板
│       ├── permission_judge_panel.py # 高级权限机评面板
│       ├── workflow_judge_panel.py  # 工作流机评面板
│       └── block_judge_panel.py     # Block 机评面板
├── workers/                         # 后台工作线程
│   ├── __init__.py
│   ├── oauth_worker.py              # OAuth 认证线程
│   ├── cookie_worker.py             # Cookie 获取线程（跨平台支持）
│   └── fetch_worker.py              # 数据获取线程
├── building_spec/                   # Building 机评核心逻辑
│   ├── batch_judge.py               # Building 和简单 agent 批量测试逻辑
│   ├── single_judge.py              # Building 和简单 agent 单条测试逻辑
│   ├── annotation_column_spec.py    # 生成标注列：配置表查找+字段模板+property 清理
│   ├── table_judge.py               # 数据表机评（单条+批量）
│   ├── dashboard_judge.py           # 仪表盘机评（单条+批量）
│   ├── permission_judge.py          # 高级权限机评（单条+批量）
│   ├── workflow_judge.py            # 工作流机评（单条+批量）
│   ├── block_judge.py               # Block 机评（单条+批量）
│   └── feishu_bitable_import.py     # 结果导入多维表格脚本
└── doc_base/                        # 飞书多维表格底层工具
    ├── __init__.py
    ├── doc_to_bitable_core.py       # 核心 API 封装（ensure_fields 支持字段类型+配置保留）
    └── feishu_bitable_import.py     # 数据导入工具
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Windows / macOS / Linux

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python main.py
```

## 📖 使用指南

### 1. 选择功能模块

左侧导航栏选择要使用的功能模块：
- 📊 数据表
- 📈 仪表盘  
- 🔄 工作流
- 🔐 高级权限
- 📝 表单
- 🏗️ Building机评（内置「生成标注列」按钮）

### 2. 配置认证

#### Token 方式（推荐）
1. 打开飞书开放平台 API 调试台
2. 获取 User Access Token
3. 粘贴到 Token 输入框中

#### OAuth 方式
1. 在飞书开放平台创建应用
2. 配置回调地址为 `http://localhost:3000`
3. 输入 App ID 和 App Secret
4. 点击"浏览器一键授权"进行 OAuth 认证

#### Cookie 方式
- **自动获取**: 点击"启动浏览器"，在打开的浏览器中登录飞书后点击"已登录"
- **手动输入**: 从浏览器开发者工具中复制 Cookie 并粘贴

### 3. 获取数据

#### 数据表
1. 输入飞书多维表格链接
2. （可选）勾选是否需要获取记录内容
3. 选择认证方式并配置
4. 点击"获取数据"

#### 仪表盘/工作流/表单
1. 输入对应链接
2. 使用 Cookie 方式认证
3. 点击对应的获取按钮

#### Building 机评
1. 配置 JUDGE_API_KEY（在机评界面中设置）
2. 选择 Agent 类型（table/dashboard/permission/workflow/block/formula/building）
3. 单条测试：直接在界面输入测试用例
4. 批量测试：点击"批量测试"按钮，选择 CSV/Excel 测试文件
5. 点击"开始测试"

#### 生成标注列（v2.12 新增）
**功能**：根据配置表（固定的飞书多维表格）中的字段模板，一键将标注列追加到你的目标多维表格。支持保留字段的原始类型和选项配置。

**操作步骤**：
1. 打开「Building 机评」面板，点击顶部的「📝 生成标注列」按钮
2. 选择数据模式：小白/Lite 模式 / Standard 模式 / Pro 模式（对应配置表中的不同模板表）
3. 输入认证信息：粘贴有效的 User Access Token
4. 输入目标表链接：粘贴要追加字段的目标飞书多维表格 URL（需包含 `?table=tbl...` 参数）
5. 点击「🔍 预览将追加的列」：查看从配置表模板中读取到的字段列表（字段名、类型、选项数）
6. 确认无误后点击「▶ 确认并追加列」：字段将被追加到目标表中，已存在的字段会自动跳过
7. 查看执行日志：确认新建了多少个字段，跳过了多少个已存在的字段

**配置表匹配逻辑**（4 级策略）：
1. 精确匹配数据表名称（如 "Pro 模式"）
2. 包含匹配（名称中包含关键词）
3. 英文关键字匹配（如 "pro"、"standard"、"lite"）
4. 兜底：如果配置表只有 1 张表，直接使用

**字段类型保留**：
- 文本（type=1）
- 数字（type=2）
- 单选（type=3）→ 保留选项名称和颜色
- 多选（type=4）→ 保留选项名称和颜色
- 人员（type=11）→ 保留关联表 ID
- 附件（type=17）
- 其他类型：创建失败时自动回落为文本类型，保证流程不中断

### 4. 文本对比功能

点击右上角的"📄 文本对比"按钮：
- 在左右两个编辑框中分别输入要对比的文本
- 点击"开始对比"查看差异
- 一致内容显示绿色背景，不一致内容显示红色背景
- 支持交换文本和清空功能

### 5. 导出结果

获取成功后，可点击"导出 JSON"按钮将结果保存到本地。

## 🏗️ Building 机评 Agent 说明

| Agent 类型 | 字段 1 | 字段 2 | 多轮对话 | Options 位置 |
|------------|--------|--------|----------|--------------|
| table | beforeBaseToken | baseToken | ❌ 否 | 顶层 |
| dashboard | beforeBaseToken | afterBaseToken | ✅ 是 | Case 内部 |
| permission | sourceBaseToken | baseToken | ✅ 是 | Case 内部 |
| workflow | beforeBaseToken | afterBaseToken | ✅ 是 | Case 内部 |
| block | beforeBaseToken | afterBaseToken | ✅ 是 | Case 内部 |
| formula | beforeBaseToken | afterBaseToken | ❌ 否 | 顶层 |
| building | beforeBaseToken | afterBaseToken | ❌ 否 | 顶层 |

## 🔧 打包成应用

### Windows 系统

```cmd
build.bat
```

### macOS / Linux 系统

```bash
chmod +x build.sh
./build.sh
```

打包完成后，可执行文件位于 `dist/` 目录下。

## 💡 常见问题

**Q: 获取失败提示权限不足？**
A: 请确保你的账号对该多维表格有访问权限，Token 或 OAuth 认证信息正确有效。

**Q: Cookie 方式提示找不到表？**
A: 请确保链接中包含 `table=tbl...` 参数，可以在浏览器中打开对应数据表后复制链接。

**Q: 数据表字段中引用了其他表的 ID？**
A: Token 和 OAuth 方式会自动将关联字段中的表 ID 和字段 ID 替换为对应的名称。

**Q: 仪表盘/工作流/高级权限提示没有设置？**
A: 这是正常现象，表示该多维表格没有配置对应的功能。

**Q: 文本对比时文字显示不全？**
A: 文本编辑框支持滚动查看所有内容，两侧内容会同步滚动。

**Q: macOS 上运行被阻止？**
A: 请在「系统设置 → 隐私与安全性」中允许运行。

**Q: 窗口没有居中显示？**
A: 请确保使用最新版本，窗口会自动居中显示。

**Q: 生成标注列功能如何使用？**
A: 在「Building 机评」面板中点击「📝 生成标注列」按钮，选择数据模式（小白/Lite/Standard/Pro），填写 Token 和目标表链接即可。配置表地址是固定的，由程序内部管理。

**Q: 生成标注列时字段类型会不会丢失？**
A: 不会。程序会读取模板表中字段的完整配置（包括单选/多选的选项、颜色、人员字段的关联表信息等），并在创建新字段时完整保留。如果某些特殊类型创建失败，会自动回落到文本类型，保证流程不中断。

**Q: 目标表中已有的字段会被覆盖吗？**
A: 不会。程序会先检查目标表中的现有字段，与模板字段名匹配的字段会被自动跳过，只追加目标表中不存在的字段。

## 🛠️ 技术栈

- **GUI 框架**: PyQt5
- **HTTP 请求**: requests
- **浏览器自动化**: Selenium + webdriver-manager
- **数据解析**: JSON, Base64, GZip, pandas (Excel 支持)
- **打包工具**: PyInstaller

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如果有问题或建议，欢迎通过飞书联系作者：[点击添加联系人](https://www.larkoffice.com/invitation/page/add_contact/?token=6e2ma113-ab71-48a6-a684-2c8bb2e38e32)

"""
飞书多维表格自动导入脚本
功能：从飞书文档读取评测数据，导入到多维表格

依赖：
  pip install lark-oapi requests

用法：
  1. 设置环境变量或直接在代码里填入 app_id / app_secret（见下方配置区）
  2. 设置 DOC_TOKEN 为机评文档的 token
  3. 运行 python script.py
"""

import json
import os
import time
import requests

# ============================================================
# 配置区
# ============================================================
# 使用用户身份（user_access_token）
# 获取方法：在飞书开放平台 API 调试台获取临时 token，或者走 OAuth2 流程
USER_ACCESS_TOKEN = "u-xxxxx"  # 在这里填入你的 user_access_token

DOC_TOKEN = "your_doc_token_here"  # 机评文档 token
TABLE_NAME = "building_evaluation"
# ============================================================


# ------------------------------------------------------------
# 飞书 Open API 基础调用
# ------------------------------------------------------------
BASE_URL = "https://open.feishu.cn/open-apis"

def get_tenant_access_token():
    """获取 tenant_access_token"""
    url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def api(method, path, token, json_body=None, params=None):
    """通用 API 请求"""
    url = f"{BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.request(method, url, headers=headers, json=json_body, params=params, timeout=30)
    try:
        data = resp.json()
    except Exception:
        data = None
    try:
        resp.raise_for_status()
    except Exception as e:
        print(f"API Error: {e}")
        if data:
            print(f"Response JSON: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"Response content: {resp.text}")
        raise
    if data is None:
        data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"API 请求失败 [{data.get('code')}]: {data.get('msg')} | path={path}")
    return data.get("data", {})


# ------------------------------------------------------------
# Step 1: 读取文档内容
# ------------------------------------------------------------
def fetch_doc(token_str, doc_token):
    """拉取飞书文档内容（Markdown 格式）"""
    # 先尝试旧版文档 API (doc/v2)
    try:
        path = f"/doc/v2/{doc_token}/raw_content"
        raw = api("GET", path, token_str)
        return raw.get("content", "")
    except Exception as e:
        print(f"旧版文档 API 失败: {e}，尝试新版文档 API...")
        # 新版文档（docx）使用 docx/v1 API
        path = f"/docx/v1/documents/{doc_token}/raw_content"
        raw = api("GET", path, token_str)
        return raw.get("content", "")


# ------------------------------------------------------------
# Step 2: 解析文档中的表格数据
# ------------------------------------------------------------
def parse_evaluation_table(markdown_text):
    """
    从机评文档中解析总览表格。
    文档结构：总览表格 → 各用例详细章节。
    新版返回的是每行一个单元格的纯文本格式。
    返回结构：
    [
        {
            "case_id": "SpecQuery_v0.7_001",
            "url": "https://...",
            "overall": "通过/不通过",
            "table_result": "通过/X分",
            "perm_result": "通过/不通过",
            "wf_result": "通过/X分",
            "formula_result": "通过/不通过",
            "dashboard_result": "通过/X分",
            "failure_reason": "..."
        },
        ...
    ]
    """
    import re

    records = []

    # 获取所有非空行
    lines = [line.strip() for line in markdown_text.split("\n") if line.strip()]

    # 找到总览开始的位置
    overview_start = -1
    for i, line in enumerate(lines):
        if line == "总览":
            overview_start = i
            break

    if overview_start == -1:
        return records

    # 表头是接下来8行：ID, 产物链接, 整体通过, Table 机评结果, Permission 机评结果, Workflow 机评结果, Formula 机评结果, Dashboard 机评结果
    # 跳过表头，从下一行开始解析数据，每8行一条记录，只取前20条
    data_start = overview_start + 9  # "总览"后1行空行，然后8行表头，再然后是数据
    for i in range(data_start, len(lines), 8):
        # 确保有足够的行
        if i + 7 >= len(lines):
            break
        case_id = lines[i]
        if not case_id.startswith("SpecQuery"):
            continue
        # 只取前20条记录
        if len(records) >= 20:
            break
        url_token = lines[i + 1]
        overall = lines[i + 2]
        table_result = lines[i + 3]
        perm_result = lines[i + 4]
        wf_result = lines[i + 5]
        formula_result = lines[i + 6]
        dashboard_result = lines[i + 7]

        # 构造完整 URL，假设链接是 https://feishu.cn/docx/{token}
        url = f"https://feishu.cn/docx/{url_token}"

        records.append({
            "case_id": case_id,
            "url": url,
            "overall": overall,
            "table_result": table_result,
            "perm_result": perm_result,
            "wf_result": wf_result,
            "formula_result": formula_result,
            "dashboard_result": dashboard_result,
            "failure_reason": "",  # 从详细章节补充
        })

    return records


def enrich_failure_reasons(records, markdown_text):
    """
    补充失败原因：从每个用例的详细章节中提取
    新格式：每个用例章节有 "SpecQuery_v0.7_001 — ----{轮次1}----" 开始
    然后下面有 "X维度：不通过（Y fail / Z项）"，接着是 "失败项"，然后是具体失败项
    """
    import re

    # 获取所有行
    lines = markdown_text.split("\n")
    
    # 遍历每个用例
    for rec in records:
        case_id = rec["case_id"]
        # 找到该用例章节的起始位置
        case_start = -1
        for i, line in enumerate(lines):
            if f"{case_id} — ----{{" in line:
                case_start = i
                break
        if case_start == -1:
            continue
        
        # 找到下一个用例的起始位置（或者文档结束）
        next_case_start = len(lines)
        for i in range(case_start + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith("SpecQuery_v0.7_") and "— ----{" in line:
                next_case_start = i
                break
        
        # 提取该用例的章节内容
        section_lines = lines[case_start:next_case_start]
        
        failure_reasons = []
        current_dimension = None
        state = "search_dimension"  # search_dimension, wait_reason_header, wait_num, wait_item, wait_reason
        current_fail_item_name = None
        
        for line in section_lines:
            stripped_line = line.strip()
            
            # 不管当前是什么状态，如果遇到新的维度行，都回到search_dimension
            if "维度：不通过" in stripped_line:
                dim_match = re.search(r'(\w+)\s*维度：不通过', stripped_line)
                if dim_match:
                    current_dimension = dim_match.group(1)
                    state = "wait_reason_header"
                continue
            
            elif state == "wait_reason_header":
                if stripped_line == "失败项":
                    state = "wait_num"
                continue
            
            elif state == "wait_num":
                if stripped_line.isdigit():
                    state = "wait_item"
                elif not stripped_line or stripped_line == "#" or stripped_line == "原因":
                    continue
                else:
                    state = "search_dimension"
                continue
            
            elif state == "wait_item":
                if stripped_line and not stripped_line.isdigit() and stripped_line != "#" and stripped_line != "原因":
                    current_fail_item_name = stripped_line
                    state = "wait_reason"
                continue
            
            elif state == "wait_reason":
                if stripped_line and not stripped_line.isdigit() and stripped_line != "#" and stripped_line != "原因":
                    failure_reasons.append(f"{current_dimension}维度：{current_fail_item_name} - {stripped_line}")
                    state = "wait_num"
                continue
        
        # 更新记录的失败原因
        rec["failure_reason"] = "\n".join(failure_reasons) if failure_reasons else ""
    
    return records


# ------------------------------------------------------------
# Step 3: 创建多维表格
# ------------------------------------------------------------
def create_bitable(token_str, name, folder_token=None):
    """创建多维表格，使用 bitable v1 API 来创建"""
    path = "/bitable/v1/apps"
    body = {"name": name}
    if folder_token:
        body["folder_token"] = folder_token
    data = api("POST", path, token_str, json_body=body)
    app_token = data.get("app", {}).get("app_token", "")
    default_table_id = data.get("app", {}).get("default_table_id", "")
    app_url = data.get("app", {}).get("url", "")
    print(f"[创建] 多维表格: {name} | app_token: {app_token}")
    print(f"[创建] 表格 URL: {app_url}")
    return app_token, default_table_id, app_url


# ------------------------------------------------------------
# Step 4: 创建数据表（并定义字段）
# ------------------------------------------------------------
def create_table(token_str, app_token, table_name, fields):
    """
    创建数据表，同时定义字段。
    fields: [{"field_name": "...", "type": 1, ...}, ...]
    字段类型对应：1=文本, 2=数字, 3=单选, 4=多选, 5=日期, 7=复选框, 11=人员, 15=超链接
    """
    body = {
        "table": {
            "name": table_name,
            "fields": fields,
        }
    }
    data = api("POST", f"/bitable/v1/apps/{app_token}/tables", token_str, json_body=body)
    table_id = data["table_id"]
    print(f"[创建] 数据表: {table_name} | table_id: {table_id}")
    return table_id


# ------------------------------------------------------------
# Step 5: 批量写入记录
# ------------------------------------------------------------
def batch_create_records(token_str, app_token, table_id, records):
    """
    批量写入记录（最多 500 条/次）
    fields 格式参考飞书多维表格 API 规范
    """
    # 分批写入（这里数据量小，直接一次）
    BATCH_SIZE = 500
    total = len(records)
    for i in range(0, total, BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        body = {"records": [{"fields": r} for r in batch]}
        data = api("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create", token_str, json_body=body)
        created = len(data.get("records", []))
        print(f"[写入] 第 {i//BATCH_SIZE + 1} 批，写入 {created} 条记录")


# ------------------------------------------------------------
# 主流程
# ------------------------------------------------------------
def main():
    print("=" * 50)
    print("飞书多维表格导入脚本")
    print("=" * 50)

    # 1. 获取 token
    token = USER_ACCESS_TOKEN
    if token == "u-xxxxx":
        raise ValueError("请先在配置区填入你的 USER_ACCESS_TOKEN！")
    print("\n[1/5] 使用配置的 USER_ACCESS_TOKEN")
    print(f"    token 长度: {len(token)}")

    # 2. 读取文档
    print("\n[2/5] 读取文档...")
    doc_text = fetch_doc(token, DOC_TOKEN)
    print(f"    文档拉取成功（字符数: {len(doc_text)}）")

    # 3. 解析数据
    print("\n[3/5] 解析评测数据...")
    records_raw = parse_evaluation_table(doc_text)
    records = enrich_failure_reasons(records_raw, doc_text)
    print(f"    解析到 {len(records)} 条用例记录")

    # 4. 创建多维表格和数据表
    print("\n[4/5] 创建多维表格...")
    app_token, default_table_id, app_url = create_bitable(token, TABLE_NAME)

    # 定义字段
    FIELDS = [
        {"field_name": "用例ID", "type": 1},                          # 文本
        {"field_name": "链接", "type": 15},                           # 超链接
        {"field_name": "整体", "type": 3},                           # 单选
        {"field_name": "Table", "type": 1},                          # 文本
        {"field_name": "Permission", "type": 1},                      # 文本
        {"field_name": "Workflow", "type": 1},                        # 文本
        {"field_name": "Formula", "type": 1},                         # 文本
        {"field_name": "Dashboard", "type": 1},                       # 文本
        {"field_name": "失败原因", "type": 1},                        # 文本
    ]
    table_id = create_table(token, app_token, "评测结果总览", FIELDS)

    # 5. 批量写入记录
    print("\n[5/5] 写入记录...")

    # 构造成飞书 API 格式
    bitable_records = []
    for rec in records:
        # 超链接字段特殊格式
        url_display = rec["url"].split("/")[-1]  # 取 token 作为显示名
        record = {
            "用例ID": rec["case_id"],
            "链接": {"link": rec["url"], "text": url_display},
            "整体": rec["overall"],  # 单选字段值
            "Table": rec["table_result"],
            "Permission": rec["perm_result"],
            "Workflow": rec["wf_result"],
            "Formula": rec["formula_result"],
            "Dashboard": rec["dashboard_result"],
            "失败原因": rec["failure_reason"],
        }
        bitable_records.append(record)

    batch_create_records(token, app_token, table_id, bitable_records)

    print("\n" + "=" * 50)
    print(f"完成！打开链接查看：{app_url}")
    print("=" * 50)


if __name__ == "__main__":
    main()

"""
飞书云文档 → 多维表格 转换核心逻辑

关键流程:
  1. 读云文档 blocks (多路径 fallback)
  2. 打印前几个 block 的原始 JSON 结构（调试用）
  3. 优先识别文档中的表格 block → 解析为 field_names + records
  4. 核对目标数据表字段；缺失字段自动补建为「文本」类型
  5. 分批写入（调用方先预览解析结果，用户确认后再写）

API 域名映射:
  - *.larkoffice.com / *.larksuite.com  →  https://open.larksuite.com
  - *.feishu.cn                          →  https://open.feishu.cn
"""

import os
import sys
import re
import json
import datetime
import requests

# ------------------------------------------------------------
# 字段名映射：云文档解析出的原始列名 → 多维表格中使用的最终字段名
# 想改列名/加字段，只改这里即可。
# ------------------------------------------------------------
FIELD_NAME_MAP = {
    "产物链接": "basetoken",
    # 示例："原列名": "新列名",
}

# 失败原因的最终字段名（在正文中提取时使用）
FAILURE_REASON_FIELD_NAME = "失败原因"
from urllib.parse import urlparse, parse_qs


# ============================================================
# 链接 / Token 解析 & API 域名映射
# ============================================================


def _detect_api_base(url_or_token):
    if not url_or_token:
        return "https://open.larksuite.com"
    s = str(url_or_token).lower()
    if "feishu.cn" in s:
        return "https://open.feishu.cn"
    if "larkoffice.com" in s or "larksuite.com" in s:
        return "https://open.larksuite.com"
    return "https://open.larksuite.com"


def extract_token_from_url(url_or_token):
    if not url_or_token:
        return None
    s = url_or_token.strip()
    if s.startswith("http://") or s.startswith("https://"):
        parsed = urlparse(s)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) >= 2 and parts[0] in ("docx", "doc", "wiki", "base"):
            return parts[1]
        return None
    return s


def extract_bitable_info_from_url(url_or_token):
    """解析 (api_base, app_token, table_id)"""
    if not url_or_token:
        return None, None, None
    s = url_or_token.strip()
    api_base = _detect_api_base(s)
    app_token = None
    table_id = None
    if s.startswith("http://") or s.startswith("https://"):
        parsed = urlparse(s)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(parts) >= 2 and parts[0] == "base":
            app_token = parts[1]
        qs = parse_qs(parsed.query)
        if "table" in qs and qs["table"]:
            table_id = qs["table"][0]
    else:
        app_token = s
    return api_base, app_token, table_id


# ============================================================
# HTTP
# ============================================================


def _headers(user_token):
    return {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }


def _parse_json_safe(text, url_for_debug):
    text = (text or "").strip()
    if not text:
        raise RuntimeError(f"接口 {url_for_debug} 返回空响应")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        snippet = text[:800]
        raise RuntimeError(
            f"接口 {url_for_debug} 响应不是合法 JSON ({e})\n"
            f"HTTP 响应前 800 字符:\n{snippet}"
        )


def _get(url, headers, params=None):
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    data = _parse_json_safe(resp.text, url)
    if data.get("code") not in (0, None):
        raise RuntimeError(
            f"GET {url} 失败 (HTTP {resp.status_code}): "
            f"code={data.get('code')}, msg={data.get('msg')}, "
            f"data={data.get('data')}"
        )
    return data.get("data", {})


def _post(url, headers, json_body=None):
    resp = requests.post(url, headers=headers, json=json_body, timeout=30)
    data = _parse_json_safe(resp.text, url)
    if data.get("code") not in (0, None):
        raise RuntimeError(
            f"POST {url} 失败 (HTTP {resp.status_code}): "
            f"code={data.get('code')}, msg={data.get('msg')}, "
            f"data={data.get('data')}"
        )
    return data.get("data", {})


def _get_all_pages(url, headers, item_key="items", params=None, page_size=100, log_fn=None):
    params = dict(params or {})
    params["page_size"] = page_size
    page_token = None
    all_items = []
    page = 0
    while True:
        page += 1
        if page_token:
            params["page_token"] = page_token
        data = _get(url, headers, params=params)
        items = data.get(item_key) or data.get("items") or []
        has_more = data.get("has_more", False)
        next_token = data.get("page_token") or data.get("next_page_token")
        all_items.extend(items)
        if log_fn:
            log_fn(f"  第 {page} 页: {len(items)} 条, 累计 {len(all_items)} 条, has_more={has_more}")
        if not has_more or not next_token:
            break
        page_token = next_token
        if page >= 100:
            if log_fn:
                log_fn("  ⚠️ 达到 100 页上限，停止翻页")
            break
    return all_items


# ============================================================
# 云文档 blocks 读取（多路径 + 原始结构日志）
# ============================================================


def _fetch_doc_blocks(api_base, user_token, doc_token, log_fn=None):
    log = log_fn or (lambda msg: None)

    candidates = [
        ("docx documents blocks",
         f"{api_base}/open-apis/docx/v1/documents/{doc_token}/blocks"),
        ("docx files blocks",
         f"{api_base}/open-apis/docx/v1/files/{doc_token}/blocks"),
        ("drive export blocks",
         f"{api_base}/open-apis/drive/explorer/v2/export/{doc_token}/blocks"),
        ("doc v2 content (旧版)",
         f"{api_base}/open-apis/doc/v2/{doc_token}/content"),
    ]

    headers = _headers(user_token)
    last_error = None

    for name, url in candidates:
        log(f"  尝试路径 [{name}]: {url}")
        try:
            all_blocks = _get_all_pages(url, headers, item_key="items",
                                         page_size=100, log_fn=log)
            if all_blocks:
                log(f"  ✅ 路径 [{name}] 成功读取 {len(all_blocks)} 个 block")
                # 打印前 5 个 block 的精简结构（便于调试）
                for i, blk in enumerate(all_blocks[:5]):
                    if isinstance(blk, dict):
                        keys_str = ", ".join(k for k in list(blk.keys())[:12])
                        log(f"    block[{i}] keys: {keys_str}")
                        bt = blk.get("block_type") or blk.get("type")
                        log(f"    block[{i}] block_type/type: {bt}")
                        # 打印前 600 个字符的 JSON（截断长内容）
                        raw = json.dumps(blk, ensure_ascii=False, indent=2)
                        if len(raw) > 600:
                            raw = raw[:600] + "\n...(已截断)"
                        log(f"    block[{i}] full JSON:\n{raw}")
                    else:
                        log(f"    block[{i}] type={type(blk).__name__}: {str(blk)[:200]}")
                return all_blocks
            else:
                log(f"  ⚠️ 路径 [{name}] 成功但返回 0 条，继续尝试...")
        except Exception as e:
            log(f"  ❌ 路径 [{name}] 失败: {e}")
            last_error = e
            continue

    raise RuntimeError(
        "所有云文档 blocks 接口路径均失败。\n"
        "可能原因：\n"
        "  1) User Access Token 没有云文档读取权限（应用需开通 云文档/文档 相关权限域）\n"
        "  2) doc_token 不正确或文档已被删除\n"
        "  3) 企业 API 域名与实际环境不符（当前使用 " + api_base + ")\n"
        "\n最后一次失败详情: " + str(last_error or "未知")
    )


def _apply_field_name_map(field_names, records):
    """按 FIELD_NAME_MAP 将原始列名替换为最终字段名，并同步更新每条记录的 dict key。"""
    if not field_names or not FIELD_NAME_MAP:
        return field_names, records

    new_field_names = [FIELD_NAME_MAP.get(fn, fn) for fn in field_names]

    # 建立 {原 key: 新 key} 的反向映射，用于重写每条记录的 dict
    new_records = []
    for rec in records:
        new_rec = {}
        for fn in field_names:
            new_key = FIELD_NAME_MAP.get(fn, fn)
            val = rec.get(fn, "")
            # 只对看起来像评分的字段进行转换
            if isinstance(val, str) and _is_score_field(fn):
                val = _convert_score_to_pass(val)
            new_rec[new_key] = val
        new_records.append(new_rec)

    return new_field_names, new_records


def _is_score_field(field_name):
    score_keywords = ["整体通过", "Table 机评结果", "Permission 机评结果", "Workflow 机评结果", "Formula 机评结果", "Dashboard 机评结果"]
    fn = str(field_name).lower()
    for kw in score_keywords:
        if kw.lower() in fn:
            return True
    return False


def _convert_score_to_pass(value):
    """
    值转换：把分数格式转换为可读性更好的状态。
    
    规则：
      - 已经是 "通过" 或 "不通过" 文本 → 保持原样
      - "10" 或 "10.0" → "通过"
      - "10 (xx/xx)" → "通过"（如 "10 (23/23)"）
      - 其他数字分数（没到10分的）→ "不通过"
      - 非分数格式的文本 → 保持原样
    """
    if not isinstance(value, str):
        return value
    
    v = value.strip()
    
    # 已经是通过/不通过文本，保持原样
    if "通过" in v:
        return v
    if "不通过" in v:
        return v
    
    # 匹配 "10" 或 "10.0"
    if v == "10" or v == "10.0":
        return "通过"
    # 匹配 "10 (xx/xx)" 或 "10(xx/xx)" 格式
    if re.match(r'^\s*10\.?0?\s*\(\d+/\d+\)\s*$', v):
        return "通过"
    # 匹配其他数字分数格式（如 "9 (20/23)"、"8.7" 等）→ 不通过
    if re.match(r'^\s*\d+(\.\d+)?\s*(\(\d+/\d+\))?\s*$', v):
        return "不通过"
    # 非分数格式文本，保持原样
    return value


def _fetch_raw_content(api_base, user_token, doc_token, log_fn=None):
    """
    拉取云文档的 raw_content（Markdown/纯文本形式）。
    用于在表格之外的正文段落中提取「失败原因」等信息。
    """
    log = log_fn or (lambda msg: None)
    headers = _headers(user_token)

    candidates = [
        ("docx documents raw_content", f"/docx/v1/documents/{doc_token}/raw_content"),
        ("docx files raw_content", f"/docx/v1/files/{doc_token}/raw_content"),
        ("doc v2 raw_content", f"/doc/v2/{doc_token}/raw_content"),
    ]

    for label, path in candidates:
        url = f"{api_base}/open-apis{path}"
        try:
            data = _get(url, headers)
            content = None
            if isinstance(data, dict):
                content = data.get("content")
                if content is None and isinstance(data.get("data"), dict):
                    content = data["data"].get("content")
            if isinstance(content, str) and len(content) > 50:
                log(f"  [raw_content] 从 [{label}] 拉取成功，{len(content)} 字符")
                return content
        except Exception as e:
            log(f"  [raw_content] [{label}] 尝试失败: {e}")
            continue

    log("  [raw_content] 未能拉取到有效 raw_content（不影响表格解析，"
        "但将无法从正文提取失败原因）")
    return ""


def _extract_failure_reasons_from_raw_content(raw_content, records, log_fn=None):
    """
    从 Markdown 正文中提取每个用例的「失败原因」，并合并到 records。

    返回 (new_field_names, merged_records)：
      - new_field_names = 原有字段名 + 末尾追加「失败原因」
      - merged_records = 每条记录都新增「失败原因」字段（空字符串或多行文本）

    逻辑：
      1) 先识别 key_field：找首列或值以 SpecQuery_ 开头的字段
      2) 在全文中定位包含 case_id 的行，进入该用例上下文
      3) 状态机扫描：X维度：不通过 → 失败项 → 编号 → 条目 → 原因
    """
    log = log_fn or (lambda msg: None)
    if not raw_content or not records:
        log("  [失败原因] 无 raw_content 或无记录，跳过")
        if records:
            field_names = list(records[0].keys())
            merged = [dict(r) for r in records]
            for r in merged:
                r[FAILURE_REASON_FIELD_NAME] = r.get(FAILURE_REASON_FIELD_NAME, "")
            if FAILURE_REASON_FIELD_NAME not in field_names:
                field_names.append(FAILURE_REASON_FIELD_NAME)
            return field_names, merged
        return [], []

    # Step 1: 识别 key_field（哪一列是用例 ID）
    key_field = None
    first_rec = records[0]
    for fn, val in first_rec.items():
        if isinstance(val, str) and val.startswith("SpecQuery_"):
            key_field = fn
            break
    if key_field is None:
        for fn, val in first_rec.items():
            if isinstance(val, str) and val.strip():
                key_field = fn
                break
    if key_field is None:
        log("  [失败原因] 无法识别 key_field，跳过失败原因提取")
        field_names = list(first_rec.keys())
        merged = [dict(r) for r in records]
        for r in merged:
            r[FAILURE_REASON_FIELD_NAME] = r.get(FAILURE_REASON_FIELD_NAME, "")
        if FAILURE_REASON_FIELD_NAME not in field_names:
            field_names.append(FAILURE_REASON_FIELD_NAME)
        return field_names, merged

    log(f"  [失败原因] 使用 key_field={key_field}")

    # Step 2: 收集所有 case_id
    case_ids = []
    for rec in records:
        cid = str(rec.get(key_field, "")).strip()
        if cid:
            case_ids.append(cid)

    # 建立 {case_id: [失败原因行...]}
    case_to_reasons = {cid: [] for cid in case_ids}

    # Step 3: 状态机扫描正文
    lines = raw_content.split("\n")

    current_case = None
    current_dimension = None
    current_fail_item_name = None
    state = "search_dimension"  # search_dimension / wait_reason_header / wait_num / wait_item / wait_reason

    for line in lines:
        stripped = line.strip()

        # 切换到某个用例的上下文：当前行包含某 case_id
        for cid in case_ids:
            if cid and cid in stripped:
                if current_case != cid:
                    current_case = cid
                    current_dimension = None
                    current_fail_item_name = None
                    state = "search_dimension"
                break

        if current_case is None:
            continue

        # 新的维度行：格式如「Table 维度：不通过（1 fail / 3项）」
        dim_match = re.search(r'(\w+)\s*维度：不通过', stripped)
        if dim_match:
            current_dimension = dim_match.group(1)
            state = "wait_reason_header"
            continue

        if state == "wait_reason_header":
            if stripped == "失败项":
                state = "wait_num"
            continue

        elif state == "wait_num":
            if stripped.isdigit():
                state = "wait_item"
            elif not stripped or stripped == "#" or stripped == "原因":
                continue
            else:
                state = "search_dimension"
            continue

        elif state == "wait_item":
            if stripped and not stripped.isdigit() and stripped != "#" and stripped != "原因":
                current_fail_item_name = stripped
                state = "wait_reason"
            continue

        elif state == "wait_reason":
            if stripped and not stripped.isdigit() and stripped != "#" and stripped != "原因":
                reason_line = f"{current_dimension}维度：{current_fail_item_name} - {stripped}"
                case_to_reasons[current_case].append(reason_line)
                state = "wait_num"
            continue

    # Step 4: 合并到 records；更新字段名
    field_names = list(first_rec.keys())
    failure_field = FAILURE_REASON_FIELD_NAME
    if failure_field not in field_names:
        field_names.append(failure_field)

    merged_records = []
    for rec in records:
        cid = str(rec.get(key_field, "")).strip()
        new_rec = dict(rec)
        reasons = case_to_reasons.get(cid, [])
        new_rec[failure_field] = "\n".join(reasons) if reasons else ""
        merged_records.append(new_rec)

    non_empty = sum(1 for r in merged_records if r.get(failure_field))
    log(f"  [失败原因] 共 {len(merged_records)} 条记录，{non_empty} 条有失败原因")
    for i, rec in enumerate(merged_records[:5]):
        r = rec.get(failure_field, "")
        snippet = r[:80] + ("..." if len(r) > 80 else "")
        log(f"    记录 {i+1} 失败原因: |{snippet}|")

    return field_names, merged_records


# ============================================================
# blocks → 结构化数据 解析（新版：更健壮）
# ============================================================


def _iter_block_text_elements(elements):
    """从 paragraph.elements 列表里拼出纯文本。"""
    if not isinstance(elements, list):
        return ""
    parts = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        tr = el.get("text_run")
        if isinstance(tr, dict) and isinstance(tr.get("content"), str):
            parts.append(tr["content"])
            continue
        if isinstance(el.get("content"), str):
            parts.append(el["content"])
    return "".join(parts)


def _block_text(blk):
    """从一个 block（段落/文本）提取纯文本。

    飞书 docx 的真实结构：
      {"block_type": 2, "text": {"elements": [{"text_run": {"content": "..."}}]}}
    """
    if not isinstance(blk, dict):
        return ""

    # 1) 最常见：{"text": {"elements": [{"text_run": ...}]}}
    text_obj = blk.get("text")
    if isinstance(text_obj, dict):
        elements = text_obj.get("elements") or []
        txt = _iter_block_text_elements(elements)
        if txt:
            return txt.strip()

    # 2) paragraph.elements（兼容其他格式）
    paragraph = blk.get("paragraph")
    if isinstance(paragraph, dict):
        txt = _iter_block_text_elements(paragraph.get("elements") or [])
        if txt:
            return txt.strip()

    # 3) heading
    for hk in ("heading1", "heading2", "heading3", "heading4", "heading5", "heading6",
               "heading_1", "heading_2", "heading_3", "heading_4", "heading_5", "heading_6"):
        h = blk.get(hk)
        if isinstance(h, dict):
            txt = _iter_block_text_elements(h.get("elements") or [])
            if txt:
                return txt.strip()

    # 4) bullet / quote / todo / callout / code ...
    for w in ("bullet", "quote", "todo", "callout", "code", "equation",
              "text", "tip", "note", "warning"):
        obj = blk.get(w)
        if isinstance(obj, dict):
            txt = _iter_block_text_elements(obj.get("elements") or [])
            if txt:
                return txt.strip()

    # 5) text 字段是字符串
    if isinstance(blk.get("text"), str) and blk["text"].strip():
        return blk["text"].strip()

    # 6) 直接 content
    if isinstance(blk.get("content"), str) and blk["content"].strip():
        return blk["content"].strip()

    return ""


def _cell_text_from_block(cell_id, block_map):
    """
    从 cell block_id 解析出文本内容。
    结构：
      cell_block (block_type=32) -> children[0] 是文本 block (block_type=2)
    """
    if not cell_id or cell_id not in block_map:
        return ""
    cell_blk = block_map[cell_id]
    if not isinstance(cell_blk, dict):
        return ""
    # 先看 cell 自己的 text（有的 cell 直接带 text）
    direct = _block_text(cell_blk)
    if direct:
        return direct
    # 再看 cell 的 children（通常是一个 paragraph 文本 block）
    cell_children = cell_blk.get("children") or []
    if isinstance(cell_children, list) and cell_children:
        for inner_id in cell_children:
            inner_blk = block_map.get(inner_id)
            if isinstance(inner_blk, dict):
                t = _block_text(inner_blk)
                if t:
                    return t
    return ""


def _parse_table_block_hierarchical(blk, block_map, log_fn=None):
    """
    解析飞书 docx 的表格 block。

    真实结构（从日志中验证）:
      block_type = 31                  <- 表格
      table.cells = [cell_id_1, cell_id_2, ...]  <- 一维列表，不是二维数组
      table.property.column_size = N   <- 每行有 N 个 cell

    每个 cell_id 指向 block_type=32 的单元格 block，
    单元格 block 的 children[0] 是 block_type=2 的文本 block。
    """
    log = log_fn or (lambda msg: None)
    if not isinstance(blk, dict):
        return None

    block_id = blk.get("block_id", "?")
    table_meta = blk.get("table") if isinstance(blk.get("table"), dict) else None

    if not table_meta:
        return None

    cells = table_meta.get("cells") or []
    if not isinstance(cells, list) or not cells:
        return None

    property_obj = table_meta.get("property") if isinstance(table_meta.get("property"), dict) else {}
    column_size = property_obj.get("column_size") or property_obj.get("column_width")
    if isinstance(column_size, list):
        column_size = len(column_size)

    # 兼容：有些环境把 cells 做成了二维数组 [[cell_id, cell_id, ...], [...]]
    if isinstance(cells[0], list):
        rows = []
        for row in cells:
            row_vals = []
            for c in row:
                if isinstance(c, str):
                    row_vals.append(_cell_text_from_block(c, block_map))
                elif isinstance(c, dict):
                    row_vals.append(_block_text(c))
                else:
                    row_vals.append(str(c))
            rows.append(row_vals)
        if rows and len(rows) >= 2:
            return rows
        return None

    # 列数诊断
    if not isinstance(column_size, int) or column_size <= 0:
        log(f"    [table] block_id={block_id} 未找到 column_size，cells={len(cells)}")
        return None

    total_cells = len(cells)
    expected_rows = total_cells // column_size
    log(f"    [table] block_id={block_id} column_size={column_size}, cells={total_cells} → 约 {expected_rows} 行")

    # 按列数把扁平 cells 切分成行
    rows = []
    for r in range(expected_rows):
        start = r * column_size
        end = start + column_size
        row_cells = cells[start:end]
        row_vals = []
        for cid in row_cells:
            row_vals.append(_cell_text_from_block(cid, block_map))
        rows.append(row_vals)

    if len(rows) >= 2:
        return rows
    return None


def _detect_table_blocks(all_blocks, log_fn=None):
    """从扁平 block 列表中识别表格块。返回 list[二维字符串数组]。

    先建 block_id -> block 的映射，然后按层级解析。
    """
    log = log_fn or (lambda msg: None)
    tables = []

    # 建 block_id -> block 映射
    block_map = {}
    for blk in all_blocks:
        if isinstance(blk, dict) and isinstance(blk.get("block_id"), str):
            block_map[blk["block_id"]] = blk
    log(f"  建立 block_id 映射: {len(block_map)} 个 block")

    # 查找表格（block_type == 8 或 table 字段非空）
    table_count = 0
    for idx, blk in enumerate(all_blocks):
        if not isinstance(blk, dict):
            continue
        block_type = blk.get("block_type") or blk.get("type")

        is_table = False
        if block_type == 31:
            is_table = True
        elif block_type == 8:
            is_table = True
        elif "table" in blk and isinstance(blk["table"], dict):
            is_table = True

        if not is_table:
            continue

        # 先尝试层级解析
        rows = _parse_table_block_hierarchical(blk, block_map, log_fn=log)
        if rows and len(rows) >= 2:
            log(f"  ✅ block[{idx}] (block_id={blk.get('block_id')}) 解析到表格："
                f"{len(rows)} 行 x {len(rows[0])} 列")
            # 打印前 3 行
            for r in rows[:3]:
                log(f"    行: {r}")
            tables.append(rows)
            table_count += 1
            continue

        # 再尝试其他结构（cells 二维数组 / rows）
        rows = _parse_table_block_flat(blk)
        if rows and len(rows) >= 2:
            log(f"  ✅ block[{idx}] 表格（扁平结构）{len(rows)} 行 x {len(rows[0])} 列")
            for r in rows[:3]:
                log(f"    行: {r}")
            tables.append(rows)
            table_count += 1
            continue

        # 解析失败时，把这个块的结构打到日志里（便于调试）
        raw = json.dumps(blk, ensure_ascii=False, indent=2)
        if len(raw) > 2000:
            raw = raw[:2000] + "\n...(已截断，共 " + str(len(json.dumps(blk, ensure_ascii=False))) + " 字符)"
        log(f"  ⚠️  block[{idx}] 疑似表格但解析失败，结构:\n{raw}")

    log(f"  共识别到 {table_count} 个有效表格块")
    return tables


def _parse_table_block_flat(tbl_obj):
    """解析表格 block，兼容 cells 二维数组 / rows 结构。"""
    if not isinstance(tbl_obj, dict):
        return None

    # 结构 A：cells 二维数组，每个 cell 是 dict
    tbl_inner = tbl_obj.get("table") if isinstance(tbl_obj.get("table"), dict) else tbl_obj
    cells = tbl_inner.get("cells") or tbl_inner.get("table_cells")
    if isinstance(cells, list) and cells and isinstance(cells[0], list):
        rows_str = []
        for row in cells:
            row_vals = []
            for cell in row:
                val = ""
                if isinstance(cell, str):
                    val = cell
                elif isinstance(cell, dict):
                    content = cell.get("content")
                    if isinstance(content, list) and content:
                        cell_txt_parts = []
                        for para in content:
                            if isinstance(para, dict):
                                elements = para.get("elements")
                                if isinstance(elements, list):
                                    cell_txt_parts.append(_iter_block_text_elements(elements))
                                elif isinstance(para.get("text"), str):
                                    cell_txt_parts.append(para["text"])
                        val = " ".join(cell_txt_parts)
                    elif isinstance(content, str):
                        val = content
                    elif isinstance(cell.get("text"), str):
                        val = cell["text"]
                row_vals.append(str(val).strip())
            rows_str.append(row_vals)
        if rows_str and any(any(c for c in r) for r in rows_str):
            return rows_str

    # 结构 B：rows -> cells
    rows = tbl_inner.get("rows") or tbl_inner.get("table_rows")
    if isinstance(rows, list) and rows:
        parsed = []
        for r in rows:
            if isinstance(r, dict):
                cells_r = r.get("cells") or []
                row_vals = []
                for cell in cells_r:
                    val = ""
                    if isinstance(cell, dict):
                        content = cell.get("content")
                        if isinstance(content, list):
                            parts = []
                            for p in content:
                                if isinstance(p, dict):
                                    elements = p.get("elements")
                                    if isinstance(elements, list):
                                        parts.append(_iter_block_text_elements(elements))
                            val = " ".join(parts)
                        elif isinstance(content, str):
                            val = content
                    elif isinstance(cell, str):
                        val = cell
                    row_vals.append(str(val).strip())
                parsed.append(row_vals)
        if parsed:
            return parsed

    return None


def _detect_columns_from_text(text_lines):
    """Tab/多空格分隔的文本兜底解析。"""
    if len(text_lines) < 2:
        return None
    tab_counts = [line.count("\t") for line in text_lines]
    if tab_counts and tab_counts[0] >= 1 and len(set(tab_counts)) == 1:
        sep = "\t"
    else:
        sep = None

    field_names = []
    records = []
    for i, line in enumerate(text_lines):
        if sep:
            cols = [c.strip() for c in line.split(sep)]
        else:
            cols = [c.strip() for c in re.split(r"\s{2,}", line)]
        if i == 0:
            field_names = [c or f"列{j+1}" for j, c in enumerate(cols)]
        else:
            rec = {field_names[j]: (cols[j] if j < len(cols) else "")
                   for j in range(len(field_names))}
            records.append(rec)
    if field_names and records:
        return field_names, records
    return None


def parse_doc_as_records(api_base, user_token, doc_token, log_fn=None):
    """**对外主解析函数**。返回 (field_names, records)。

    策略顺序：
      1) 识别表格 block → 使用第 1 张表格的内容
      2) 兜底：按 Tab 分隔的文本解析
    """
    log = log_fn or (lambda msg: None)

    log(f"读取云文档 blocks（API: {api_base}, doc_token: {doc_token}）")
    all_blocks = _fetch_doc_blocks(api_base, user_token, doc_token, log_fn=log)
    log(f"共读取 {len(all_blocks)} 个 block")

    # --- 策略 1：表格 ---
    log("--- 开始识别表格 block ---")
    tables = _detect_table_blocks(all_blocks, log_fn=log)
    if tables:
        log(f"识别到 {len(tables)} 张表格，默认使用第 1 张")
        rows = tables[0]
        header = [str(c).strip() for c in rows[0]]

        # 去掉空列 + 列名去重
        keep_idx = [j for j, h in enumerate(header) if h]
        field_names = []
        seen = set()
        for j in keep_idx:
            base = header[j] or f"列{j+1}"
            name = base
            k = 1
            while name in seen:
                k += 1
                name = f"{base}_{k}"
            seen.add(name)
            field_names.append(name)

        records = []
        for row in rows[1:]:
            rec = {}
            for pos, j in enumerate(keep_idx):
                val = row[j] if j < len(row) else ""
                rec[field_names[pos]] = str(val or "").strip()
            if any(v for v in rec.values()):
                records.append(rec)

        if records:
            log(f"✅ 表格解析完成: {len(field_names)} 列, {len(records)} 条记录")
            log(f"字段: {', '.join(field_names)}")
            # 打印前 3 行
            for i, rec in enumerate(records[:3]):
                log(f"  记录 {i+1}: {rec}")

            # --- 额外：从正文 Markdown 中提取失败原因合并到每条记录 ---
            log("--- 开始从文档正文提取失败原因 ---")
            try:
                raw_content = _fetch_raw_content(api_base, user_token, doc_token, log_fn=log)
                if raw_content:
                    field_names, records = _extract_failure_reasons_from_raw_content(
                        raw_content, records, log_fn=log
                    )
            except Exception as exc:
                log(f"  ⚠️  失败原因提取出错: {exc}（不影响表格数据写入）")

            log(f"最终字段: {', '.join(field_names)}")
            for i, rec in enumerate(records[:3]):
                log(f"  记录 {i+1}: {rec}")

            # --- 字段名最终映射（把云文档原始列名替换为业务字段名）---
            field_names, records = _apply_field_name_map(field_names, records)
            log(f"映射后字段: {', '.join(field_names)}")

            return field_names, records
        else:
            log("⚠️ 表格存在但解析出 0 条数据行，尝试其他策略")

    # --- 策略 2：Tab 分隔文本（兜底） ---
    log("未识别到有效表格，尝试 Tab 分隔文本兜底解析...")
    all_lines = []
    for blk in all_blocks:
        txt = _block_text(blk)
        if txt:
            for line in txt.split("\n"):
                line = line.strip()
                if line:
                    all_lines.append(line)

    result = _detect_columns_from_text(all_lines)
    if result is not None:
        field_names, records = result
        log(f"文本解析成功: {len(field_names)} 列, {len(records)} 条记录")
        log(f"字段: {', '.join(field_names)}")
        for i, rec in enumerate(records[:3]):
            log(f"  记录 {i+1}: {rec}")
        # 同样做字段名映射
        field_names, records = _apply_field_name_map(field_names, records)
        log(f"映射后字段: {', '.join(field_names)}")
        return field_names, records

    raise RuntimeError(
        "未能从云文档中解析出结构化数据。\n"
        "请确认：\n"
        "  1) 云文档内容包含一个真正的「表格」(不是纯文本)\n"
        "  2) 或使用 Tab 字符分隔的文本格式"
    )


# ============================================================
# 多维表格：查字段 / 补建字段 / 追加记录
# ============================================================


def list_bitable_fields(api_base, user_token, app_token, table_id, log_fn=None):
    """列出目标数据表所有字段，返回 [{field_id, field_name, type, ...}]"""
    log = log_fn or (lambda msg: None)
    headers = _headers(user_token)
    url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    fields = _get_all_pages(url, headers, item_key="items", page_size=100)
    log(f"目标数据表当前字段: {len(fields)} 个")
    for f in fields:
        if isinstance(f, dict):
            log(f"  - {f.get('field_name')} (id={f.get('field_id')}, type={f.get('type')})")
    return fields


def _clean_property_for_creation(property_data):
    """清理从列表接口读取的 property，去掉 options 中的内部字段（id、is_invalid 等）。"""
    if not property_data or not isinstance(property_data, dict):
        return None
    cleaned = {}
    for k, v in property_data.items():
        if k == "options" and isinstance(v, list):
            cleaned_options = []
            for opt in v:
                if isinstance(opt, dict):
                    clean_opt = {}
                    if "name" in opt:
                        clean_opt["name"] = opt["name"]
                    if "color" in opt:
                        clean_opt["color"] = opt["color"]
                    if clean_opt:
                        cleaned_options.append(clean_opt)
            cleaned["options"] = cleaned_options
        elif k in ("table_id", "format", "currency", "format_type",
                   "formula_expression", "formula_result_type", "formula"):
            cleaned[k] = v
    return cleaned if cleaned else None


def ensure_fields(api_base, user_token, app_token, table_id, field_names,
                  field_types=None, field_configs=None, log_fn=None):
    """对比目标表；缺失字段按对应类型 + property 创建。返回 (已存在集合, 新建数量)。

    field_configs: list[dict]，每项含 field_name/type/property；优先级最高
    field_types: 与 field_names 一一对应的类型列表（可选，没有 field_configs 时用）
    如果都没提供，全部用 type=1（文本）。
    """
    log = log_fn or (lambda msg: None)
    existing = list_bitable_fields(api_base, user_token, app_token, table_id, log_fn=log)
    existing_names = set()
    for f in existing:
        if isinstance(f, dict) and f.get("field_name"):
            existing_names.add(f["field_name"])

    headers = _headers(user_token)
    url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    created = 0

    for i, fn in enumerate(field_names):
        if fn in existing_names:
            continue

        # 优先从 field_configs 取配置（含 property），否则从 field_types 取 type
        cfg = field_configs[i] if field_configs and i < len(field_configs) else None
        ftype = cfg.get("type") if cfg else (field_types[i] if field_types and i < len(field_types) else 1)
        raw_property = cfg.get("property") if cfg else None

        # 关键：清理 property 中的内部字段，否则创建接口会报 1254082/1254083 错误
        cleaned_property = _clean_property_for_creation(raw_property)

        body = {"field_name": fn, "type": ftype}
        if cleaned_property:
            body["property"] = cleaned_property

        # 正确的类型名称（参考 api/feishu_api.py 的 FIELD_TYPE_MAPPING）
        type_name = {1: "文本", 2: "数字", 3: "单选", 4: "多选", 5: "日期",
                     7: "复选框", 11: "人员", 13: "电话号码", 15: "超链接",
                     17: "附件", 18: "单项关联", 19: "查找引用", 20: "公式",
                     21: "双向关联"}.get(ftype, f"type={ftype}")

        extra_info = ""
        if cleaned_property and "options" in cleaned_property:
            extra_info = f" (选项{len(cleaned_property['options'])}个)"

        try:
            _post(url, headers, json_body=body)
            existing_names.add(fn)
            created += 1
            log(f"  ✚ 新建字段: {fn} ({type_name}){extra_info}")
        except Exception as e:
            # 回落策略：如果带 property 创建失败（单选/多选需要 options）
            # 先尝试：保留类型但去掉 property（对人员/附件这类可能不需要 options 的类型有效）
            # 再尝试：完全回落为文本字段
            if ftype != 1:
                if cleaned_property:
                    log(f"  ⚠️  创建 '{fn}' 带配置失败，尝试仅保留类型: {e}")
                    try:
                        _post(url, headers, json_body={"field_name": fn, "type": ftype})
                        existing_names.add(fn)
                        created += 1
                        log(f"  ✚ 新建字段: {fn} ({type_name})")
                    except Exception as e2:
                        log(f"  ⚠️  创建 '{fn}' 仅保留类型也失败，回落为文本类型: {e2}")
                        try:
                            _post(url, headers, json_body={"field_name": fn, "type": 1})
                            existing_names.add(fn)
                            created += 1
                            log(f"  ✚ 新建字段: {fn} (文本)")
                        except Exception as e3:
                            log(f"  ❌ 创建字段 '{fn}' 彻底失败: {e3}")
                else:
                    log(f"  ⚠️  创建 '{fn}' 类型 {ftype} 失败，回落为文本类型: {e}")
                    try:
                        _post(url, headers, json_body={"field_name": fn, "type": 1})
                        existing_names.add(fn)
                        created += 1
                        log(f"  ✚ 新建字段: {fn} (文本)")
                    except Exception as e2:
                        log(f"  ❌ 创建字段 '{fn}' 彻底失败: {e2}")
            else:
                log(f"  ⚠️ 创建字段 '{fn}' 失败: {e}")

    log(f"字段核对完成：{len(existing_names)} 个字段（新建 {created} 个）")
    return existing_names, created


def append_records(api_base, user_token, app_token, table_id, records, field_names,
                   batch_size=50, log_fn=None):
    """分批写入记录；每批 50 条，字段值超过 10 万字符会被截断。"""
    log = log_fn or (lambda msg: None)
    headers = _headers(user_token)
    url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"

    total = 0
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        fields_list = []
        for rec in batch:
            fields = {}
            for fn in field_names:
                val = rec.get(fn, "")
                if val is None:
                    fields[fn] = ""
                elif isinstance(val, (dict, list)):
                    fields[fn] = json.dumps(val, ensure_ascii=False)[:100000]
                else:
                    s = str(val)
                    if len(s) > 100000:
                        s = s[:100000]
                    fields[fn] = s
            fields_list.append({"fields": fields})

        try:
            _post(url, headers, json_body={"records": fields_list})
            total += len(batch)
            log(f"  已写入 {total}/{len(records)} 条")
        except Exception as e:
            raise RuntimeError(f"写入第 {start}-{start+len(batch)} 条失败: {e}")
    return total


def list_records(api_base, user_token, app_token, table_id, batch_size=100, log_fn=None):
    """读取目标数据表的现有记录。返回 list[{record_id, fields:{name:value,...}}]。"""
    log = log_fn or (lambda msg: None)
    headers = _headers(user_token)
    url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    items = _get_all_pages(url, headers, item_key="items", page_size=batch_size)
    log(f"  目标数据表共 {len(items)} 条记录")
    return items


def update_records_by_key(api_base, user_token, app_token, table_id,
                          records, field_names, key_field_name,
                          batch_size=50, log_fn=None):
    """
    按匹配键字段批量更新已有记录。

    流程：
      1. 读取目标表的所有现有记录
      2. 用 key_field_name 建立 value -> record_id 的索引
      3. 对每条云文档记录：按 key 找到对应 record_id，然后用 batch_update 只更新写入的字段
      4. 云文档中存在但目标表中找不到 key 的记录 → 做 batch_create 追加

    返回：(updated_count, created_count, result_url)
    """
    log = log_fn or (lambda msg: None)
    if key_field_name not in field_names:
        raise RuntimeError(
            f"匹配字段 '{key_field_name}' 不在云文档解析出的字段中。"
            f"\n云文档解析出的字段：{field_names}"
        )

    log(f"--- 按匹配键 '{key_field_name}' 批量更新已有记录 ---")

    # 1) 读取目标表现有记录
    existing = list_records(api_base, user_token, app_token, table_id, log_fn=log)

    # 2) 获取目标表字段类型，跳过附件类型字段（避免 AttachFieldConvFail 错误）
    # 附件类型字段类型码：11=附件, 12=图片, 13=文件, 18=视频
    attachment_types = {11, 12, 13, 18}
    skip_fields = set()
    try:
        target_fields = list_bitable_fields(api_base, user_token, app_token, table_id, log_fn=None)
        for f in target_fields:
            if isinstance(f, dict):
                field_name = f.get("field_name")
                field_type = f.get("type")
                if field_name and field_type in attachment_types:
                    skip_fields.add(field_name)
                    log(f"  ⚠️  跳过附件类型字段: {field_name} (type={field_type})")
    except Exception as e:
        log(f"  ⚠️  获取字段类型失败，跳过检查: {e}")

    # 3) 建立 value -> record_id 索引
    key_to_record_id = {}
    for rec in existing:
        if not isinstance(rec, dict):
            continue
        rid = rec.get("record_id")
        fields = rec.get("fields") or {}
        key_val = None
        if key_field_name in fields:
            key_val = fields.get(key_field_name)
        # 兼容字段名末尾有空格/全半角差异：做一轮宽松匹配
        if key_val is None:
            for fn in fields:
                if isinstance(fn, str) and fn.strip().lower() == key_field_name.strip().lower():
                    key_val = fields.get(fn)
                    break
        if rid:
            k = str(key_val).strip() if key_val is not None else ""
            if k:
                key_to_record_id[k] = rid

    log(f"  建立匹配索引：{len(key_to_record_id)} 个有效值")

    # 4) 分桶：更新 vs 新增
    to_update = []   # [{record_id, fields:{}}]
    to_create = []   # [{fields:{}}]
    missing_key = 0
    matched_count = 0

    for rec in records:
        key_val_raw = rec.get(key_field_name, "")
        key_val = str(key_val_raw or "").strip()

        if not key_val:
            missing_key += 1
            # 跳过附件字段
            new_rec = {}
            for fn in field_names:
                if fn not in skip_fields:
                    new_rec[fn] = str(rec.get(fn, "")).strip()
            to_create.append(new_rec)
            continue

        existing_rid = key_to_record_id.get(key_val)
        # 再试：宽松匹配（去空格/忽略大小写）
        if existing_rid is None:
            for k in key_to_record_id:
                if k.strip().lower() == key_val.lower():
                    existing_rid = key_to_record_id[k]
                    break

        fields = {}
        for fn in field_names:
            if fn == key_field_name:
                # 匹配键本身也写（保持一致性，但不强制）
                pass
            if fn in skip_fields:
                continue  # 跳过附件类型字段
            val = rec.get(fn, "")
            if val is None:
                fields[fn] = ""
            elif isinstance(val, (dict, list)):
                fields[fn] = json.dumps(val, ensure_ascii=False)[:100000]
            else:
                s = str(val)
                if len(s) > 100000:
                    s = s[:100000]
                fields[fn] = s

        if existing_rid:
            to_update.append({"record_id": existing_rid, "fields": fields})
            matched_count += 1
        else:
            to_create.append(fields)

    log(f"  匹配成功 {matched_count} 条（将更新）")
    log(f"  未匹配 {len(to_create)} 条（将作为新记录追加）")
    if missing_key:
        log(f"  ⚠️  {missing_key} 条记录的匹配字段为空")

    headers = _headers(user_token)
    update_url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update"
    create_url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"

    # 4) 批量更新
    updated_total = 0
    for start in range(0, len(to_update), batch_size):
        batch = to_update[start:start + batch_size]
        try:
            _post(update_url, headers, json_body={"records": batch})
            updated_total += len(batch)
            log(f"  更新完成 {updated_total}/{len(to_update)} 条")
        except Exception as e:
            raise RuntimeError(f"批量更新第 {start}-{start+len(batch)} 条失败: {e}")

    # 5) 未匹配的 → 追加新记录
    created_total = 0
    for start in range(0, len(to_create), batch_size):
        batch = to_create[start:start + batch_size]
        body = [{"fields": f} for f in batch]
        try:
            _post(create_url, headers, json_body={"records": body})
            created_total += len(batch)
        except Exception as e:
            raise RuntimeError(f"批量追加第 {start}-{start+len(batch)} 条失败: {e}")

    if created_total:
        log(f"  追加新记录 {created_total} 条")

    return updated_total, created_total, _make_base_url(api_base, app_token, table_id)


def fill_new_columns_by_row_order(api_base, user_token, app_token, table_id,
                                   records, field_names, batch_size=50, log_fn=None):
    """
    按行号顺序把云文档数据填入现有记录的新列中。

    逻辑：
      1. 读取目标表的所有现有记录（按飞书 API 返回的顺序）
      2. 第 N 条云文档记录 → 填入目标表的第 N 条记录的指定字段
      3. 云文档记录数 > 现有记录数 → 超出的部分做 batch_create 追加为新行
      4. 云文档记录数 < 现有记录数 → 后面的现有记录不改动

    返回：(updated_count, created_count, result_url)
    """
    log = log_fn or (lambda msg: None)
    log("--- 按行号顺序填充现有记录的新列 ---")

    # 1) 读取现有记录
    existing = list_records(api_base, user_token, app_token, table_id, log_fn=log)
    log(f"  现有记录 {len(existing)} 条；本次写入 {len(records)} 条")

    # 2) 获取目标表字段类型，跳过附件类型字段（避免 AttachFieldConvFail 错误）
    # 附件类型字段类型码：11=附件, 12=图片, 13=文件, 18=视频
    attachment_types = {11, 12, 13, 18}
    skip_fields = set()
    try:
        target_fields = list_bitable_fields(api_base, user_token, app_token, table_id, log_fn=None)
        for f in target_fields:
            if isinstance(f, dict):
                field_name = f.get("field_name")
                field_type = f.get("type")
                if field_name and field_type in attachment_types:
                    skip_fields.add(field_name)
                    log(f"  ⚠️  跳过附件类型字段: {field_name} (type={field_type})")
    except Exception as e:
        log(f"  ⚠️  获取字段类型失败，跳过检查: {e}")

    headers = _headers(user_token)
    update_url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update"
    create_url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"

    # 3) 构建 fields dict（只写入云文档解析出的列，跳过附件类型字段）


    def _make_fields(rec):
        fields = {}
        for fn in field_names:
            if fn in skip_fields:
                continue  # 跳过附件类型字段
            val = rec.get(fn, "")
            if val is None:
                fields[fn] = ""
            elif isinstance(val, (dict, list)):
                fields[fn] = json.dumps(val, ensure_ascii=False)[:100000]
            else:
                s = str(val)
                if len(s) > 100000:
                    s = s[:100000]
                fields[fn] = s
        return fields

    # 3) 分桶：更新 vs 追加
    to_update = []   # [{record_id, fields:{...}}]
    to_create = []   # [{fields:{...}}]

    for idx, rec in enumerate(records):
        fields = _make_fields(rec)
        if idx < len(existing) and isinstance(existing[idx], dict) and existing[idx].get("record_id"):
            to_update.append({"record_id": existing[idx]["record_id"], "fields": fields})
        else:
            to_create.append(fields)

    log(f"  将更新 {len(to_update)} 条现有记录；云文档超出部分将追加 {len(to_create)} 条新记录")

    # 4) 批量更新
    updated_total = 0
    for start in range(0, len(to_update), batch_size):
        batch = to_update[start:start + batch_size]
        try:
            _post(update_url, headers, json_body={"records": batch})
            updated_total += len(batch)
            log(f"  已更新 {updated_total}/{len(to_update)} 条")
        except Exception as e:
            raise RuntimeError(f"批量更新第 {start}-{start+len(batch)} 条失败: {e}")

    # 5) 超出部分 → 追加新行
    created_total = 0
    for start in range(0, len(to_create), batch_size):
        batch = to_create[start:start + batch_size]
        body = [{"fields": f} for f in batch]
        try:
            _post(create_url, headers, json_body={"records": body})
            created_total += len(batch)
        except Exception as e:
            raise RuntimeError(f"批量追加第 {start}-{start+len(batch)} 条失败: {e}")
    if created_total:
        log(f"  已追加超出部分 {created_total} 条")

    return updated_total, created_total, _make_base_url(api_base, app_token, table_id)


# ============================================================
# 对外入口（供对话框调用）
# ============================================================


def run_append_to_table(user_token, doc_input, target_app_token, target_table_id, log_fn=None):
    """模式 B：把云文档数据**追加到已有数据表**。

    流程：解析云文档 → 核对字段 → 写入数据。返回 (写入条数, 结果URL)。"""
    log = log_fn or (lambda msg: None)

    doc_token = extract_token_from_url(doc_input)
    if not doc_token:
        raise RuntimeError(f"无法从输入解析出 doc_token: {doc_input}")

    api_base = _detect_api_base(doc_input)

    # 1) 解析文档
    field_names, records = parse_doc_as_records(api_base, user_token, doc_token, log_fn=log)
    if not records:
        raise RuntimeError("云文档中未解析出任何数据")

    # 2) 补建字段（确保目标表有这些列）
    log("--- 核对目标数据表字段 ---")
    ensure_fields(api_base, user_token, target_app_token, target_table_id, field_names, log_fn=log)

    # 3) 写入
    log(f"--- 开始写入 {len(records)} 条记录 ---")
    written = append_records(api_base, user_token, target_app_token, target_table_id,
                             records, field_names, batch_size=50, log_fn=log)
    log(f"✅ 成功追加 {written} 条记录")
    return written, _make_base_url(api_base, target_app_token, target_table_id)


def run_create_new_table(user_token, doc_input, new_table_name, log_fn=None):
    """模式 A：新建一个全新的飞书多维表格（base），并写入数据。"""
    log = log_fn or (lambda msg: None)

    doc_token = extract_token_from_url(doc_input)
    api_base = _detect_api_base(doc_input)

    field_names, records = parse_doc_as_records(api_base, user_token, doc_token, log_fn=log)
    if not records:
        raise RuntimeError("云文档中未解析出任何数据")

    # Step 1: 新建一个多维表格应用（base）
    log(f"创建全新多维表格 '{new_table_name}'...")
    headers = _headers(user_token)
    url = f"{api_base}/open-apis/bitable/v1/apps"
    body = {"name": new_table_name}
    data = _post(url, headers, json_body=body)
    app = data.get("app") if isinstance(data.get("app"), dict) else data
    target_app_token = app.get("app_token")
    default_table_id = app.get("table_id")
    if not target_app_token:
        raise RuntimeError(f"新建多维表格未返回 app_token，响应: {data}")
    log(f"✅ 多维表格创建成功 app_token={target_app_token}")

    # Step 2: 如果默认表可用，直接把字段建到默认表；否则新建一张数据表
    if default_table_id:
        target_table_id = default_table_id
        log(f"使用默认数据表 table_id={target_table_id}，补建字段...")
        ensure_fields(api_base, user_token, target_app_token, target_table_id, field_names, log_fn=log)
    else:
        target_table_id = _create_table(api_base, user_token, target_app_token, new_table_name, field_names)
        log(f"新建数据表成功 table_id={target_table_id}")

    # Step 3: 写入记录
    written = append_records(api_base, user_token, target_app_token, target_table_id,
                             records, field_names, batch_size=50, log_fn=log)
    log(f"✅ 已新建多维表格并写入 {written} 条记录")
    return written, _make_base_url(api_base, target_app_token, target_table_id)


def _create_table(api_base, user_token, app_token, table_name, field_names):
    """新建数据表并返回 table_id。"""
    headers = _headers(user_token)
    url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables"
    fields_payload = []
    for fn in field_names:
        fields_payload.append({"field_name": fn, "type": 1, "property": None})
    body = {"table": {"name": table_name, "fields": fields_payload}}
    data = _post(url, headers, json_body=body)
    tbl = data.get("table") if isinstance(data.get("table"), dict) else data
    table_id = tbl.get("table_id")
    if not table_id:
        raise RuntimeError(f"新建数据表未返回 table_id，响应: {data}")
    return table_id


def _make_base_url(api_base, app_token, table_id=None):
    domain = "bytedance.larkoffice.com" if ("larksuite" in api_base or "larkoffice" in api_base) else "bytedance.feishu.cn"
    url = f"https://{domain}/base/{app_token}"
    if table_id:
        url += f"?table={table_id}"
    return url

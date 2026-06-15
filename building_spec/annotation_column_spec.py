"""
生成标注列 - 业务逻辑模块

核心流程：
  1. 用户选择模式（小白/Lite / Standard / Pro）
  2. 到配置 Bitable（Ji0Yb8dgvaA8bgsijJtcdFbLnOe）中查询模式对应的数据表
  3. 读取该数据表的全部记录（跳过第一列）
  4. 追加写入到用户指定的目标 Bitable 链接表中

UI 层由 ui/building_ui/annotation_column_dialog.py 负责，
它调用本模块中的 AnnotationColumnWorker 完成耗时操作。
"""
import sys
import os
import datetime

# 添加上级目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from PyQt5.QtCore import QThread, pyqtSignal


# ------------------------------------------------------------------
# 配置表（固定）
# ------------------------------------------------------------------
CONFIG_APP_TOKEN = "Ji0Yb8dgvaA8bgsijJtcdFbLnOe"
CONFIG_API_BASE = "https://open.larksuite.com"


# ------------------------------------------------------------------
# 模式名称映射（用户在 UI 看到的文本 → 在配置表中查找的关键词）
# ------------------------------------------------------------------
MODE_DISPLAY = {
    "lite": "小白/Lite 模式",
    "standard": "Standard 模式",
    "pro": "Pro 模式",
}


# ------------------------------------------------------------------
# Helper: 安全的单行文本提取，用于把飞书返回的字段值转成普通字符串
# ------------------------------------------------------------------
def _field_value_to_str(v):
    """把飞书 API 返回的字段值（可能是 dict/list/str/int/float/None）转成纯文本。"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        # 常见于多选/关联字段，取内部文本
        parts = []
        for item in v:
            if isinstance(item, dict):
                # 关联字段可能 {"record_id": "...", "title": "xxx"} 或类似结构
                for key in ("text", "name", "title", "value", "en_name"):
                    if key in item and item[key] is not None:
                        parts.append(str(item[key]))
                        break
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return ", ".join(parts)
    if isinstance(v, dict):
        # 单选等
        for key in ("text", "name", "title", "value", "en_name"):
            if key in v and v[key] is not None:
                return str(v[key])
        return str(v)
    return str(v)


# ------------------------------------------------------------------
# 列出某 base 下的所有 table（调用飞书 Bitable tables 列表接口）
# ------------------------------------------------------------------
def list_tables(api_base, user_token, app_token, log_fn=None):
    """
    列出指定 app 下的所有 table。
    返回: [{"table_id": "xxx", "name": "xxx"}, ...]
    """
    from doc_base.doc_to_bitable_core import _headers, _get_all_pages

    log = log_fn or (lambda msg: None)
    headers = _headers(user_token)
    url = f"{api_base}/open-apis/bitable/v1/apps/{app_token}/tables"

    log(f"  请求 APP 数据表列表: {url}")
    items = _get_all_pages(url, headers, item_key="items")

    tables = []
    for item in items:
        if isinstance(item, dict):
            tid = item.get("table_id") or item.get("id")
            tname = item.get("name") or item.get("table_name") or ""
            tables.append({"table_id": tid, "name": tname})
    log(f"  共检索到 {len(tables)} 个数据表:")
    for t in tables:
        log(f"    - {t.get('name')}  (table_id={t.get('table_id')})")
    return tables


# ------------------------------------------------------------------
# 主逻辑：在配置表中查找匹配模式的数据表
# ------------------------------------------------------------------
def find_mode_table(api_base, user_token, mode, log_fn=None):
    """
    在配置 APP 中查找名称与所选模式匹配的 table。

    匹配策略（优先级从高到低）：
      1. 精确匹配 == "小白/Lite 模式" 等
      2. 包含匹配: table 名称中包含 "小白/Lite" / "Standard" / "Pro"
      3. 英文关键字匹配: table 名称包含 "lite" / "standard" / "pro"
      4. 兜底: 如果只有 1 张表，直接使用该表
    返回: {"table_id": ..., "name": ...}  找不到则返回 None
    """
    log = log_fn or (lambda msg: None)
    display = MODE_DISPLAY.get(mode, mode)

    log(f"  在配置表({CONFIG_APP_TOKEN})中查找匹配模式: {display}")
    tables = list_tables(api_base, user_token, CONFIG_APP_TOKEN, log_fn=log)

    if not tables:
        log("  ❌ 配置表中没有任何数据表，请确认 app_token 是否正确。")
        return None

    # 1) 精确匹配
    for t in tables:
        tname = (t.get("name") or "").strip()
        if tname == display:
            log(f"  ✅ 精确匹配找到数据表: {tname} ({t.get('table_id')})")
            return t

    # 2) 包含匹配（模式关键词在 table 名中，或 table 名在模式关键词中）
    for t in tables:
        tname = (t.get("name") or "").strip()
        if display.lower() in tname.lower() or tname.lower() in display.lower():
            log(f"  ✅ 包含匹配找到数据表: {tname} ({t.get('table_id')})")
            return t

    # 3) 英文关键字匹配（lite / standard / pro）
    mode_keyword = mode.lower()
    for t in tables:
        tname = (t.get("name") or "").strip()
        if mode_keyword in tname.lower():
            log(f"  ✅ 关键字匹配找到数据表: {tname} ({t.get('table_id')})")
            return t

    # 4) 兜底：如果只有一张表，直接使用
    if len(tables) == 1:
        log(f"  ✅ 兜底：配置表只有 1 张表，直接使用: {tables[0].get('name')} ({tables[0].get('table_id')})")
        return tables[0]

    log(f"  ❌ 未在配置表中找到匹配 '{display}' 的数据表。")
    log(f"  提示：请将 table 名称改为包含「{display}」、「{mode.upper()}」或「{mode.lower()}」关键字。")
    return None


# ------------------------------------------------------------------
# 读取目标数据表的所有记录，并跳过第一列
# ------------------------------------------------------------------
def read_template_columns(api_base, user_token, table_info, log_fn=None):
    """
    读取模板数据表的字段定义，跳过第一列。

    参数 table_info: {"table_id": "...", "name": "..."}
    返回: (field_names, field_types, field_configs)
      - field_names: list[str]，跳过第一列后的字段名列表
      - field_types: list[int]，对应的字段类型
      - field_configs: list[dict]，完整字段配置（含 property/options 等，用于创建时保留原始配置）
    """
    from doc_base.doc_to_bitable_core import list_bitable_fields

    log = log_fn or (lambda msg: None)
    table_id = table_info.get("table_id")

    log(f"  读取模板表: {table_info.get('name')} ({table_id})")

    # 1) 获取字段定义，并保留「除第一列外」的所有字段
    all_fields = list_bitable_fields(api_base, user_token, CONFIG_APP_TOKEN, table_id, log_fn=log)
    if not all_fields:
        log("  ⚠️  无法读取模板表的字段定义（返回为空）")
        return [], [], []

    # 解析字段（参考 api/feishu_api.py 的成熟写法：兼容 field_type/type 两种键，提取 property）
    field_dicts = []
    for f in all_fields:
        if isinstance(f, dict):
            fn = f.get("field_name") or f.get("name") or ""
            # 关键：API 可能返回 field_type 也可能返回 type，两个都尝试
            ftype = f.get("field_type") or f.get("type", 1)
            # 关键：直接提取 property（单选/多选字段的 options 在这里）
            fproperty = f.get("property")
            if fn:
                prop_info = ""
                if isinstance(fproperty, dict) and fproperty:
                    if "options" in fproperty:
                        prop_info = f", property.options={len(fproperty['options'])}"
                    else:
                        prop_info = f", property.keys={list(fproperty.keys())[:5]}"
                else:
                    prop_info = f", property=None"
                log(f"    - {fn}  (type={ftype}{prop_info})")
                field_dicts.append({
                    "field_name": fn,
                    "type": ftype,
                    "property": fproperty,
                    "_raw": f,
                })

    # 2) 跳过第一列
    target_fields = field_dicts[1:]
    if not target_fields:
        log("  ⚠️  模板表只有 1 列（已被跳过），没有可追加的字段。")
        log("  提示：请在模板表中增加第二列及之后的字段。")
        return [], [], []

    target_field_names = [f["field_name"] for f in target_fields]
    target_field_types = [f["type"] for f in target_fields]
    target_field_configs = [{
        "field_name": f["field_name"],
        "type": f["type"],
        "property": f["property"],
    } for f in target_fields]
    log(f"  将追加的字段 ({len(target_field_names)} 个): {', '.join(target_field_names)}")
    return target_field_names, target_field_types, target_field_configs


# ------------------------------------------------------------------
# 写入：把模板表读出来的记录追加到目标表
# ------------------------------------------------------------------
def add_columns_to_target_table(api_base, user_token, target_app_token, target_table_id,
                                field_names, field_types=None, field_configs=None, log_fn=None):
    """
    在目标表中追加新列（字段）。按模板表中的类型 + property 创建。已存在的字段跳过。
    field_configs: list[dict]，每个元素含 field_name/type/property，优先级最高
    返回: (existing_count, created_count)
    """
    from doc_base.doc_to_bitable_core import ensure_fields

    log = log_fn or (lambda msg: None)

    log(f"  目标表: {target_app_token} / {target_table_id}")
    log(f"  待追加字段 ({len(field_names)} 个): {', '.join(field_names)}")

    existing_names, created = ensure_fields(
        api_base, user_token, target_app_token, target_table_id,
        field_names, field_types=field_types, field_configs=field_configs, log_fn=log
    )
    skipped = len(field_names) - created
    log(f"  ✅ 完成：本次请求的 {len(field_names)} 个字段中，跳过已有 {skipped} 个，新增 {created} 个")
    return skipped, created


# ==================================================================
# 后台工作线程（给 UI 层调用）
# ==================================================================
class AnnotationColumnWorker(QThread):
    """执行预览或写入操作的后台线程。"""

    finished = pyqtSignal(bool, object, str)   # (success, result_data, error_msg)
    log_message = pyqtSignal(str)

    def __init__(self, task_type, **kwargs):
        super().__init__()
        self.task_type = task_type   # 'preview' 或 'write'
        self.kwargs = kwargs
        self._stop_flag = False

    def run(self):
        try:
            if self.task_type == 'preview':
                self._run_preview()
            elif self.task_type == 'write':
                self._run_write()
        except Exception as e:
            self.finished.emit(False, None, str(e))

    def log(self, msg):
        self.log_message.emit(msg)

    # -----------------------------------------------------------
    # 预览：查询配置表 + 读取模板数据 + 展示给用户确认
    # -----------------------------------------------------------
    def _run_preview(self):
        user_token = self.kwargs.get('user_token')
        mode = self.kwargs.get('mode')  # lite / standard / pro
        target_api_base = self.kwargs.get('target_api_base')
        target_app_token = self.kwargs.get('target_app_token')
        target_table_id = self.kwargs.get('target_table_id')

        self.log(f"当前模式: {MODE_DISPLAY.get(mode, mode)}")
        self.log("开始查询配置表...")

        # 1) 在配置表中找到匹配的数据表
        table_info = find_mode_table(CONFIG_API_BASE, user_token, mode, log_fn=self.log)
        if table_info is None:
            self.finished.emit(False, None,
                f"未在配置表中找到与「{MODE_DISPLAY.get(mode, mode)}」匹配的数据表。")
            return

        # 2) 读取模板表的字段定义（跳过第一列）
        field_names, field_types, field_configs = read_template_columns(
            CONFIG_API_BASE, user_token, table_info, log_fn=self.log
        )
        if not field_names:
            self.finished.emit(False, None,
                "模板表字段读取失败。请确认模板表至少有 2 列（第一列留作 ID/序号）。")
            return

        # 3) 返回给 UI 用于预览
        result = {
            "template_table_name": table_info.get("name"),
            "template_table_id": table_info.get("table_id"),
            "field_names": field_names,
            "field_types": field_types,
            "field_configs": field_configs,
            "target_api_base": target_api_base or CONFIG_API_BASE,
            "target_app_token": target_app_token,
            "target_table_id": target_table_id,
        }
        self.finished.emit(True, result, "")

    # -----------------------------------------------------------
    # 写入：在目标表中追加列
    # -----------------------------------------------------------
    def _run_write(self):
        user_token = self.kwargs.get('user_token')
        field_names = self.kwargs.get('field_names')
        field_types = self.kwargs.get('field_types')
        field_configs = self.kwargs.get('field_configs')
        target_api_base = self.kwargs.get('target_api_base')
        target_app_token = self.kwargs.get('target_app_token')
        target_table_id = self.kwargs.get('target_table_id')

        self.log(f"开始追加列 ({len(field_names)} 个)")

        skipped, created = add_columns_to_target_table(
            target_api_base, user_token, target_app_token, target_table_id,
            field_names, field_types=field_types, field_configs=field_configs, log_fn=self.log
        )
        self.finished.emit(True, (skipped, created), "")

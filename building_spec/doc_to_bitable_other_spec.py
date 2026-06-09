"""
飞书云文档 → 多维表格 · 其他模式逻辑模块

逻辑与 Building 模式保持一致（先预览解析，确认后再写入）。
提供两部分：
  1. DocToBitableOtherWorker  —— 后台线程（执行解析/写入的耗时操作）
  2. DocToBitableOtherLogic   —— 预览 + 写入的业务逻辑
"""
import sys
import os
import datetime

from PyQt5.QtCore import QThread, pyqtSignal

# 添加项目根目录，以便导入 doc_base
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _parent_dir)


# ======================================================================
# 1. 后台线程 —— 与 Building 模式的 WorkerThread 完全一致
# ======================================================================
class DocToBitableOtherWorker(QThread):
    """后台工作线程 —— 执行耗时操作（解析文档、写入表格）"""

    finished = pyqtSignal(bool, object, str)  # (success, result_data, error_msg)
    log_message = pyqtSignal(str)

    def __init__(self, task_type, **kwargs):
        super().__init__()
        self.task_type = task_type  # 'preview' 或 'write'
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

    def _run_preview(self):
        """预览解析任务（其他模式：查找『用例总览』标题下面的表格）"""
        api_base = self.kwargs.get('api_base')
        user_token = self.kwargs.get('user_token')
        doc_token = self.kwargs.get('doc_token')

        def log_fn(msg):
            self.log_message.emit(msg)

        field_names, records = parse_overview_table_as_records(
            api_base, user_token, doc_token, log_fn=log_fn
        )
        self.finished.emit(True, (field_names, records), "")

    def _run_write(self):
        """写入任务"""
        api_base = self.kwargs.get('api_base')
        user_token = self.kwargs.get('user_token')
        app_token = self.kwargs.get('app_token')
        table_id = self.kwargs.get('table_id')
        field_names = self.kwargs.get('field_names')
        records = self.kwargs.get('records')
        mode = self.kwargs.get('mode')

        def log_fn(msg):
            self.log_message.emit(msg)

        if mode == 'B':
            from doc_base.doc_to_bitable_core import ensure_fields, fill_new_columns_by_row_order

            ensure_fields(api_base, user_token, app_token, table_id, field_names, log_fn=log_fn)
            updated, created, result_url = fill_new_columns_by_row_order(
                api_base, user_token, app_token, table_id,
                records, field_names, batch_size=50, log_fn=log_fn
            )
            self.finished.emit(True, (updated, created, result_url), "")
        else:
            # 方式 A：创建全新多维表格（使用『用例总览』表格解析逻辑）
            doc_input = self.kwargs.get('doc_input')
            new_table_name = self.kwargs.get('new_table_name')
            written, result_url = _run_create_new_table_other_mode(
                user_token, doc_input, new_table_name, log_fn=log_fn
            )
            self.finished.emit(True, (written, result_url), "")


# ======================================================================
# 2. 业务逻辑封装 —— 与 Building 模式的 on_preview / on_run 逻辑一致
# ======================================================================
class DocToBitableOtherLogic:
    """
    其他模式的业务逻辑容器。

    用法（在 UI 层）：
      self.logic = DocToBitableOtherLogic(
          get_inputs_fn=lambda: {
              'token_input': self.token_input,
              'doc_input': self.doc_input,
              'a_name_input': self.a_name_input,
              'existing_bitable_input': self.existing_bitable_input,
          },
          append_log_fn=self.append_log,
          get_parsed_cache_fn=lambda: self._parsed_cache,
          set_parsed_cache_fn=lambda v: setattr(self, '_parsed_cache', v),
      )
      self.logic.on_preview()    # 触发预览
      self.logic.on_run()        # 触发写入
    """

    def __init__(self, panel):
        """
        Args:
            panel: 拥有以下属性/方法的 UI 面板对象：
              - token_input / doc_input / a_name_input / existing_bitable_input
              - result_text
              - preview_btn / run_btn
              - append_log(text)
              - _parsed_cache (可变的缓存元组：(field_names, records, mode_info))
              - is_processing (bool)
        """
        self.panel = panel
        self.worker = None  # 当前运行的后台线程引用

    # ---------------------------------------------------------------
    # 辅助：从输入控件取值
    # ---------------------------------------------------------------
    def _get_inputs(self):
        return {
            'user_token': self.panel.token_input.text().strip(),
            'doc_input_text': self.panel.doc_input.text().strip(),
            'existing_bitable': self.panel.existing_bitable_input.text().strip(),
            'a_name': self.panel.a_name_input.text().strip(),
        }

    # ---------------------------------------------------------------
    # 预览：只解析不写入
    # ---------------------------------------------------------------
    def on_preview(self):
        if self.panel.is_processing:
            return

        inputs = self._get_inputs()
        user_token = inputs['user_token']
        doc_input_text = inputs['doc_input_text']
        existing_bitable = inputs['existing_bitable']
        a_name = inputs['a_name']

        if not user_token:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.panel, "提示", "请输入 User Access Token"); return
        if not doc_input_text:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.panel, "提示", "请输入飞书云文档链接或 doc_token"); return

        # 判断输出模式
        from doc_base.doc_to_bitable_core import (
            extract_bitable_info_from_url, _detect_api_base, extract_token_from_url,
        )

        mode = None
        mode_info = None
        if existing_bitable:
            api_base, app_token, table_id = extract_bitable_info_from_url(existing_bitable)
            if not app_token:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self.panel, "提示", "B 选项中的链接无法解析出 app_token"); return
            mode_info = ("B", api_base, app_token, table_id)
            mode = "B"
        else:
            api_base = _detect_api_base(doc_input_text)
            if not a_name:
                a_name = f"导入_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
            mode_info = ("A", api_base, a_name, None)
            mode = "A"

        # 准备工作：禁用按钮、清空日志
        self.panel.is_processing = True
        self.panel.preview_btn.setEnabled(False)
        self.panel.run_btn.setEnabled(False)
        self.panel.result_text.clear()
        self.panel.append_log("开始解析云文档...")

        # 创建后台线程执行解析
        doc_token = extract_token_from_url(doc_input_text)
        self.worker = DocToBitableOtherWorker(
            task_type='preview',
            api_base=api_base,
            user_token=user_token,
            doc_token=doc_token,
            mode_info=mode_info,
        )
        self.worker.log_message.connect(self.panel.append_log)
        self.worker.finished.connect(
            lambda success, data, err: self._on_preview_finished(success, data, err, mode_info)
        )
        self.worker.start()

    def _on_preview_finished(self, success, data, error_msg, mode_info):
        """预览完成后的回调"""
        from PyQt5.QtWidgets import QMessageBox

        try:
            if success and data:
                field_names, records = data
                mode = mode_info[0]

                self.panel.append_log("")
                self.panel.append_log(f"======== 预览 ========")
                self.panel.append_log(f"解析结果：")
                self.panel.append_log(f"  字段数: {len(field_names)}")
                self.panel.append_log(f"  记录数: {len(records)}")
                self.panel.append_log(f"  字段: {', '.join(field_names)}")
                self.panel.append_log("")

                if records:
                    self.panel.append_log("前 5 条记录预览：")
                    for i, rec in enumerate(records[:5]):
                        self.panel.append_log(f"  第 {i + 1} 条: {rec}")

                # 如果是模式 B：额外展示目标表字段对比
                if mode == "B" and mode_info[3]:
                    self.panel.append_log("")
                    self.panel.append_log(f"--- 目标数据表字段对比 ---")
                    try:
                        from doc_base.doc_to_bitable_core import list_bitable_fields
                        api_base = mode_info[1]
                        user_token = self.panel.token_input.text().strip()
                        target_fields = list_bitable_fields(
                            api_base, user_token, mode_info[2], mode_info[3],
                            log_fn=self.panel.append_log,
                        )
                        target_names = []
                        for f in target_fields:
                            if isinstance(f, dict) and f.get("field_name"):
                                target_names.append(f["field_name"])

                        self.panel.append_log("")
                        self.panel.append_log("字段匹配检查：")
                        matched = []
                        unmatched = []
                        for fn in field_names:
                            hit = None
                            for tn in target_names:
                                if (isinstance(tn, str) and isinstance(fn, str)
                                        and tn.strip().lower() == fn.strip().lower()):
                                    hit = tn
                                    break
                            if hit:
                                matched.append(fn)
                            else:
                                unmatched.append(fn)
                        if matched:
                            self.panel.append_log(f"  ✅ 已存在字段：{', '.join(matched)}")
                        if unmatched:
                            self.panel.append_log(
                                f"  ➕ 新建字段（将自动创建为文本类型）：{', '.join(unmatched)}"
                            )
                        self.panel.append_log("")

                        # 智能提示匹配字段（如果面板上有 key_field_input 才生效）
                        key_field_input = getattr(self.panel, 'key_field_input', None)
                        if key_field_input is not None and target_names:
                            suggested = None
                            for fn in field_names:
                                if any(k in str(fn) for k in ("ID", "id", "编号", "失败项", "名称")):
                                    suggested = fn
                                    break
                            if suggested is None and field_names:
                                suggested = field_names[0]
                            self.panel.append_log(f"💡 建议：将「{suggested}」填到下方【匹配字段名】中。")
                            key_field_input.setText(suggested)
                    except Exception as fe:
                        self.panel.append_log(f"  (读取目标表字段失败，不影响写入：{fe})")

                self.panel._parsed_cache = (field_names, records, mode_info)
                self.panel.run_btn.setEnabled(True)
                self.panel.append_log("")
                self.panel.append_log("✅ 预览完成。如果预览正确，请点击【确认并写入】。")

                QMessageBox.information(
                    self.panel, "预览成功",
                    f"解析完成：{len(field_names)} 个字段，{len(records)} 条记录。\n\n"
                    f"字段：{', '.join(field_names)}\n\n"
                    f"请检查日志区域查看详细解析结果。如果没问题请点击【确认并写入】。"
                )
            else:
                self.panel.append_log(f"❌ 错误: {error_msg}")
                QMessageBox.critical(self.panel, "解析失败", error_msg)
        finally:
            self.panel.is_processing = False
            self.panel.preview_btn.setEnabled(True)

    # ---------------------------------------------------------------
    # 执行写入（预览通过后调用）
    # ---------------------------------------------------------------
    def on_run(self):
        from PyQt5.QtWidgets import QMessageBox

        if self.panel.is_processing or self.panel._parsed_cache is None:
            if self.panel._parsed_cache is None:
                QMessageBox.warning(self.panel, "提示", "请先点击【预览解析结果】"); return
            return

        field_names, records, mode_info = self.panel._parsed_cache
        mode = mode_info[0]

        # 禁用按钮
        self.panel.is_processing = True
        self.panel.run_btn.setEnabled(False)
        self.panel.preview_btn.setEnabled(False)

        user_token = self.panel.token_input.text().strip()

        # 创建后台线程执行写入
        worker_kwargs = {
            'task_type': 'write',
            'user_token': user_token,
            'mode': mode,
        }
        if mode == 'A':
            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M')
            new_table_name = self.panel.a_name_input.text().strip() or f"导入_{ts}"
            worker_kwargs['doc_input'] = self.panel.doc_input.text().strip()
            worker_kwargs['new_table_name'] = new_table_name
        else:
            api_base = mode_info[1]
            app_token = mode_info[2]
            table_id = mode_info[3]
            fields_to_write = [fn for fn in field_names if fn != "ID"]
            records_to_write = [
                {k: v for k, v in rec.items() if k != "ID"}
                for rec in records
            ]
            if "ID" in field_names:
                self.panel.append_log(f"提示：已跳过 ID 字段，将写入 {len(fields_to_write)} 个字段")
            worker_kwargs['api_base'] = api_base
            worker_kwargs['app_token'] = app_token
            worker_kwargs['table_id'] = table_id
            worker_kwargs['field_names'] = fields_to_write
            worker_kwargs['records'] = records_to_write

        self.worker = DocToBitableOtherWorker(**worker_kwargs)
        self.worker.log_message.connect(self.panel.append_log)
        self.worker.finished.connect(
            lambda success, data, err: self._on_run_finished(success, data, err, mode)
        )
        self.worker.start()

    def _on_run_finished(self, success, data, error_msg, mode):
        """写入完成后的回调"""
        from PyQt5.QtWidgets import QMessageBox

        try:
            if success and data:
                if mode == 'B':
                    updated, created, result_url = data
                    self.panel.append_log(
                        f"✅ 完成：已更新 {updated} 条现有记录的新列值；追加 {created} 条新记录"
                    )
                    QMessageBox.information(
                        self.panel, "完成",
                        f"✅ 完成：\n  • 更新 {updated} 条记录的新列值\n  • 追加 {created} 条新记录\n\n链接：{result_url}"
                    )
                else:
                    written, result_url = data
                    QMessageBox.information(
                        self.panel, "完成",
                        f"✅ 已新建数据表并写入 {written} 条记录\n\n链接：{result_url}"
                    )
            else:
                self.panel.append_log(f"❌ 错误: {error_msg}")
                QMessageBox.critical(self.panel, "失败", error_msg)
        finally:
            self.panel.is_processing = False
            self.panel.run_btn.setEnabled(True)
            self.panel.preview_btn.setEnabled(True)


# ======================================================================
# 其他模式专用：定位『用例总览』标题下的表格并解析
# ======================================================================

# 定位『用例总览』标题使用的关键词（小写匹配，便于兼容多种写法）
_OVERVIEW_HEADING_KEYWORDS = ("用例总览", "用例汇总", "case overview", "overview")

# 后续标题关键词（遇到这些词表示到了下一个 section，停止向前扫描表格）
_NEXT_SECTION_KEYWORDS = (
    "整体结论", "整体通过", "执行环境", "失败原因",
    "table", "permission", "workflow", "dashboard",
)


def _is_overview_heading(text):
    """判断一段文本是否是『用例总览』相关的标题。"""
    if not isinstance(text, str):
        return False
    low = text.strip().lower()
    if not low:
        return False
    for kw in _OVERVIEW_HEADING_KEYWORDS:
        if kw.lower() in low:
            return True
    return False


def _is_next_section_heading(text):
    """判断一段文本是否是『下一个 section』的标题（用于停止向前扫描表格）。"""
    if not isinstance(text, str):
        return False
    low = text.strip().lower()
    if not low:
        return False
    for kw in _NEXT_SECTION_KEYWORDS:
        if kw.lower() in low:
            return True
    return False


def _find_overview_table_blocks(all_blocks, log_fn=None):
    """
    在扁平 block 列表中查找位于『用例总览』section 下的表格。

    策略：
      1. 遍历所有 block，找到第一个文本包含「用例总览 / 用例汇总 / overview」
         的 heading / paragraph block（记为 heading_idx）。
      2. 从 heading_idx + 1 开始向前扫描：
           - 遇到表格 block → 返回这张表格
           - 遇到其他 section 的标题关键词 → 停止（说明已经过了用例总览 section）
      3. 如果找不到 heading 但文档中包含多张表格，使用最后一张表格兜底
         （很多情况下『用例总览』位于文档末尾）。
    """
    log = log_fn or (lambda msg: None)

    # 先建 block_id -> block 映射（和 doc_to_bitable_core 保持一致）
    block_map = {}
    for blk in all_blocks:
        if isinstance(blk, dict) and isinstance(blk.get("block_id"), str):
            block_map[blk["block_id"]] = blk

    # Step 1：找 heading_idx
    heading_idx = None
    for idx, blk in enumerate(all_blocks):
        if not isinstance(blk, dict):
            continue
        txt = _safe_block_text(blk)
        if _is_overview_heading(txt):
            log(f"  ✅ 在 block[{idx}] 找到『用例总览』标题: '{txt}'")
            heading_idx = idx
            break

    # Step 2：从 heading_idx 往后找表格
    if heading_idx is not None:
        for idx in range(heading_idx + 1, len(all_blocks)):
            blk = all_blocks[idx]
            if not isinstance(blk, dict):
                continue

            # 遇到下一个 section 的标题 → 停止
            txt = _safe_block_text(blk)
            if txt and _is_next_section_heading(txt):
                log(f"  ℹ️  在 block[{idx}] 遇到下一个 section: '{txt}'，停止向前扫描")
                break

            block_type = blk.get("block_type") or blk.get("type")
            has_table_field = "table" in blk and isinstance(blk.get("table"), dict)

            if block_type in (31, 8) or has_table_field:
                # 尝试解析表格
                from doc_base.doc_to_bitable_core import (
                    _parse_table_block_hierarchical, _parse_table_block_flat,
                )
                rows = _parse_table_block_hierarchical(
                    blk, block_map, log_fn=log
                ) if _has_parse_table_hierarchical() else None
                if not rows or len(rows) < 2:
                    rows = _parse_table_block_flat(blk) if _has_parse_table_flat() else None

                if rows and len(rows) >= 2:
                    log(f"  ✅ 解析到『用例总览』section 下的表格："
                        f"{len(rows)} 行 x {len(rows[0])} 列")
                    for r in rows[:3]:
                        log(f"    行: {r}")
                    return rows

    # Step 3：找不到 heading 或 section 下无表格 → 用「最后一张表格」兜底
    log("  ℹ️  未在『用例总览』 section 找到表格，尝试使用文档中最后一张表格兜底")
    last_rows = None
    for idx, blk in enumerate(all_blocks):
        if not isinstance(blk, dict):
            continue
        block_type = blk.get("block_type") or blk.get("type")
        has_table_field = "table" in blk and isinstance(blk.get("table"), dict)
        if block_type not in (31, 8) and not has_table_field:
            continue
        from doc_base.doc_to_bitable_core import (
            _parse_table_block_hierarchical, _parse_table_block_flat,
        )
        rows = _parse_table_block_hierarchical(
            blk, block_map, log_fn=log
        ) if _has_parse_table_hierarchical() else None
        if not rows or len(rows) < 2:
            rows = _parse_table_block_flat(blk) if _has_parse_table_flat() else None
        if rows and len(rows) >= 2:
            last_rows = rows

    if last_rows:
        log(f"  ✅ 使用兜底策略，文档中共识别到 {len(last_rows)} 行表格内容")
        for r in last_rows[:3]:
            log(f"    行: {r}")
        return last_rows

    return None


def _safe_block_text(blk):
    """从 block 中取出纯文本（与 doc_to_bitable_core._block_text 相同逻辑但更容错）。"""
    if not isinstance(blk, dict):
        return ""
    # 先尝试 paragraph / heading 的 elements 结构
    for top_key in ("paragraph", "text"):
        inner = blk.get(top_key)
        if isinstance(inner, dict):
            elements = inner.get("elements") or []
            if isinstance(elements, list):
                parts = []
                for el in elements:
                    if isinstance(el, dict):
                        tr = el.get("text_run")
                        if isinstance(tr, dict) and isinstance(tr.get("content"), str):
                            parts.append(tr["content"])
                txt = "".join(parts).strip()
                if txt:
                    return txt
    # heading1 / heading2 / ...
    for hk in ("heading1", "heading2", "heading3", "heading4", "heading5", "heading6",
               "heading_1", "heading_2", "heading_3", "heading_4", "heading_5", "heading_6"):
        inner = blk.get(hk)
        if isinstance(inner, dict):
            elements = inner.get("elements") or []
            if isinstance(elements, list):
                parts = []
                for el in elements:
                    if isinstance(el, dict):
                        tr = el.get("text_run")
                        if isinstance(tr, dict) and isinstance(tr.get("content"), str):
                            parts.append(tr["content"])
                txt = "".join(parts).strip()
                if txt:
                    return txt
    # 直接 text 字段
    if isinstance(blk.get("text"), str) and blk["text"].strip():
        return blk["text"].strip()
    if isinstance(blk.get("content"), str) and blk["content"].strip():
        return blk["content"].strip()
    return ""


def _has_parse_table_hierarchical():
    try:
        from doc_base.doc_to_bitable_core import _parse_table_block_hierarchical
        return True
    except Exception:
        return False


def _has_parse_table_flat():
    try:
        from doc_base.doc_to_bitable_core import _parse_table_block_flat
        return True
    except Exception:
        return False


def _detect_key_field(field_names, records):
    """从『用例总览』表格中识别作为 key 的列名。
    优先：列名含 "用例"/"case"/"id"/"query"，其次：值以 SpecQuery_ 开头的列，最后：第一列非空。
    返回 (key_field_name, key_values)。
    """
    preferred_kw = ("用例", "case", "id", "query", "编号")
    if field_names:
        for kw in preferred_kw:
            for fn in field_names:
                if kw.lower() in str(fn).lower():
                    vals = [str(r.get(fn, "")).strip() for r in records]
                    non_empty = [v for v in vals if v]
                    if non_empty:
                        return fn, vals
    # 次选：值以 SpecQuery_ 开头
    if records:
        for fn in field_names:
            for r in records:
                v = str(r.get(fn, "")).strip()
                if v.startswith("SpecQuery_") or v.startswith("specquery_"):
                    vals = [str(r.get(fn, "")).strip() for r in records]
                    return fn, vals
    # 兜底：第一列非空
    if field_names:
        return field_names[0], [str(r.get(field_names[0], "")).strip() for r in records]
    return None, []


def _extract_error_reasons_other_mode(raw_content, field_names, records, log_fn=None):
    """
    **其他模式专用**：通读飞书云文档全文，提取「错误理由」下的内容。

    策略：
      1) 定位文档中所有「错误理由」/「错误原因」/「失败原因」/「Error Reason」关键词
         的段落（按行扫描，关键词不区分大小写）。
      2) 对每一个关键词段落，把该词之后的内容（同一行余下文本 + 后续若干行直到遇到
         下一个标题/表格/关键词/空行超过阈值）作为该条「错误理由」的正文。
      3) 尝试把错误理由关联到具体记录：
          - 如果错误理由的上下文（前后几行）中能识别出用例 ID
            （包含某个记录 key_field 的值，或包含 "SpecQuery_xxx"），
            则把该段错误理由归到对应 records[i]；
          - 否则作为「文档全局错误理由」累计。
      4) 最终每条记录的「错误理由」字段 = 已关联的错误理由段落（多行）
         + 如果没有任何关联则尝试填入全局错误理由。

    返回 (new_field_names, merged_records)
    """
    log = log_fn or (lambda msg: None)

    # 失败原因列名（最终会出现在 records 的字段里）
    FAIL_FIELD = "错误理由"

    if not raw_content or not records:
        log("  [错误理由] 无文档内容或无记录，跳过")
        new_field_names = list(field_names)
        if FAIL_FIELD not in new_field_names:
            new_field_names.append(FAIL_FIELD)
        merged = [dict(r) for r in records]
        for r in merged:
            r[FAIL_FIELD] = r.get(FAIL_FIELD, "")
        return new_field_names, merged

    # 先识别 key_field
    key_field, key_values = _detect_key_field(field_names, records)
    case_ids = [v for v in key_values if v] if key_values else []

    log(f"  [错误理由] key_field={key_field}, 有效 case_id 数={len(case_ids)}")

    # 关键词列表（小写匹配）
    KEYWORDS = ("错误理由", "错误原因", "失败原因", "error reason", "error:")

    # 按行扫描正文，找到关键词后收集后面的内容
    lines = raw_content.split("\n")

    # 先建立 {case_id: index} 的反向索引
    case_to_idx = {}
    if key_field:
        for i, r in enumerate(records):
            v = str(r.get(key_field, "")).strip()
            if v:
                case_to_idx[v] = i

    # 给每条记录预分配一个错误理由列表
    per_record_reasons = [[] for _ in records]
    global_reasons = []  # 无法关联到具体用例的错误理由

    # 停止收集的信号（行内容触发，用于截断元数据与大段 query）
    def _is_section_break(line):
        s = line.strip()
        if not s:
            return False
        # 标题行
        if s.startswith("#"):
            return True
        low = s.lower()
        # 另一个错误理由或 section 标题
        for stop_kw in ("错误理由", "错误原因", "失败原因", "error reason",
                         "test case", "testcase", "用例总览", "用例汇总",
                         "specquery_", "预期结果", "实际结果", "测试结果"):
            if stop_kw in low:
                return True
        # 元数据行（这些是"错误理由"之后的辅助信息，不属于错误理由正文）
        meta_prefixes = (
            "修改前 base:", "修改后 base:", "before base:", "after base:",
            "score:", "分数:", "result:", "结果:",
            "query", "之前轮次 query", "本轮 query", "user query",
        )
        for prefix in meta_prefixes:
            if low.startswith(prefix):
                return True
        # 以 _test_ 结尾或包含 _test_ 数字的纯用例 id 行（如 permission_test_002）
        import re as _re_inner
        if (("_test_" in low or "_spec_" in low)
                and len(low) < 80
                and _re_inner.match(r"^[a-z0-9_\-:：]+$", low)):
            return True
        # 表格分隔符
        if "|" in s and all(c in "|:- " for c in s):
            return True
        return False

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        low = stripped.lower()

        # 匹配当前行是否包含关键词
        matched_kw = None
        for kw in KEYWORDS:
            if kw in low:
                matched_kw = kw
                break

        if matched_kw is None:
            i += 1
            continue

        # 记录当前关键词前后的上下文（用于关联 case_id，先记录再做正文截断）
        context_window_start = max(0, i - 10)
        context_window_end = min(len(lines), i + 30)  # 放宽窗口，便于匹配到 case_id
        context_block = "\n".join(lines[context_window_start:context_window_end])

        # 收集关键词所在行的剩余内容
        # 例："错误理由：字段顺序不一致" → 取到":"后的全部
        first_extra = ""
        idx = low.find(matched_kw)
        if idx >= 0:
            tail = stripped[idx + len(matched_kw):]
            # 去掉开头可能的"："或":"或"-"或"|"
            tail = tail.lstrip("：:-| \t")
            if tail.strip():
                first_extra = tail.strip()

        # 继续读后续行（直到遇到 section break 或连续多行空行）
        collected = []
        if first_extra:
            collected.append(first_extra)

        empty_streak = 0
        j = i + 1
        while j < len(lines):
            l = lines[j].strip()
            if not l:
                empty_streak += 1
                if empty_streak >= 2:
                    break
                j += 1
                continue
            empty_streak = 0
            if _is_section_break(l):
                break
            # 去掉 Markdown 列表符号前缀
            cleaned = l.lstrip("-*• \t")
            cleaned = cleaned.rstrip("|")
            collected.append(cleaned)
            if len(collected) > 50:
                break
            j += 1

        reason_text = "\n".join(c for c in collected if c).strip()
        if not reason_text:
            # 没抓到内容，跳过
            i = j if j > i else i + 1
            continue

        # 关联到记录：优先从 context_window 中找 case_id
        assigned_idx = None
        for cid, ridx in case_to_idx.items():
            if cid and cid in context_block:
                assigned_idx = ridx
                break

        # 次选：从已收集的 reason_text 本身找 case_id
        if assigned_idx is None:
            for cid, ridx in case_to_idx.items():
                if cid and cid in reason_text:
                    assigned_idx = ridx
                    break

        # 再次选：匹配 SpecQuery_xxx 模式
        if assigned_idx is None:
            import re as _re
            m = _re.search(r"SpecQuery[_-]?[A-Za-z0-9_\-]+",
                            context_block + "\n" + reason_text, flags=_re.IGNORECASE)
            if m:
                found = m.group(0)
                for cid, ridx in case_to_idx.items():
                    if cid.lower() == found.lower() or found.lower() in cid.lower():
                        assigned_idx = ridx
                        break

        if assigned_idx is not None:
            per_record_reasons[assigned_idx].append(reason_text)
            log(f"  [错误理由] 记录 #{assigned_idx + 1} 新增 1 段错误理由 "
                f"({len(reason_text)} 字符)")
        else:
            global_reasons.append(reason_text)
            log(f"  [错误理由] 未找到对应用例 ID，作为全局错误理由 "
                f"({len(reason_text)} 字符)")

        i = j  # 跳到这段收集结束的位置

    # 把提取结果合并到 records
    new_field_names = list(field_names)
    if FAIL_FIELD not in new_field_names:
        new_field_names.append(FAIL_FIELD)

    merged_records = []
    for idx, rec in enumerate(records):
        new_rec = dict(rec)
        parts = list(per_record_reasons[idx])
        # 如果这条记录自己没找到，且全局有错误理由 → 把全局的填进来
        if not parts and global_reasons:
            parts = list(global_reasons)
        new_rec[FAIL_FIELD] = "\n\n---\n\n".join(parts) if parts else ""
        merged_records.append(new_rec)

    # 日志汇总
    with_reason = sum(1 for r in merged_records if r.get(FAIL_FIELD))
    log(f"  [错误理由] 完成：共 {len(merged_records)} 条记录，"
        f"{with_reason} 条有错误理由，全局收集 {len(global_reasons)} 段")
    for k, r in enumerate(merged_records[:5]):
        snippet = (r.get(FAIL_FIELD) or "")[:120]
        log(f"    记录 {k + 1} 错误理由: {snippet}")

    return new_field_names, merged_records


def _finalize_table_rows(rows, api_base, user_token, doc_token, log_fn=None):
    """把二维 rows 整理成 (field_names, records)，并：
      - 调用其他模式专用的错误理由提取函数（通读文档 → 找『错误理由』）
      - 最后做字段名映射
    """
    log = log_fn or (lambda msg: None)

    header = [str(c).strip() for c in rows[0]]

    # 去空列 + 列名去重
    keep_idx = [j for j, h in enumerate(header) if h]
    field_names = []
    seen = set()
    for j in keep_idx:
        base = header[j] or f"列{j + 1}"
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

    if not records:
        raise RuntimeError("解析出 0 条数据记录，请确认『用例总览』表格非空")

    # 其他模式：通读文档提取『错误理由』
    try:
        from doc_base.doc_to_bitable_core import _fetch_raw_content
        raw_content = _fetch_raw_content(api_base, user_token, doc_token, log_fn=log)
        if raw_content:
            log("--- 开始通读文档提取『错误理由』 ---")
            field_names, records = _extract_error_reasons_other_mode(
                raw_content, field_names, records, log_fn=log
            )
    except Exception as exc:
        log(f"  ⚠️  错误理由提取出错: {exc}（不影响表格数据写入）")

    # 最后做字段名映射
    try:
        from doc_base.doc_to_bitable_core import _apply_field_name_map
        field_names, records = _apply_field_name_map(field_names, records)
    except Exception as exc:
        log(f"  ⚠️  字段名映射出错: {exc}（不影响表格数据写入）")

    return field_names, records


def _run_create_new_table_other_mode(user_token, doc_input, new_table_name, log_fn=None):
    """
    方式 A（其他模式）：新建一个飞书多维表格并写入数据。
    与 Building 模式的 run_create_new_table 逻辑一致，区别只在于：
      - 使用 parse_overview_table_as_records 解析『用例总览』下的表格
    """
    log = log_fn or (lambda msg: None)

    from doc_base.doc_to_bitable_core import (
        extract_token_from_url, _detect_api_base, ensure_fields,
        append_records, _make_base_url,
    )

    doc_token = extract_token_from_url(doc_input)
    api_base = _detect_api_base(doc_input)

    field_names, records = parse_overview_table_as_records(
        api_base, user_token, doc_token, log_fn=log
    )
    if not records:
        raise RuntimeError("云文档中未解析出任何数据")

    # Step 1: 新建一个多维表格应用
    log(f"创建全新多维表格 '{new_table_name}'...")
    from doc_base.doc_to_bitable_core import _headers
    headers = _headers(user_token)
    url = f"{api_base}/open-apis/bitable/v1/apps"
    import requests, json
    resp = requests.post(url, headers=headers, json={"name": new_table_name}, timeout=30)
    data = resp.json().get("data", {})
    app = data.get("app") if isinstance(data.get("app"), dict) else data
    target_app_token = app.get("app_token")
    default_table_id = app.get("table_id")
    if not target_app_token:
        raise RuntimeError(f"新建多维表格未返回 app_token，响应: {data}")
    log(f"✅ 多维表格创建成功 app_token={target_app_token}")

    # Step 2: 补建字段到默认表
    if default_table_id:
        target_table_id = default_table_id
        log(f"使用默认数据表 table_id={target_table_id}，补建字段...")
        ensure_fields(api_base, user_token, target_app_token, target_table_id,
                       field_names, log_fn=log)
    else:
        from doc_base.doc_to_bitable_core import _create_table
        target_table_id = _create_table(api_base, user_token, target_app_token,
                                         new_table_name, field_names)
        log(f"新建数据表成功 table_id={target_table_id}")

    # Step 3: 写入记录
    written = append_records(api_base, user_token, target_app_token, target_table_id,
                              records, field_names, batch_size=50, log_fn=log)
    log(f"✅ 已新建多维表格并写入 {written} 条记录")
    return written, _make_base_url(api_base, target_app_token, target_table_id)


def parse_overview_table_as_records(api_base, user_token, doc_token, log_fn=None):
    """**其他模式主解析函数**。返回 (field_names, records)。

    与 Building 模式的区别：
      - Building 模式：默认使用文档中的**第一张**表格
      - 其他模式：优先定位『用例总览』标题 section 下的**特定表格**，
        找不到则回退到使用文档中**最后一张**表格兜底
    """
    log = log_fn or (lambda msg: None)

    log(f"读取云文档 blocks（API: {api_base}, doc_token: {doc_token}）")
    from doc_base.doc_to_bitable_core import _fetch_doc_blocks
    all_blocks = _fetch_doc_blocks(api_base, user_token, doc_token, log_fn=log)
    log(f"共读取 {len(all_blocks)} 个 block")

    log("--- 定位『用例总览』section 下的表格 ---")
    rows = _find_overview_table_blocks(all_blocks, log_fn=log)
    if rows and len(rows) >= 2:
        log("✅ 成功定位到『用例总览』下的表格")
        field_names, records = _finalize_table_rows(
            rows, api_base, user_token, doc_token, log_fn=log
        )
        log(f"解析完成: {len(field_names)} 列, {len(records)} 条记录")
        log(f"字段: {', '.join(field_names)}")
        for i, rec in enumerate(records[:3]):
            log(f"  记录 {i + 1}: {rec}")
        return field_names, records

    raise RuntimeError(
        "未能在『用例总览』 section 下找到有效表格。\n"
        "请确认：\n"
        "  1) 云文档中存在包含『用例总览』（或相近标题）的标题行\n"
        "  2) 该标题下方紧跟着一个真正的「表格」(不是纯文本)\n"
        "  3) 表格至少有表头行 + 1 条数据行"
    )

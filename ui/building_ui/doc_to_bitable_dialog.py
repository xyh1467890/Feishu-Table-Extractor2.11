"""
飞书云文档 → 多维表格 转换对话框

UI 层

两步操作：
  1) 模式 B：把云文档的「表格」内容追加到已有数据表（推荐）
  2) 模式 A：在已有 base 下新建一张数据表并写入

UI 改为「先预览解析结果，用户确认后再写入」的安全流程。
"""
import sys
import os
import datetime

# 添加上级目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)
sys.path.insert(0, root_dir)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QGroupBox, QTextEdit, QDialog, QRadioButton,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from ui.building_ui.doc_to_bitable_other_panel import DocToBitableOtherPanel
from doc_base.doc_to_bitable_core import (
    run_append_to_table,
    run_create_new_table,
    parse_doc_as_records,
    extract_bitable_info_from_url,
    extract_token_from_url,
    _detect_api_base,
    ensure_fields,
)


class WorkerThread(QThread):
    """后台工作线程——执行耗时操作（解析文档、写入表格）"""
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
        """预览解析任务"""
        api_base = self.kwargs.get('api_base')
        user_token = self.kwargs.get('user_token')
        doc_token = self.kwargs.get('doc_token')

        def log_fn(msg):
            self.log_message.emit(msg)

        from doc_base.doc_to_bitable_core import parse_doc_as_records
        field_names, records = parse_doc_as_records(api_base, user_token, doc_token, log_fn=log_fn)
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
            # 方式 A：创建全新多维表格 —— 不再需要 target_app_token
            from doc_base.doc_to_bitable_core import run_create_new_table
            doc_input = self.kwargs.get('doc_input')
            new_table_name = self.kwargs.get('new_table_name')
            written, result_url = run_create_new_table(
                user_token, doc_input, new_table_name, log_fn=log_fn
            )
            self.finished.emit(True, (written, result_url), "")


class DocToBitableDialog(QDialog):
    """飞书云文档 → 多维表格对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("飞书云文档 → 多维表格")
        self.setMinimumSize(960, 980)
        self.is_processing = False
        self._parsed_cache = None  # 存放解析后的 (field_names, records, mode_info)
        self.mode_type = "building"  # 默认 building 模式
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 12, 32, 32)  # 顶部边距从32改小到12
        layout.setSpacing(12)  # Section 之间的间距也略缩小

        self.setStyleSheet("""
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
                font-size: 14px;
                color: #1f2937;
                background-color: #f8fafc;
            }
        """)

        # ========== 新增：模式选择 Section ==========
        mode_group = QGroupBox("🔧 模式选择")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setSpacing(24)
        mode_layout.setContentsMargins(20, 16, 20, 16)

        self.building_radio = QRadioButton("Building 模式")
        self.building_radio.setChecked(True)
        self.building_radio.setStyleSheet("QRadioButton { font-weight: 600; font-size: 14px; }")
        self.building_radio.toggled.connect(lambda checked: self._on_mode_changed("building") if checked else None)
        mode_layout.addWidget(self.building_radio)

        self.other_radio = QRadioButton("其他模式")
        self.other_radio.setStyleSheet("QRadioButton { font-weight: 600; font-size: 14px; color: #64748b; }")
        self.other_radio.toggled.connect(lambda checked: self._on_mode_changed("other") if checked else None)
        mode_layout.addWidget(self.other_radio)

        mode_layout.addStretch()
        layout.addWidget(mode_group)

        # ========== Building 模式内容容器（所有原来的 Section 都放这里） ==========
        self.building_container = QWidget()
        building_layout = QVBoxLayout(self.building_container)
        building_layout.setContentsMargins(0, 0, 0, 0)
        building_layout.setSpacing(16)

        # Section 1: 输入信息
        input_group = QGroupBox("① 输入信息")
        ig = QVBoxLayout(input_group)
        ig.setSpacing(10)

        token_label = QLabel(
            '<a href="https://open.larksuite.com/api-explorer/cli_a9bec8ebdc78dbcc?apiName=get&project=bitable&resource=app&version=v1" '
            'style="color:#2563eb; text-decoration:underline;">User Access Token</a>'
        )
        token_label.setStyleSheet("font-weight:600;")
        token_label.setOpenExternalLinks(True)
        ig.addWidget(token_label)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("u-xxxxxxxxxxxxxxxxxxxx")
        ig.addWidget(self.token_input)

        doc_label = QLabel("飞书云文档链接（或 doc_token）")
        doc_label.setStyleSheet("font-weight:600;")
        ig.addWidget(doc_label)
        self.doc_input = QLineEdit()
        self.doc_input.setPlaceholderText("https://bytedance.larkoffice.com/docx/XXXXX  或直接粘贴 doc_token")
        ig.addWidget(self.doc_input)

        building_layout.addWidget(input_group)

        # Section 2: 输出方式（二选一）
        target_group = QGroupBox("② 输出方式（二选一）")
        tg = QVBoxLayout(target_group)
        tg.setSpacing(10)

        # 方式 A：新建多维表格
        a_label = QLabel("A. 新建一个全新的飞书多维表格")
        a_label.setStyleSheet("font-weight:600;")
        tg.addWidget(a_label)
        a_row = QHBoxLayout()
        self.a_name_input = QLineEdit()
        self.a_name_input.setPlaceholderText("新多维表格名（可选，留空则自动生成）")
        a_row.addWidget(self.a_name_input, stretch=1)
        tg.addLayout(a_row)

        # 分隔
        sep = QLabel("— 或 —")
        sep.setStyleSheet("color:#94a3b8;")
        sep.setAlignment(Qt.AlignCenter)
        tg.addWidget(sep)

        # 方式 B：追加到已有数据表
        b_label = QLabel("B. 直接追加到已有数据表（推荐）")
        b_label.setStyleSheet("font-weight:600;")
        tg.addWidget(b_label)
        self.existing_bitable_input = QLineEdit()
        self.existing_bitable_input.setPlaceholderText(
            "粘贴带 table 参数的链接，如：https://bytedance.larkoffice.com/base/XXX?table=YYY")
        tg.addWidget(self.existing_bitable_input)

        building_layout.addWidget(target_group)

        # Section 2.5: 写入方式（单一模式：按行号顺序填充新列）
        write_mode_group = QGroupBox("③ 写入方式（模式 B 时有效）")
        wg = QVBoxLayout(write_mode_group)
        wg.setSpacing(10)

        info_label = QLabel(
            "✅ 将按行号顺序写入：云文档第 1 条 → 目标表第 1 行，依次写入新列值，不改变其他列。"
        )
        info_label.setStyleSheet("color: #1d4ed8; font-weight: 600; font-size: 13px;")
        wg.addWidget(info_label)

        building_layout.addWidget(write_mode_group)

        # Section 3: 按钮区域（预览 + 确认写）
        btn_section = QWidget()
        bs = QHBoxLayout(btn_section)
        bs.setContentsMargins(0, 0, 0, 0)
        bs.addStretch()

        self.preview_btn = QPushButton("🔍 预览解析结果")
        self.preview_btn.setMinimumHeight(40)
        self.preview_btn.setMinimumWidth(160)
        self.preview_btn.clicked.connect(self.on_preview)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
                color: white; border-radius: 8px; padding: 8px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3b82f6, stop:1 #2563eb);
            }
        """)
        bs.addWidget(self.preview_btn)

        self.run_btn = QPushButton("▶ 确认并写入")
        self.run_btn.setMinimumHeight(40)
        self.run_btn.setMinimumWidth(160)
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self.on_run)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669);
                color: white; border-radius: 8px; padding: 8px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton:disabled { background: #94a3b8; color: #cbd5e1;
            }
        """)
        bs.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.clicked.connect(self.close)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db; border-radius: 8px; padding: 8px 20px; font-weight: 600;
            }
            QPushButton:hover { background-color: #f3f4f6; }
        """)
        bs.addWidget(self.cancel_btn)

        building_layout.addWidget(btn_section)

        # Section 4: 日志
        log_group = QGroupBox("③ 执行日志 / 预览结果")
        lg = QVBoxLayout(log_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 13px;
            }
        """)
        self.result_text.setMinimumHeight(50)
        lg.addWidget(self.result_text)
        building_layout.addWidget(log_group, stretch=1)

        # 把 Building 模式容器加入主 layout
        layout.addWidget(self.building_container, stretch=1)

        # ========== 其他模式容器（引用独立 UI 面板） ==========
        self.other_panel = DocToBitableOtherPanel()
        layout.addWidget(self.other_panel, stretch=1)
        self.other_panel.setVisible(False)

    def append_log(self, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.result_text.append(f"[{ts}] {text}")
        sb = self.result_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---------------------------------------------------------------
    # 模式切换：building / other
    # ---------------------------------------------------------------
    def _on_mode_changed(self, mode):
        self.mode_type = mode
        if mode == "building":
            self.building_container.setVisible(True)
            self.other_panel.setVisible(False)
        else:
            self.building_container.setVisible(False)
            self.other_panel.setVisible(True)

    # ---------------------------------------------------------------
    # 预览：只解析不写入
    # ---------------------------------------------------------------
    def on_preview(self):
        if self.is_processing:
            return

        user_token = self.token_input.text().strip()
        doc_input_text = self.doc_input.text().strip()
        existing_bitable = self.existing_bitable_input.text().strip()
        a_name = self.a_name_input.text().strip()

        if not user_token:
            QMessageBox.warning(self, "提示", "请输入 User Access Token"); return
        if not doc_input_text:
            QMessageBox.warning(self, "提示", "请输入飞书云文档链接或 doc_token"); return

        # 判断输出模式
        mode = None  # "B" 追加 / "A" 新建
        mode_info = None
        if existing_bitable:
            api_base, app_token, table_id = extract_bitable_info_from_url(existing_bitable)
            if not app_token:
                QMessageBox.warning(self, "提示", "B 选项中的链接无法解析出 app_token"); return
            mode_info = ("B", api_base, app_token, table_id)
            mode = "B"
        else:
            # 方式 A：新建一个全新的多维表格（不再需要填目标 base）
            api_base = _detect_api_base(doc_input_text)
            if not a_name:
                from datetime import datetime as _dt
                a_name = f"导入_{_dt.now().strftime('%Y%m%d_%H%M')}"
            mode_info = ("A", api_base, a_name, None)
            mode = "A"

        # 准备工作：禁用按钮、清空日志
        self.is_processing = True
        self.preview_btn.setEnabled(False)
        self.run_btn.setEnabled(False)
        self.result_text.clear()
        self.append_log("开始解析云文档...")

        # 创建后台线程执行解析
        doc_token = extract_token_from_url(doc_input_text)
        self.worker = WorkerThread(
            task_type='preview',
            api_base=api_base,
            user_token=user_token,
            doc_token=doc_token,
            mode_info=mode_info,
        )
        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(lambda success, data, err: self._on_preview_finished(success, data, err, mode_info))
        self.worker.start()

    def _on_preview_finished(self, success, data, error_msg, mode_info):
        """预览完成后的回调"""
        try:
            if success and data:
                field_names, records = data
                mode = mode_info[0]

                self.append_log("")
                self.append_log(f"======== 预览 ========")
                self.append_log(f"解析结果：")
                self.append_log(f"  字段数: {len(field_names)}")
                self.append_log(f"  记录数: {len(records)}")
                self.append_log(f"  字段: {', '.join(field_names)}")
                self.append_log("")

                if records:
                    self.append_log("前 5 条记录预览：")
                    for i, rec in enumerate(records[:5]):
                        self.append_log(f"  第 {i+1} 条: {rec}")

                # 如果是模式 B：额外展示目标表字段对比（便于确认匹配字段）
                if mode == "B" and mode_info[3]:  # 有 table_id
                    self.append_log("")
                    self.append_log(f"--- 目标数据表字段对比 ---")
                    try:
                        from doc_base.doc_to_bitable_core import list_bitable_fields
                        api_base = mode_info[1]
                        user_token = self.token_input.text().strip()
                        target_fields = list_bitable_fields(
                            api_base, user_token, mode_info[2], mode_info[3], log_fn=self.append_log
                        )
                        target_names = []
                        for f in target_fields:
                            if isinstance(f, dict) and f.get("field_name"):
                                target_names.append(f["field_name"])

                        self.append_log("")
                        self.append_log("字段匹配检查：")
                        matched = []
                        unmatched = []
                        for fn in field_names:
                            hit = None
                            for tn in target_names:
                                if isinstance(tn, str) and isinstance(fn, str) and tn.strip().lower() == fn.strip().lower():
                                    hit = tn
                                    break
                            if hit:
                                matched.append(fn)
                            else:
                                unmatched.append(fn)
                        if matched:
                            self.append_log(f"  ✅ 已存在字段：{', '.join(matched)}")
                        if unmatched:
                            self.append_log(f"  ➕ 新建字段（将自动创建为文本类型）：{', '.join(unmatched)}")
                        self.append_log("")

                        # 智能提示匹配字段
                        if self.key_field_input.text().strip() == "" and target_names:
                            suggested = None
                            for fn in field_names:
                                if any(k in str(fn) for k in ("ID", "id", "编号", "失败项", "名称")):
                                    suggested = fn
                                    break
                            if suggested is None and field_names:
                                suggested = field_names[0]
                            self.append_log(f"💡 建议：将「{suggested}」填到下方【匹配字段名】中。")
                            self.key_field_input.setText(suggested)
                    except Exception as fe:
                        self.append_log(f"  (读取目标表字段失败，不影响写入：{fe})")

                self._parsed_cache = (field_names, records, mode_info)
                self.run_btn.setEnabled(True)
                self.append_log("")
                self.append_log("✅ 预览完成。如果预览正确，请点击【确认并写入。")

                QMessageBox.information(
                    self, "预览成功",
                    f"解析完成：{len(field_names)} 个字段，{len(records)} 条记录。\n\n字段：{', '.join(field_names)}\n\n请检查日志区域查看详细解析结果。如果没问题请点击【确认并写入。"
                )
            else:
                self.append_log(f"❌ 错误: {error_msg}")
                QMessageBox.critical(self, "解析失败", error_msg)
        finally:
            self.is_processing = False
            self.preview_btn.setEnabled(True)

    # ---------------------------------------------------------------
    # 执行写入（在预览通过后才会调用这里
    # ---------------------------------------------------------------
    def on_run(self):
        if self.is_processing or self._parsed_cache is None:
            if self._parsed_cache is None:
                QMessageBox.warning(self, "提示", "请先点击【预览解析结果】"); return
            return

        field_names, records, mode_info = self._parsed_cache
        mode = mode_info[0]  # "A" 或 "B"

        # 禁用按钮
        self.is_processing = True
        self.run_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)

        user_token = self.token_input.text().strip()

        # 创建后台线程执行写入
        worker_kwargs = {
            'task_type': 'write',
            'user_token': user_token,
            'mode': mode,
        }
        if mode == 'A':
            # 方式 A：创建全新多维表格 —— 只需要 doc_input 和 new_table_name
            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M')
            new_table_name = self.a_name_input.text().strip() or f"导入_{ts}"
            worker_kwargs['doc_input'] = self.doc_input.text().strip()
            worker_kwargs['new_table_name'] = new_table_name
        else:
            # 方式 B：追加到已有数据表 —— 使用 api_base/app_token/table_id，且过滤 ID 字段
            api_base = mode_info[1]
            app_token = mode_info[2]
            table_id = mode_info[3]
            fields_to_write = [fn for fn in field_names if fn != "ID"]
            records_to_write = [
                {k: v for k, v in rec.items() if k != "ID"}
                for rec in records
            ]
            if "ID" in field_names:
                self.append_log(f"提示：已跳过 ID 字段，将写入 {len(fields_to_write)} 个字段")
            worker_kwargs['api_base'] = api_base
            worker_kwargs['app_token'] = app_token
            worker_kwargs['table_id'] = table_id
            worker_kwargs['field_names'] = fields_to_write
            worker_kwargs['records'] = records_to_write

        self.worker = WorkerThread(**worker_kwargs)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(lambda success, data, err: self._on_run_finished(success, data, err, mode))
        self.worker.start()

    def _on_run_finished(self, success, data, error_msg, mode):
        """写入完成后的回调"""
        try:
            if success and data:
                if mode == 'B':
                    updated, created, result_url = data
                    self.append_log(f"✅ 完成：已更新 {updated} 条现有记录的新列值；追加 {created} 条新记录")
                    QMessageBox.information(
                        self, "完成",
                        f"✅ 完成：\n  • 更新 {updated} 条记录的新列值\n  • 追加 {created} 条新记录\n\n链接：{result_url}"
                    )
                else:
                    written, result_url = data
                    QMessageBox.information(self, "完成", f"✅ 已新建数据表并写入 {written} 条记录\n\n链接：{result_url}")
            else:
                self.append_log(f"❌ 错误: {error_msg}")
                QMessageBox.critical(self, "失败", error_msg)
        finally:
            self.is_processing = False
            self.run_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)

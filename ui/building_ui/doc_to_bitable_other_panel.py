"""
飞书云文档 → 多维表格 · 其他模式 UI 面板

UI 结构、样式与 Building 模式保持一致。
业务逻辑通过 building_spec.doc_to_bitable_other_spec 中封装的
DocToBitableOtherLogic 执行。
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QTextEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from building_spec.doc_to_bitable_other_spec import DocToBitableOtherLogic


class DocToBitableOtherPanel(QWidget):
    """其他模式面板 —— UI 结构与 Building 模式保持一致。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 状态变量（与 Building 模式 dialog 保持一致的命名）
        self.is_processing = False
        self._parsed_cache = None  # (field_names, records, mode_info)
        self.init_ui()
        self._init_logic()

    def _init_logic(self):
        """初始化业务逻辑控制器"""
        self.logic = DocToBitableOtherLogic(self)
        # 绑定按钮事件
        self.preview_btn.clicked.connect(self.logic.on_preview)
        self.run_btn.clicked.connect(self.logic.on_run)
        self.cancel_btn.clicked.connect(self._on_cancel_click)

    def _on_cancel_click(self):
        """取消按钮：清空输入 + 清空日志 + 重置写入按钮"""
        if self.is_processing:
            return
        self.token_input.clear()
        self.doc_input.clear()
        self.a_name_input.clear()
        self.existing_bitable_input.clear()
        self.result_text.clear()
        self._parsed_cache = None
        self.run_btn.setEnabled(False)

    # ---------------------------------------------------------------
    # UI 构建（与 Building 模式完全一致）
    # ---------------------------------------------------------------
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ---------- Section 1: 输入信息 ----------
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

        layout.addWidget(input_group)

        # ---------- Section 2: 输出方式（二选一） ----------
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

        layout.addWidget(target_group)

        # ---------- Section 3: 写入方式 ----------
        write_mode_group = QGroupBox("③ 写入方式（模式 B 时有效）")
        wg = QVBoxLayout(write_mode_group)
        wg.setSpacing(10)

        info_label = QLabel(
            "✅ 将按行号顺序写入：云文档第 1 条 → 目标表第 1 行，依次写入新列值，不改变其他列。"
        )
        info_label.setStyleSheet("color: #1d4ed8; font-weight: 600; font-size: 13px;")
        wg.addWidget(info_label)

        layout.addWidget(write_mode_group)

        # ---------- Section 4: 按钮区域 ----------
        btn_section = QWidget()
        bs = QHBoxLayout(btn_section)
        bs.setContentsMargins(0, 0, 0, 0)
        bs.addStretch()

        self.preview_btn = QPushButton("🔍 预览解析结果")
        self.preview_btn.setMinimumHeight(40)
        self.preview_btn.setMinimumWidth(160)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
                color: white; border-radius: 8px; padding: 8px 20px; font-weight: 600;
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
        self.run_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669);
                color: white; border-radius: 8px; padding: 8px 20px; font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton:disabled {
                background: #94a3b8; color: #cbd5e1;
            }
        """)
        bs.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff; color: #374151; border: 1px solid #d1d5db;
                border-radius: 8px; padding: 8px 20px; font-weight: 600;
            }
            QPushButton:hover { background-color: #f3f4f6; }
        """)
        bs.addWidget(self.cancel_btn)

        layout.addWidget(btn_section)

        # ---------- Section 5: 日志 ----------
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
        layout.addWidget(log_group, stretch=1)

    # ---------------------------------------------------------------
    # 便捷方法（占位，供未来业务逻辑使用）
    # ---------------------------------------------------------------
    def append_log(self, text):
        """向日志区追加一行文本。"""
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.result_text.append(f"[{ts}] {text}")
        sb = self.result_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear_log(self):
        self.result_text.clear()

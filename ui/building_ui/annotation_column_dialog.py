"""
生成标注列对话框 - UI 层

业务逻辑统一放在 building_spec/annotation_column_spec.py 中。

用户操作流程：
  1. 选择模式（小白/Lite / Standard / Pro）
  2. 输入 User Access Token + 目标 Bitable 链接（含 ?table=xxx）
  3. 点击【预览目标表】验证连接并展示将要写入的字段和记录数
  4. 点击【确认并写入】调用业务逻辑完成追加写入
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
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from doc_base.doc_to_bitable_core import extract_bitable_info_from_url
from building_spec.annotation_column_spec import (
    AnnotationColumnWorker,
    MODE_DISPLAY,
)


class AnnotationColumnDialog(QDialog):
    """生成标注列对话框（UI 层，业务逻辑由 building_spec 处理）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("生成标注列")
        self.setMinimumSize(960, 900)
        self.is_processing = False
        self._parsed_cache = None     # 预览结果缓存
        self.mode_type = "lite"       # 默认小白/Lite 模式
        self.init_ui()

    # ---------------------------------------------------------------
    # UI 构建
    # ---------------------------------------------------------------
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 12, 32, 32)
        layout.setSpacing(12)

        self.setStyleSheet("""
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
                font-size: 14px;
                color: #1f2937;
                background-color: #f8fafc;
            }
        """)

        # ========== 模式选择 Section ==========
        mode_group = QGroupBox("🔧 模式选择")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setSpacing(24)
        mode_layout.setContentsMargins(20, 16, 20, 16)

        self.lite_radio = QRadioButton("小白/Lite 模式")
        self.lite_radio.setChecked(True)
        self.lite_radio.setStyleSheet("QRadioButton { font-weight: 600; font-size: 14px; }")
        self.lite_radio.toggled.connect(lambda checked: self._on_mode_changed("lite") if checked else None)
        mode_layout.addWidget(self.lite_radio)

        self.standard_radio = QRadioButton("Standard 模式")
        self.standard_radio.setStyleSheet("QRadioButton { font-weight: 600; font-size: 14px; }")
        self.standard_radio.toggled.connect(lambda checked: self._on_mode_changed("standard") if checked else None)
        mode_layout.addWidget(self.standard_radio)

        self.pro_radio = QRadioButton("Pro 模式")
        self.pro_radio.setStyleSheet("QRadioButton { font-weight: 600; font-size: 14px; }")
        self.pro_radio.toggled.connect(lambda checked: self._on_mode_changed("pro") if checked else None)
        mode_layout.addWidget(self.pro_radio)

        mode_layout.addStretch()
        layout.addWidget(mode_group)

        # ========== 主内容容器 ==========
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

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

        main_layout.addWidget(input_group)

        # Section 2: 输出方式
        target_group = QGroupBox("② 输出方式")
        tg = QVBoxLayout(target_group)
        tg.setSpacing(10)

        b_label = QLabel("B. 直接追加到已有数据表")
        b_label.setStyleSheet("font-weight:600;")
        tg.addWidget(b_label)
        self.existing_bitable_input = QLineEdit()
        self.existing_bitable_input.setPlaceholderText(
            "粘贴带 table 参数的链接，如：https://bytedance.larkoffice.com/base/XXX?table=YYY"
        )
        tg.addWidget(self.existing_bitable_input)

        main_layout.addWidget(target_group)

        # Section 3: 按钮区
        btn_section = QWidget()
        bs = QHBoxLayout(btn_section)
        bs.setContentsMargins(0, 0, 0, 0)
        bs.addStretch()

        self.preview_btn = QPushButton("🔍 预览将追加的列")
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

        self.run_btn = QPushButton("▶ 确认并追加列")
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
            QPushButton:disabled { background: #94a3b8; color: #cbd5e1; }
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

        main_layout.addWidget(btn_section)

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
        main_layout.addWidget(log_group, stretch=1)

        layout.addWidget(self.main_container, stretch=1)

    # ---------------------------------------------------------------
    # 辅助：追加日志
    # ---------------------------------------------------------------
    def append_log(self, text):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.result_text.append(f"[{ts}] {text}")
        sb = self.result_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ---------------------------------------------------------------
    # 模式切换
    # ---------------------------------------------------------------
    def _on_mode_changed(self, mode):
        self.mode_type = mode
        self.append_log(f"模式切换为：{MODE_DISPLAY.get(mode, mode)}")
        # 模式切换后，缓存的预览结果已无效
        self._parsed_cache = None
        self.run_btn.setEnabled(False)

    # ---------------------------------------------------------------
    # 预览：查询配置表 + 读取模板数据
    # ---------------------------------------------------------------
    def on_preview(self):
        if self.is_processing:
            return

        user_token = self.token_input.text().strip()
        existing_bitable = self.existing_bitable_input.text().strip()

        if not user_token:
            QMessageBox.warning(self, "提示", "请输入 User Access Token"); return
        if not existing_bitable:
            QMessageBox.warning(self, "提示", "请输入目标 Bitable 链接（含 table 参数）"); return

        # 解析目标 Bitable
        api_base, app_token, table_id = extract_bitable_info_from_url(existing_bitable)
        if not app_token or not table_id:
            QMessageBox.warning(self, "提示",
                "无法从链接解析出 app_token 和 table_id。请粘贴带 ?table= 参数的完整链接。"); return

        # 准备工作：禁用按钮、清空日志
        self.is_processing = True
        self.preview_btn.setEnabled(False)
        self.run_btn.setEnabled(False)
        self.result_text.clear()
        self.append_log("开始查询配置表并预览...")

        # 调用后台线程（逻辑在 building_spec 中）
        self.worker = AnnotationColumnWorker(
            task_type='preview',
            user_token=user_token,
            mode=self.mode_type,
            target_api_base=api_base,
            target_app_token=app_token,
            target_table_id=table_id,
        )
        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(self._on_preview_finished)
        self.worker.start()

    def _on_preview_finished(self, success, result, error_msg):
        """预览完成回调。"""
        try:
            if success and result:
                template_table_name = result.get("template_table_name", "未知")
                field_names = result.get("field_names", [])
                field_types = result.get("field_types", [])

                self.append_log("")
                self.append_log(f"======== 预览结果 ========")
                self.append_log(f"模板表: {template_table_name}")
                self.append_log(f"将追加到目标表的字段 ({len(field_names)} 个):")
                for i, fn in enumerate(field_names):
                    ftype = field_types[i] if i < len(field_types) else 1
                    self.append_log(f"  {i+1:2d}. {fn}  (type={ftype})")
                self.append_log("")

                self._parsed_cache = result  # 缓存给写入用
                self.run_btn.setEnabled(True)
                self.append_log(f"✅ 预览完成。确认后点击【确认并追加列】。")

                QMessageBox.information(
                    self, "预览成功",
                    f"模板表: {template_table_name}\n"
                    f"将追加 {len(field_names)} 个字段到目标表。\n\n"
                    f"字段列表:\n" +
                    "\n".join([f"  {i+1}. {fn}" for i, fn in enumerate(field_names)]) +
                    "\n\n确认后点击【确认并追加列】。"
                )
            else:
                self.append_log(f"❌ 预览失败: {error_msg}")
                QMessageBox.critical(self, "预览失败", error_msg)
        finally:
            self.is_processing = False
            self.preview_btn.setEnabled(True)

    # ---------------------------------------------------------------
    # 写入：在目标表中追加列
    # ---------------------------------------------------------------
    def on_run(self):
        if self.is_processing or self._parsed_cache is None:
            if self._parsed_cache is None:
                QMessageBox.warning(self, "提示", "请先点击【预览将追加的列】"); return
            return

        # 禁用按钮
        self.is_processing = True
        self.run_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)

        user_token = self.token_input.text().strip()
        field_names = self._parsed_cache.get("field_names", [])
        field_types = self._parsed_cache.get("field_types", [])
        field_configs = self._parsed_cache.get("field_configs", [])
        target_api_base = self._parsed_cache.get("target_api_base")
        target_app_token = self._parsed_cache.get("target_app_token")
        target_table_id = self._parsed_cache.get("target_table_id")

        self.append_log(f"开始在目标表中追加列: {target_app_token} / {target_table_id}")

        # 调用后台线程执行
        self.worker = AnnotationColumnWorker(
            task_type='write',
            user_token=user_token,
            field_names=field_names,
            field_types=field_types,
            field_configs=field_configs,
            target_api_base=target_api_base,
            target_app_token=target_app_token,
            target_table_id=target_table_id,
        )
        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(self._on_run_finished)
        self.worker.start()

    def _on_run_finished(self, success, data, error_msg):
        """写入完成回调。"""
        try:
            if success and data:
                skipped, created = data
                self.append_log(f"✅ 完成：跳过已有 {skipped} 个字段，新增 {created} 个字段")
                QMessageBox.information(
                    self, "完成",
                    f"✅ 完成：\n"
                    f"  • 跳过已有字段 {skipped} 个\n"
                    f"  • 新增字段 {created} 个\n\n"
                    f"请打开目标多维表格查看新增的列。"
                )
            else:
                self.append_log(f"❌ 失败: {error_msg}")
                QMessageBox.critical(self, "失败", error_msg)
        finally:
            self.is_processing = False
            self.run_btn.setEnabled(True)
            self.preview_btn.setEnabled(True)

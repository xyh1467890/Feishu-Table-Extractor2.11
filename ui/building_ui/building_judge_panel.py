"""
Building 机评模块
"""
import sys
import os
# 添加上级目录到路径，这样可以导入 config 和 building_spec
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)
sys.path.insert(0, root_dir)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QMessageBox, QComboBox, QGroupBox, QTextEdit, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from .batch_judge_dialog import BatchJudgeDialog
from .doc_to_bitable_dialog import DocToBitableDialog
from .annotation_column_dialog import AnnotationColumnDialog
from .dashboard_judge_panel import DashboardJudgePanel
from .workflow_judge_panel import WorkflowJudgePanel
from .block_judge_panel import BlockJudgePanel
from .table_judge_panel import TableJudgePanel
from .permission_judge_panel import PermissionJudgePanel
from building_spec.single_judge import SingleJudge
from config.settings import get_judge_api_key, set_judge_api_key


class BuildingJudgePanel(QWidget):
    """Building 机评面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setObjectName("module_panel")
        
        self.single_judge = SingleJudge()
        self.init_ui()
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 15)
        layout.setSpacing(15)
        
        self.setStyleSheet("""
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
                font-size: 14px;
                color: #1f2937;
                background-color: #f8fafc;
            }
        """)
        
        # --- 配置区域 ---
        config_section = self._create_config_section()
        layout.addWidget(config_section)
        
        # --- 面板切换区域 ---
        self.panel_stack = QStackedWidget()
        layout.addWidget(self.panel_stack, stretch=1)
        
        # Building 专用面板
        self.building_panel = self._create_building_panel()
        self.panel_stack.addWidget(self.building_panel)
        
        # Permission 专用面板
        self.permission_panel = PermissionJudgePanel(self)
        self.panel_stack.addWidget(self.permission_panel)
        
        # Table 专用面板
        self.table_panel = TableJudgePanel(self)
        self.panel_stack.addWidget(self.table_panel)
        
        # Dashboard 专用面板
        self.dashboard_panel = DashboardJudgePanel(self)
        self.panel_stack.addWidget(self.dashboard_panel)
        
        # Workflow 专用面板
        self.workflow_panel = WorkflowJudgePanel(self)
        self.panel_stack.addWidget(self.workflow_panel)
        
        # Block 专用面板
        self.block_panel = BlockJudgePanel(self)
        self.panel_stack.addWidget(self.block_panel)
        
        # --- 按钮区域 ---
        btn_section = self._create_button_section()
        layout.addWidget(btn_section)
    
    def _create_config_section(self):
        """创建配置区域"""
        group = QGroupBox("⚙️ 配置")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 15px;
                color: #1f2937;
                border: none;
                border-radius: 10px;
                margin-top: 2px;
                padding-top: 20px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 18px;
                padding: 0 10px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 28, 20, 22)
        
        row1 = QHBoxLayout()
        
        # --- Agent 类型 ---
        self.agent_widget = QWidget()
        self.agent_widget.setStyleSheet("background-color: #ffffff;")
        agent_layout = QVBoxLayout(self.agent_widget)
        agent_layout.setContentsMargins(0, 0, 0, 0)
        agent_label = QLabel("Agent 类型")
        agent_label.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 6px; background-color: white;")
        agent_layout.addWidget(agent_label)
        
        self.agent_combo = QComboBox()
        self.agent_combo.addItems(["building", "table", "dashboard", "permission", "workflow", "block"])
        self.agent_combo.setCurrentText("building")
        self.agent_combo.currentTextChanged.connect(self.on_agent_changed)
        self.agent_combo.setMinimumHeight(40)
        self.agent_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 14px;
                background-color: #ffffff;
                color: #1f2937;
                min-width: 160px;
            }
            QComboBox:hover {
                border-color: #93c5fd;
            }
            QComboBox::drop-down {
                border: none;
                width: 35px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid #64748b;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #e5e7eb;
                background-color: #ffffff;
                selection-background-color: #dbeafe;
                selection-color: #1e40af;
                padding: 6px;
                border-radius: 8px;
            }
        """)
        agent_layout.addWidget(self.agent_combo)
        row1.addWidget(self.agent_widget)
        
        # --- 评估模式 ---
        self.mode_widget = QWidget()
        self.mode_widget.setStyleSheet("background-color: #ffffff;")
        mode_layout = QVBoxLayout(self.mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_label = QLabel("评估模式")
        mode_label.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 6px; background-color: white;")
        mode_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["spec", "freeform"])
        self.mode_combo.setCurrentText("spec")
        self.mode_combo.setMinimumHeight(40)
        self.mode_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 14px;
                background-color: #ffffff;
                color: #1f2937;
                min-width: 130px;
            }
            QComboBox:hover {
                border-color: #93c5fd;
            }
            QComboBox::drop-down {
                border: none;
                width: 35px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 6px solid #64748b;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #e5e7eb;
                background-color: #ffffff;
                selection-background-color: #dbeafe;
                selection-color: #1e40af;
                padding: 6px;
                border-radius: 8px;
            }
        """)
        mode_layout.addWidget(self.mode_combo)
        row1.addWidget(self.mode_widget)
        
        # --- API Key ---
        self.api_key_widget = QWidget()
        self.api_key_widget.setStyleSheet("background-color: #ffffff;")
        api_key_layout = QVBoxLayout(self.api_key_widget)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_label = QLabel("JUDGE_API_KEY（必填）")
        api_key_label.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 6px; background-color: white;")
        api_key_layout.addWidget(api_key_label)
        
        api_key_input_layout = QHBoxLayout()
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("请输入 JUDGE_API_KEY...")
        self.api_key_input.setMinimumHeight(40)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                background-color: #fafafa;
                color: #1f2937;
            }
            QLineEdit:hover {
                border-color: #93c5fd;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                background-color: #ffffff;
            }
        """)
        # 加载已保存的 API Key
        saved_api_key = get_judge_api_key()
        if saved_api_key:
            self.api_key_input.setText(saved_api_key)
        
        self.toggle_api_key_btn = QPushButton("👁")
        self.toggle_api_key_btn.setMinimumWidth(40)
        self.toggle_api_key_btn.setMinimumHeight(40)
        self.toggle_api_key_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        self.toggle_api_key_btn.clicked.connect(self.toggle_api_key_visibility)
        self.toggle_api_key_btn.setToolTip("显示/隐藏")
        
        api_key_input_layout.addWidget(self.api_key_input, stretch=1)
        api_key_input_layout.addWidget(self.toggle_api_key_btn)
        api_key_layout.addLayout(api_key_input_layout)
        row1.addWidget(self.api_key_widget, stretch=1)
        
        # 安装焦点事件过滤器
        self.api_key_input.installEventFilter(self)
        
        row1.addStretch()
        layout.addLayout(row1)
        
        self.dimensions_widget = QWidget()
        self.dimensions_widget.setStyleSheet("background-color: white;")
        dim_v_layout = QVBoxLayout(self.dimensions_widget)
        dim_v_layout.setContentsMargins(0, 14, 0, 0)
        dim_v_layout.setSpacing(5)
        
        dimensions_label = QLabel("评估维度")
        dimensions_label.setStyleSheet("color: #64748b; font-size: 13px; font-weight: 600; margin-bottom: 4px; background-color: white;")
        dim_v_layout.addWidget(dimensions_label)
        
        dim_layout = QHBoxLayout()
        dim_layout.setSpacing(20)
        
        self.dim_table_checkbox = QCheckBox("📊 Table（表格）")
        self.dim_table_checkbox.setChecked(True)
        self.dim_permission_checkbox = QCheckBox("🔐 Permission（权限）")
        self.dim_permission_checkbox.setChecked(True)
        self.dim_workflow_checkbox = QCheckBox("🔄 Workflow（工作流）")
        self.dim_workflow_checkbox.setChecked(True)
        self.dim_formula_checkbox = QCheckBox("🔢 Formula（公式）")
        self.dim_formula_checkbox.setChecked(True)
        self.dim_dashboard_checkbox = QCheckBox("📈 Dashboard（仪表盘）")
        self.dim_dashboard_checkbox.setChecked(True)
        
        for checkbox in [self.dim_table_checkbox, self.dim_permission_checkbox, self.dim_workflow_checkbox, self.dim_formula_checkbox, self.dim_dashboard_checkbox]:
            checkbox.setStyleSheet("""
                QCheckBox {
                    color: #1f2937;
                    font-size: 13px;
                    spacing: 10px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #d1d5db;
                    border-radius: 5px;
                    background-color: #f9fafb;
                }
                QCheckBox::indicator:hover {
                    border-color: #3b82f6;
                }
                QCheckBox::indicator:checked {
                    background-color: #3b82f6;
                    border-color: #3b82f6;
                }
            """)
            dim_layout.addWidget(checkbox)
        
        dim_layout.addStretch()
        dim_v_layout.addLayout(dim_layout)
        layout.addWidget(self.dimensions_widget)
        
        return group
    
    def _create_building_panel(self):
        """创建 Building 专用面板"""
        panel = QWidget()
        panel.setStyleSheet("background-color: transparent;")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 单条测试区域
        single_test_section = self._create_single_test_section()
        layout.addWidget(single_test_section)
        
        # 结果显示区域
        result_section = self._create_result_section()
        layout.addWidget(result_section, stretch=1)
        
        return panel
    
    def _create_single_test_section(self):
        """创建单条测试区域"""
        group = QGroupBox("🧪 单条测试")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 15px;
                color: #1f2937;
                border: none;
                border-radius: 10px;
                margin-top: 6px;
                padding-top: 20px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 18px;
                padding: 0 10px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 28, 20, 22)
        
        self.single_query_input = QTextEdit()
        self.single_query_input.setPlaceholderText("输入测试 Query...")
        self.single_query_input.setMinimumHeight(50)
        self.single_query_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 14px;
                background-color: #fafafa;
                color: #1f2937;
                font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
            }
            QTextEdit:hover {
                border-color: #93c5fd;
            }
            QTextEdit:focus {
                border-color: #3b82f6;
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.single_query_input)
        
        self.single_base_input = QTextEdit()
        self.single_base_input.setPlaceholderText("输入 Base Token...")
        self.single_base_input.setFixedHeight(40)
        self.single_base_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 14px;
                background-color: #fafafa;
                color: #1f2937;
                min-height: 40px;
                max-height: 40px;
            }
            QTextEdit:hover {
                border-color: #93c5fd;
            }
            QTextEdit:focus {
                border-color: #3b82f6;
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.single_base_input)
        
        self.single_test_btn = QPushButton("运行单条测试")
        self.single_test_btn.clicked.connect(self.on_single_test)
        self.single_test_btn.setMinimumHeight(40)
        self.single_test_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #60a5fa, stop:1 #3b82f6);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
            }
        """)
        layout.addWidget(self.single_test_btn)
        
        return group
    
    def _create_result_section(self):
        """创建结果显示区域"""
        group = QGroupBox("📝 评测结果")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                font-size: 15px;
                color: #1f2937;
                border: none;
                border-radius: 10px;
                margin-top: 6px;
                padding-top: 20px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 18px;
                padding: 0 10px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 28, 20, 22)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("响应体将显示在这里...")
        self.result_text.setMinimumHeight(160)
        self.result_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                background-color: #fafafa;
                color: #1f2937;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
            }
            QTextEdit:focus {
                border-color: #3b82f6;
                background-color: #ffffff;
            }
        """)
        layout.addWidget(self.result_text)
        
        return group
    
    def _create_button_section(self):
        """创建按钮区域"""
        widget = QWidget()
        widget.setStyleSheet("background-color: #f8fafc;")
        layout = QHBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addStretch()
        
        self.annotation_column_btn = QPushButton("📝生成标注列")
        self.annotation_column_btn.clicked.connect(self.on_generate_annotation_column)
        self.annotation_column_btn.setMinimumHeight(40)
        self.annotation_column_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f97316, stop:1 #ea580c);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fb923c, stop:1 #f97316);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ea580c, stop:1 #c2410c);
            }
        """)
        layout.addWidget(self.annotation_column_btn)

        self.doc_to_bitable_btn = QPushButton("📄云文档转BASE")
        self.doc_to_bitable_btn.clicked.connect(self.on_doc_to_bitable)
        self.doc_to_bitable_btn.setMinimumHeight(40)
        self.doc_to_bitable_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #059669, stop:1 #047857);
            }
        """)
        layout.addWidget(self.doc_to_bitable_btn)

        self.batch_call_btn = QPushButton("🚀批量调用")
        self.batch_call_btn.clicked.connect(self.on_batch_call)
        self.batch_call_btn.setMinimumHeight(40)
        self.batch_call_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #60a5fa, stop:1 #3b82f6);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
            }
        """)
        layout.addWidget(self.batch_call_btn)
        
        return widget
    
    def on_agent_changed(self, agent):
        """Agent 类型切换处理"""
        panel_index = {
            "building": 0,
            "permission": 1,
            "table": 2,
            "dashboard": 3,
            "workflow": 4,
            "block": 5
        }.get(agent, 0)
        self.panel_stack.setCurrentIndex(panel_index)
        
        # 控制评估模式和评估维度的显示
        is_special_type = agent in ["permission", "table", "dashboard", "workflow", "block"]
        self.mode_widget.setVisible(not is_special_type)
        self.dimensions_widget.setVisible(agent == "building")
    
    def on_single_test(self):
        """单条测试"""
        agent = self.agent_combo.currentText()
        mode = self.mode_combo.currentText()
        
        query = self.single_query_input.toPlainText().strip()
        base_token = self.single_base_input.toPlainText().strip()
        
        if not query:
            QMessageBox.warning(self, "提示", "请输入 Query！")
            return
        
        if not base_token:
            QMessageBox.warning(self, "提示", "请输入 Base Token！")
            return
        
        dimensions = None
        if agent == "building":
            dimensions = []
            if self.dim_table_checkbox.isChecked():
                dimensions.append("table")
            if self.dim_permission_checkbox.isChecked():
                dimensions.append("permission")
            if self.dim_workflow_checkbox.isChecked():
                dimensions.append("workflow")
            if self.dim_formula_checkbox.isChecked():
                dimensions.append("formula")
            if self.dim_dashboard_checkbox.isChecked():
                dimensions.append("dashboard")
        
        result = self.single_judge.send_request(
            query=query,
            base_token=base_token,
            agent=agent,
            dimensions=dimensions,
            mode=mode
        )
        
        self.append_result("单条测试响应", result)
    
    def on_batch_call(self):
        """打开批量调用对话框"""
        dialog = BatchJudgeDialog(self)
        dialog.exec_()

    def on_doc_to_bitable(self):
        """打开云文档转 BASE 对话框"""
        dialog = DocToBitableDialog(self)
        dialog.exec_()

    def on_generate_annotation_column(self):
        """打开生成标注列对话框"""
        dialog = AnnotationColumnDialog(self)
        dialog.exec_()
    
    def append_result(self, title, data):
        """添加结果到文本框"""
        import json
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        content = f"[{timestamp}] {title}\n"
        content += json.dumps(data, indent=2, ensure_ascii=False)
        content += "\n" + "="*60 + "\n\n"
        
        self.result_text.append(content)
        scrollbar = self.result_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def toggle_api_key_visibility(self):
        """切换 API Key 显示/隐藏"""
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.toggle_api_key_btn.setText("🙈")
            self.toggle_api_key_btn.setToolTip("隐藏")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.toggle_api_key_btn.setText("👁")
            self.toggle_api_key_btn.setToolTip("显示")
        
        # 自动保存
        api_key = self.api_key_input.text().strip()
        if api_key:
            set_judge_api_key(api_key)
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于监听焦点事件"""
        if obj == self.api_key_input and event.type() == event.Type.FocusOut:
            # 失去焦点时自动保存
            api_key = self.api_key_input.text().strip()
            if api_key:
                set_judge_api_key(api_key)
        return super().eventFilter(obj, event)
    
    def get_config(self):
        """获取当前配置"""
        agent = self.agent_combo.currentText()
        config = {
            "agent": agent,
            "mode": self.mode_combo.currentText()
        }
        
        if agent == "building":
            dimensions = []
            if self.dim_table_checkbox.isChecked():
                dimensions.append("table")
            if self.dim_permission_checkbox.isChecked():
                dimensions.append("permission")
            if self.dim_workflow_checkbox.isChecked():
                dimensions.append("workflow")
            if self.dim_formula_checkbox.isChecked():
                dimensions.append("formula")
            if self.dim_dashboard_checkbox.isChecked():
                dimensions.append("dashboard")
            config["dimensions"] = dimensions
        
        return config

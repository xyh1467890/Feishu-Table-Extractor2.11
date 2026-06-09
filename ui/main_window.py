import sys
import os
import json
import webbrowser
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QTabWidget, QFileDialog, QMessageBox, QLineEdit, QLabel, QFrame,
    QStackedWidget, QPushButton, QSizePolicy
)
from ui.text_diff_dialog import TextDiffDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDesktopWidget

from ui.styles import APP_STYLE
from ui.table_panel import TablePanel, resource_path
from ui.simple_panel import SimplePanel
from ui.permission_panel import PermissionPanel
from ui.result_panel import ResultPanel
from ui.search_logic import SearchLogic
from ui.building_ui.building_judge_panel import BuildingJudgePanel
from workers.oauth_worker import OAuthTokenThread
from workers.cookie_worker import GetCookieThread
from workers.fetch_worker import FetchDataThread


class FeishuBitableApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("飞书多维表格数据管理工具")
        self.resize(1300, 920)
        self.setMinimumSize(1100, 700)
        
        self.current_module = "table"
        # 当前选中的导航组: "metadata" 或 "building_judge"
        self.current_nav_group = "metadata"
        self.current_result = None
        self.original_json = ""
        self.oauth_thread = None
        self.get_cookie_thread = None
        
        # 导航相关引用
        self.module_nav = None          # 主导航容器
        self.sub_nav_container = None   # 二级菜单容器（仅获取元数据组使用）
        self.nav_buttons = []           # 所有一级导航按钮
        self.sub_buttons = []           # 所有二级导航按钮
        self.table_panel = None
        self.dashboard_panel = None
        self.workflow_panel = None
        self.permission_panel = None
        self.form_panel = None
        self.building_judge_panel = None
        self.result_panel = None
        self.search_logic = None
        
        self.init_ui()
        
        # 窗口居中显示
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def init_ui(self):
        QApplication.instance().setStyle('Fusion')
        self.setStyleSheet(APP_STYLE)
        
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        left_sidebar = self.create_left_sidebar()
        main_layout.addWidget(left_sidebar)
        
        right_content = self.create_right_content()
        main_layout.addWidget(right_content, 1)
    
    def create_left_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("left_sidebar")
        sidebar.setFixedWidth(240)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        logo_container = QWidget()
        logo_container.setObjectName("logo_container")
        logo_container.setFixedHeight(72)
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(24, 20, 24, 20)
        logo_layout.setSpacing(8)
        
        app_title = QLabel("飞书多维表格工具")
        app_title.setObjectName("app_title")
        
        logo_layout.addWidget(app_title)
        logo_layout.addStretch()
        layout.addWidget(logo_container)
        
        nav_container = QWidget()
        nav_container.setObjectName("nav_container")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(16, 12, 16, 16)
        nav_layout.setSpacing(8)
        
        nav_label = QLabel("功能导航")
        nav_label.setObjectName("nav_section_label")
        nav_layout.addWidget(nav_label)
        
        self.module_nav = QWidget()
        self.module_nav.setObjectName("module_nav")
        main_layout = QVBoxLayout(self.module_nav)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        
        # ---------- 一级：获取元数据 ----------
        self.metadata_group_btn = self._create_group_button("📁  获取元数据", "metadata", is_selected=True)
        main_layout.addWidget(self.metadata_group_btn)
        
        # 二级菜单容器
        self.sub_nav_container = QWidget()
        sub_layout = QVBoxLayout(self.sub_nav_container)
        sub_layout.setContentsMargins(0, 4, 0, 4)
        sub_layout.setSpacing(2)
        
        self._create_sub_button(sub_layout, "📊  数据表", "table", is_selected=True)
        self._create_sub_button(sub_layout, "📈  仪表盘", "dashboard")
        self._create_sub_button(sub_layout, "🔄  工作流", "workflow")
        self._create_sub_button(sub_layout, "🔐  高级权限", "permission")
        self._create_sub_button(sub_layout, "📝  表单", "form")
        
        main_layout.addWidget(self.sub_nav_container)
        
        # 分隔
        spacer = QLabel("")
        spacer.setFixedHeight(4)
        main_layout.addWidget(spacer)
        
        # ---------- 一级：BASE 机评 ----------
        self.building_group_btn = self._create_group_button("🏗️  BASE 机评", "building_judge", is_selected=False)
        main_layout.addWidget(self.building_group_btn)
        
        main_layout.addStretch()
        nav_layout.addWidget(self.module_nav)
        
        nav_layout.addStretch()
        
        help_container = QWidget()
        help_container.setObjectName("help_container")
        help_layout = QVBoxLayout(help_container)
        help_layout.setContentsMargins(16, 16, 16, 24)
        
        help_title = QLabel("需要帮助？")
        help_title.setObjectName("help_title")
        
        help_desc = QLabel('点击联系<a href="https://www.larkoffice.com/invitation/page/add_contact/?token=6e2ma113-ab71-48a6-a684-2c8bb2e38e32" style="text-decoration:none;color:#3b82f6;">作者</a>')
        help_desc.setObjectName("help_desc")
        help_desc.setOpenExternalLinks(True)
        
        help_layout.addWidget(help_title)
        help_layout.addWidget(help_desc)
        nav_layout.addWidget(help_container)
        
        layout.addWidget(nav_container, 1)
        
        return sidebar
    
    def _create_group_button(self, text, group_id, is_selected=False):
        """创建一级导航组按钮"""
        btn = QLabel(text)
        btn.setObjectName("nav_group_button")
        btn.setProperty("group_id", group_id)
        btn.setProperty("selected", is_selected)
        btn.mousePressEvent = lambda e, g=group_id: self._on_group_clicked(g)
        btn.setCursor(Qt.PointingHandCursor)
        self.nav_buttons.append(btn)
        return btn
    
    def _create_sub_button(self, parent_layout, text, module_id, is_selected=False):
        """创建二级子导航按钮"""
        btn = QLabel(text)
        btn.setObjectName("nav_sub_button")
        btn.setProperty("module_id", module_id)
        btn.setProperty("selected", is_selected)
        btn.mousePressEvent = lambda e, m=module_id: self.on_module_clicked(m)
        btn.setCursor(Qt.PointingHandCursor)
        self.sub_buttons.append(btn)
        parent_layout.addWidget(btn)
        return btn
    
    def _on_group_clicked(self, group_id):
        """点击一级导航组"""
        self.current_nav_group = group_id
        
        # 更新一级按钮的选中状态
        for btn in self.nav_buttons:
            is_current = btn.property("group_id") == group_id
            btn.setProperty("selected", is_current)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        
        if group_id == "building_judge":
            # 直接跳转到 building 机评
            self.on_module_clicked("building_judge")
        else:
            # 点击"获取元数据"：默认进入第一个二级按钮（数据表）
            # 找到当前已选的子模块，若没有则默认选第一个
            active_module = "table"
            for sb in self.sub_buttons:
                if sb.property("selected"):
                    active_module = sb.property("module_id")
                    break
            self.on_module_clicked(active_module)
    
    def on_module_clicked(self, module_id):
        self.current_module = module_id
        
        # 根据 module_id 决定当前所属的导航组
        if module_id == "building_judge":
            self.current_nav_group = "building_judge"
        else:
            self.current_nav_group = "metadata"
        
        # 更新一级按钮的选中态
        for btn in self.nav_buttons:
            is_current = btn.property("group_id") == self.current_nav_group
            btn.setProperty("selected", is_current)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()
        
        # 更新二级按钮的选中态（仅对 metadata 组有效）
        for sb in self.sub_buttons:
            is_current = sb.property("module_id") == module_id and self.current_nav_group == "metadata"
            sb.setProperty("selected", is_current)
            sb.style().unpolish(sb)
            sb.style().polish(sb)
            sb.update()
        
        # 更新标题 & 面板
        module_titles = {
            "table": "📊 数据表",
            "dashboard": "📈 仪表盘",
            "workflow": "🔄 工作流",
            "permission": "🔐 高级权限",
            "form": "📝 表单",
            "building_judge": "🏗️ BASE 机评"
        }
        self.module_title.setText(module_titles.get(module_id, "📊 数据表"))
        
        panel_index = {
            "table": 0,
            "dashboard": 1,
            "workflow": 2,
            "permission": 3,
            "form": 4,
            "building_judge": 5
        }.get(module_id, 0)
        self.module_stack.setCurrentIndex(panel_index)
        self.result_panel.result_text.clear()
        self.current_result = None
        self.result_panel.export_button.setEnabled(False)
        
        # 对 Building 机评模块特殊处理：切换到单栏模式
        if module_id == "building_judge":
            self.mode_stack.setCurrentIndex(1)  # 切换到单栏模式
        else:
            self.mode_stack.setCurrentIndex(0)  # 切换到分栏模式
            self.result_panel.show()
            self.divider.show()
    
    def create_right_content(self):
        right_widget = QWidget()
        right_widget.setObjectName("right_content")
        
        layout = QVBoxLayout(right_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        header_bar = QWidget()
        header_bar.setObjectName("header_bar")
        header_bar.setFixedHeight(72)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(16)
        
        self.module_title = QLabel("📊 数据表")
        self.module_title.setObjectName("module_title")
        
        header_layout.addWidget(self.module_title)
        header_layout.addStretch()
        
        # 文本对比按钮
        text_diff_btn = QPushButton("📄 文本对比")
        text_diff_btn.setObjectName("secondary_btn")
        text_diff_btn.setMinimumHeight(40)
        text_diff_btn.setMinimumWidth(120)
        text_diff_btn.clicked.connect(self.show_text_diff_dialog)
        header_layout.addWidget(text_diff_btn)
        
        layout.addWidget(header_bar)
        
        # 创建两种布局模式的容器
        self.mode_stack = QStackedWidget()
        
        # --- 模式 0：普通分栏布局（给其他模块用） ---
        normal_widget = QWidget()
        normal_layout = QHBoxLayout(normal_widget)
        normal_layout.setContentsMargins(0, 0, 0, 0)
        normal_layout.setSpacing(1)
        
        self.left_panel_container = QWidget()
        self.left_panel_container.setObjectName("left_panel_container")
        self.left_panel_container.setFixedWidth(400)
        
        left_panel_layout = QVBoxLayout(self.left_panel_container)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        
        self.module_stack = QStackedWidget()
        self.table_panel = TablePanel(self)
        self.table_panel.tabs.currentChanged.connect(self.on_auth_tab_changed)
        self.dashboard_panel = SimplePanel(self, "仪表盘")
        self.workflow_panel = SimplePanel(self, "工作流")
        self.permission_panel = PermissionPanel(self)
        self.form_panel = SimplePanel(self, "表单")
        self.building_judge_panel = BuildingJudgePanel(self)
        
        self.module_stack.addWidget(self.table_panel)
        self.module_stack.addWidget(self.dashboard_panel)
        self.module_stack.addWidget(self.workflow_panel)
        self.module_stack.addWidget(self.permission_panel)
        self.module_stack.addWidget(self.form_panel)
        self.module_stack.addWidget(self.building_judge_panel)
        
        left_panel_layout.addWidget(self.module_stack)
        normal_layout.addWidget(self.left_panel_container)
        
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.VLine)
        self.divider.setObjectName("divider")
        normal_layout.addWidget(self.divider)
        
        self.result_panel = ResultPanel(self)
        normal_layout.addWidget(self.result_panel, 1)
        
        self.mode_stack.addWidget(normal_widget)
        
        # --- 模式 1：Building 机评单栏布局 ---
        self.mode_stack.addWidget(self.building_judge_panel)
        
        # 添加到主布局
        layout.addWidget(self.mode_stack, 1)
        
        self.search_logic = SearchLogic(
            self.result_panel.result_text,
            self.result_panel.search_widget
        )
        
        return right_widget
    
    def get_current_panel(self):
        if self.current_module == "table":
            return self.table_panel
        elif self.current_module == "dashboard":
            return self.dashboard_panel
        elif self.current_module == "workflow":
            return self.workflow_panel
        elif self.current_module == "permission":
            return self.permission_panel
        elif self.current_module == "form":
            return self.form_panel
        elif self.current_module == "building_judge":
            return self.building_judge_panel
        return None
    
    def on_manual_info_link_clicked(self, link):
        if link == "help:token":
            video_path = resource_path("get_user_access_token.mp4")
            if os.path.exists(video_path):
                if sys.platform == "win32":
                    os.startfile(video_path)
                elif sys.platform == "darwin":
                    subprocess.call(["open", video_path])
                else:
                    subprocess.call(["xdg-open", video_path])
            else:
                QMessageBox.warning(self, "提示", f"视频文件不存在：{video_path}")
        elif link.startswith("http"):
            webbrowser.open(link)
    
    def toggle_token_visibility(self, checked):
        current_panel = self.get_current_panel()
        if not current_panel or not hasattr(current_panel, 'token_input'):
            return
        
        if checked:
            current_panel.token_input.setEchoMode(QLineEdit.Normal)
            current_panel.show_token_btn.setText("隐藏")
        else:
            current_panel.token_input.setEchoMode(QLineEdit.Password)
            current_panel.show_token_btn.setText("显示")
    
    def start_get_cookie(self):
        current_panel = self.get_current_panel()
        if not current_panel:
            return
        
        current_panel.get_cookie_btn.setEnabled(False)
        current_panel.cookie_status_label.setText("正在准备...")
        
        self.get_cookie_thread = GetCookieThread()
        self.get_cookie_thread.cookie_received.connect(self.on_cookie_received)
        self.get_cookie_thread.error.connect(self.on_get_cookie_error)
        self.get_cookie_thread.progress.connect(self.update_cookie_status)
        self.get_cookie_thread.start()
    
    def confirm_get_cookie(self):
        if self.get_cookie_thread:
            current_panel = self.get_current_panel()
            if current_panel:
                current_panel.confirm_login_btn.setEnabled(False)
            self.get_cookie_thread.get_cookie_after_login()
    
    def update_cookie_status(self, message):
        current_panel = self.get_current_panel()
        if current_panel:
            current_panel.cookie_status_label.setText(message)
            if "请在浏览器中登录" in message:
                current_panel.confirm_login_btn.setEnabled(True)
    
    def on_cookie_received(self, cookie):
        current_panel = self.get_current_panel()
        if current_panel:
            current_panel.cookie_input.setText(cookie)
            current_panel.cookie_status_label.setText("✓ Cookie 已自动填入")
            current_panel.get_cookie_btn.setEnabled(True)
            current_panel.confirm_login_btn.setEnabled(False)
        QMessageBox.information(self, "成功", "Cookie 获取成功，已自动填入！")
    
    def on_get_cookie_error(self, error_msg):
        current_panel = self.get_current_panel()
        if current_panel:
            current_panel.cookie_status_label.setText(f"✗ 错误：{error_msg}")
            current_panel.get_cookie_btn.setEnabled(True)
            current_panel.confirm_login_btn.setEnabled(False)
        QMessageBox.critical(self, "错误", error_msg)
    
    def start_oauth_flow(self):
        current_panel = self.get_current_panel()
        if not current_panel or not hasattr(current_panel, 'app_id_input'):
            return
        
        app_id = current_panel.app_id_input.text().strip()
        app_secret = current_panel.app_secret_input.text().strip()
        
        if not app_id:
            QMessageBox.warning(self, "提示", "请输入 App ID")
            return
        if not app_secret:
            QMessageBox.warning(self, "提示", "请输入 App Secret")
            return
        
        current_panel.login_button.setEnabled(False)
        current_panel.oauth_status_label.setText("正在打开浏览器进行授权...")
        
        self.oauth_thread = OAuthTokenThread(app_id, app_secret)
        self.oauth_thread.token_received.connect(self.on_token_received)
        self.oauth_thread.error.connect(self.on_oauth_error)
        self.oauth_thread.start()
    
    def on_token_received(self, token):
        current_panel = self.get_current_panel()
        if current_panel and hasattr(current_panel, 'token_input'):
            current_panel.token_input.setText(token)
            current_panel.oauth_status_label.setText("✓ 登录成功！")
            current_panel.login_button.setEnabled(True)
        QMessageBox.information(self, "成功", "登录成功！Token 已自动填充。")
    
    def on_oauth_error(self, error_msg):
        current_panel = self.get_current_panel()
        if current_panel and hasattr(current_panel, 'oauth_status_label'):
            current_panel.oauth_status_label.setText(f"✗ 错误：{error_msg}")
            current_panel.login_button.setEnabled(True)
        QMessageBox.critical(self, "错误", error_msg)
    
    def fetch_data(self):
        current_panel = self.get_current_panel()
        if not current_panel:
            return
        
        feishu_url = current_panel.url_input.text().strip()
        
        if not feishu_url:
            QMessageBox.warning(self, "提示", "请输入多维表格链接")
            return
        
        current_panel.fetch_button.setEnabled(False)
        self.result_panel.export_button.setEnabled(False)
        self.result_panel.result_text.clear()
        current_panel.progress_label.setStyleSheet("color: #409eff;")
        
        # 根据当前模块处理不同类型
        if self.current_module == "table":
            # 数据表 - 使用现有的 FetchDataThread
            auth_type = None
            auth_data = None
            
            tab_index = current_panel.tabs.currentIndex()
            if tab_index == 0 or tab_index == 1:
                if not hasattr(current_panel, 'token_input'):
                    QMessageBox.warning(self, "提示", "未找到 Token 输入框")
                    current_panel.fetch_button.setEnabled(True)
                    return
                user_token = current_panel.token_input.text().strip()
                if not user_token:
                    QMessageBox.warning(self, "提示", "请输入用户 Token")
                    current_panel.fetch_button.setEnabled(True)
                    return
                auth_type = "token"
                auth_data = user_token
            elif tab_index == 2:
                if not hasattr(current_panel, 'cookie_input'):
                    QMessageBox.warning(self, "提示", "未找到 Cookie 输入框")
                    current_panel.fetch_button.setEnabled(True)
                    return
                cookie = current_panel.cookie_input.text().strip()
                if not cookie:
                    QMessageBox.warning(self, "提示", "请输入飞书 Cookie")
                    current_panel.fetch_button.setEnabled(True)
                    return
                auth_type = "cookie"
                auth_data = cookie
            
            fetch_records = current_panel.fetch_records_checkbox.isChecked() if hasattr(current_panel, 'fetch_records_checkbox') else False
            
            self.thread = FetchDataThread(auth_type, auth_data, feishu_url, fetch_records)
            self.thread.progress.connect(lambda msg: current_panel.progress_label.setText(msg))
            self.thread.finished.connect(self.on_fetch_finished)
            self.thread.error.connect(lambda err: self.on_fetch_error(err, current_panel))
            self.thread.start()
        
        elif self.current_module == "workflow":
            # 工作流 - 使用新的 API
            cookie = current_panel.cookie_input.text().strip()
            if not cookie:
                QMessageBox.warning(self, "提示", "请输入飞书 Cookie")
                current_panel.fetch_button.setEnabled(True)
                return
            
            current_panel.progress_label.setText("正在提取工作流...")
            
            # 创建工作流线程
            from PyQt5.QtCore import QThread, pyqtSignal
            
            class WorkflowFetchThread(QThread):
                progress = pyqtSignal(str)
                finished = pyqtSignal(object)
                error = pyqtSignal(str)
                
                def __init__(self, url, cookie):
                    super().__init__()
                    self.url = url
                    self.cookie = cookie
                
                def run(self):
                    try:
                        # 延迟导入避免循环依赖
                        from api.feishu_workflow_api import extract_workflow_info
                        self.progress.emit("正在获取工作流配置...")
                        result = extract_workflow_info(self.url, self.cookie)
                        self.finished.emit(result)
                    except Exception as e:
                        self.error.emit(str(e))
            
            self.workflow_thread = WorkflowFetchThread(feishu_url, cookie)
            self.workflow_thread.progress.connect(lambda msg: current_panel.progress_label.setText(msg))
            self.workflow_thread.finished.connect(lambda r: self.on_workflow_fetch_finished(r, current_panel))
            self.workflow_thread.error.connect(lambda err: self.on_fetch_error(err, current_panel))
            self.workflow_thread.start()
        
        elif self.current_module == "dashboard":
            # 仪表盘
            cookie = current_panel.cookie_input.text().strip()
            if not cookie:
                QMessageBox.warning(self, "提示", "请输入飞书 Cookie")
                current_panel.fetch_button.setEnabled(True)
                return
            
            current_panel.progress_label.setText("正在获取仪表盘数据...")
            
            from PyQt5.QtCore import QThread, pyqtSignal
            
            class DashboardFetchThread(QThread):
                progress = pyqtSignal(str)
                finished = pyqtSignal(object)
                error = pyqtSignal(str)
                
                def __init__(self, url, cookie):
                    super().__init__()
                    self.url = url
                    self.cookie = cookie
                
                def run(self):
                    try:
                        from api.feishu_dashboard_api import extract_dashboard_info
                        self.progress.emit("正在获取仪表盘配置...")
                        result = extract_dashboard_info(self.url, self.cookie)
                        self.finished.emit(result)
                    except Exception as e:
                        self.error.emit(str(e))
            
            self.dashboard_thread = DashboardFetchThread(feishu_url, cookie)
            self.dashboard_thread.progress.connect(lambda msg: current_panel.progress_label.setText(msg))
            self.dashboard_thread.finished.connect(lambda r: self.on_dashboard_fetch_finished(r, current_panel))
            self.dashboard_thread.error.connect(lambda err: self.on_fetch_error(err, current_panel))
            self.dashboard_thread.start()
        
        elif self.current_module == "permission":
            # 高级权限
            tab_index = current_panel.tabs.currentIndex()
            if not hasattr(current_panel, 'token_input'):
                QMessageBox.warning(self, "提示", "未找到 Token 输入框")
                current_panel.fetch_button.setEnabled(True)
                return
            
            user_token = current_panel.token_input.text().strip()
            if not user_token:
                QMessageBox.warning(self, "提示", "请输入用户 Token")
                current_panel.fetch_button.setEnabled(True)
                return
            
            current_panel.progress_label.setText("正在获取高级权限...")
            
            # 创建权限获取线程
            from PyQt5.QtCore import QThread, pyqtSignal
            
            class PermissionFetchThread(QThread):
                progress = pyqtSignal(str)
                finished = pyqtSignal(object)
                error = pyqtSignal(str)
                
                def __init__(self, url, token):
                    super().__init__()
                    self.url = url
                    self.token = token
                
                def run(self):
                    try:
                        # 延迟导入避免循环依赖
                        from api.feishu_permission_api import extract_permission_info
                        self.progress.emit("正在获取权限配置...")
                        result = extract_permission_info(self.url, self.token)
                        self.finished.emit(result)
                    except Exception as e:
                        self.error.emit(str(e))
            
            self.permission_thread = PermissionFetchThread(feishu_url, user_token)
            self.permission_thread.progress.connect(lambda msg: current_panel.progress_label.setText(msg))
            self.permission_thread.finished.connect(lambda r: self.on_permission_fetch_finished(r, current_panel))
            self.permission_thread.error.connect(lambda err: self.on_fetch_error(err, current_panel))
            self.permission_thread.start()
        
        elif self.current_module == "form":
            # 表单 - 使用Cookie方法
            cookie = current_panel.cookie_input.text().strip()
            if not cookie:
                QMessageBox.warning(self, "提示", "请输入飞书 Cookie")
                current_panel.fetch_button.setEnabled(True)
                return
            
            current_panel.progress_label.setText("正在获取表单配置...")
            
            # 创建表单获取线程
            from PyQt5.QtCore import QThread, pyqtSignal
            
            class FormFetchThread(QThread):
                progress = pyqtSignal(str)
                finished = pyqtSignal(object)
                error = pyqtSignal(str)
                
                def __init__(self, url, cookie):
                    super().__init__()
                    self.url = url
                    self.cookie = cookie
                
                def run(self):
                    try:
                        from api.feishu_form_api import extract_form_info
                        self.progress.emit("正在提取表单数据...")
                        result = extract_form_info(self.url, self.cookie)
                        self.finished.emit(result)
                    except Exception as e:
                        self.error.emit(str(e))
            
            self.form_thread = FormFetchThread(feishu_url, cookie)
            self.form_thread.progress.connect(lambda msg: current_panel.progress_label.setText(msg))
            self.form_thread.finished.connect(lambda r: self.on_form_fetch_finished(r, current_panel))
            self.form_thread.error.connect(lambda err: self.on_fetch_error(err, current_panel))
            self.form_thread.start()
    
    def on_workflow_fetch_finished(self, result, current_panel):
        """工作流提取完成处理"""
        self.current_result = result
        self.original_json = json.dumps(result, ensure_ascii=False, indent=2)
        self.result_panel.result_text.setText(self.original_json)
        self.search_logic.set_original_text(self.original_json)
        self.result_panel.export_button.setEnabled(True)
        current_panel.fetch_button.setEnabled(True)
        current_panel.progress_label.setStyleSheet("color: #27ae60;")
        current_panel.progress_label.setText("✓ 获取成功！")
    
    def on_dashboard_fetch_finished(self, result, current_panel):
        """仪表盘提取完成处理"""
        self.current_result = result
        self.original_json = json.dumps(result, ensure_ascii=False, indent=2)
        self.result_panel.result_text.setText(self.original_json)
        self.search_logic.set_original_text(self.original_json)
        self.result_panel.export_button.setEnabled(True)
        current_panel.fetch_button.setEnabled(True)
        current_panel.progress_label.setStyleSheet("color: #27ae60;")
        current_panel.progress_label.setText("✓ 获取成功！")
    
    def on_permission_fetch_finished(self, result, current_panel):
        """高级权限提取完成处理"""
        self.current_result = result
        self.original_json = json.dumps(result, ensure_ascii=False, indent=2)
        self.result_panel.result_text.setText(self.original_json)
        self.search_logic.set_original_text(self.original_json)
        self.result_panel.export_button.setEnabled(True)
        current_panel.fetch_button.setEnabled(True)
        current_panel.progress_label.setStyleSheet("color: #27ae60;")
        current_panel.progress_label.setText("✓ 获取成功！")
    
    def on_form_fetch_finished(self, result, current_panel):
        """表单提取完成处理"""
        self.current_result = result
        self.original_json = json.dumps(result, ensure_ascii=False, indent=2)
        self.result_panel.result_text.setText(self.original_json)
        self.search_logic.set_original_text(self.original_json)
        self.result_panel.export_button.setEnabled(True)
        current_panel.fetch_button.setEnabled(True)
        current_panel.progress_label.setStyleSheet("color: #27ae60;")
        current_panel.progress_label.setText("✓ 获取成功！")
    
    def on_fetch_finished(self, result):
        current_panel = self.get_current_panel()
        if not current_panel:
            return
        
        self.current_result = result
        self.original_json = json.dumps(result, ensure_ascii=False, indent=2)
        self.result_panel.result_text.setText(self.original_json)
        self.search_logic.set_original_text(self.original_json)
        self.result_panel.export_button.setEnabled(True)
        current_panel.fetch_button.setEnabled(True)
        current_panel.progress_label.setStyleSheet("color: #27ae60;")
        current_panel.progress_label.setText("✓ 获取成功！")
    
    def on_fetch_error(self, error_msg, current_panel):
        self.result_panel.result_text.setText(f"错误：{error_msg}")
        current_panel.fetch_button.setEnabled(True)
        current_panel.progress_label.setStyleSheet("color: #e74c3c;")
        current_panel.progress_label.setText("✗ 获取失败")
        QMessageBox.critical(self, "错误", f"获取数据失败：{error_msg}")
    
    def on_search_text_changed(self, search_text):
        self.search_logic.on_search_text_changed(search_text)
    
    def on_prev_match(self):
        self.search_logic.on_prev_match()
    
    def on_next_match(self):
        self.search_logic.on_next_match()
    
    def on_auth_tab_changed(self, index):
        from PyQt5.QtWidgets import QMessageBox
        # index 0: Token, 1: OAuth, 2: Cookie
        if index == 2 and self.table_panel:
            # Cookie tab selected
            QMessageBox.information(
                self,
                "提示",
                "该方法仅支持提取当前数据表的 JSON 数据，不支持获取全部飞书多维表格的元数据。",
                QMessageBox.Ok
            )
            # Disable fetch records checkbox
            if self.table_panel.fetch_records_checkbox:
                self.table_panel.fetch_records_checkbox.setEnabled(False)
                self.table_panel.fetch_records_checkbox.setChecked(False)
        elif self.table_panel and self.table_panel.fetch_records_checkbox:
            # Enable fetch records checkbox for other tabs
            self.table_panel.fetch_records_checkbox.setEnabled(True)

    def export_json(self):
        if not self.current_result:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存 JSON 文件",
            "",
            "JSON 文件 (*.json);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.current_result, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "成功", f"文件已保存到：{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件失败：{str(e)}")
    
    def show_text_diff_dialog(self):
        """显示文本对比对话框"""
        # 检查是否已经有对话框存在
        if not hasattr(self, 'text_diff_dialog') or not self.text_diff_dialog:
            # 不传入parent，让它成为独立窗口
            self.text_diff_dialog = TextDiffDialog()
        self.text_diff_dialog.show()
        self.text_diff_dialog.raise_()
        self.text_diff_dialog.activateWindow()

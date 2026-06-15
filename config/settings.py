# OAuth 配置
REDIRECT_PORT = 3000
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"

# Building 机评 API 配置
JUDGE_API_URL = "https://sszy6ucc.fn-boe.bytedance.net/v1/judge"

# 配置文件路径
import os
import json
import sys

def get_config_dir():
    """获取配置文件目录
    - 打包后（PyInstaller）：优先存在用户应用数据目录，保证持久化
    - 开发时：存在项目根目录下
    """
    if getattr(sys, "frozen", False):
        # Windows: %APPDATA%\飞书多维表格工具
        if sys.platform == "win32":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
            path = os.path.join(base, "飞书多维表格工具")
        # macOS: ~/Library/Application Support/飞书多维表格工具
        elif sys.platform == "darwin":
            path = os.path.join(os.path.expanduser("~"),
                                "Library", "Application Support",
                                "飞书多维表格工具")
        # Linux: ~/.config/飞书多维表格工具
        else:
            path = os.path.join(os.path.expanduser("~"),
                                ".config", "飞书多维表格工具")
    else:
        # 开发模式：放在项目根目录下的 config/ 子目录
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    os.makedirs(path, exist_ok=True)
    return path

CONFIG_DIR = get_config_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "user_config.json")

def get_config():
    """获取用户配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config):
    """保存用户配置"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")

def get_judge_api_key():
    """获取 JUDGE_API_KEY"""
    config = get_config()
    return config.get("JUDGE_API_KEY", "")

def set_judge_api_key(api_key):
    """设置 JUDGE_API_KEY"""
    config = get_config()
    config["JUDGE_API_KEY"] = api_key
    save_config(config)

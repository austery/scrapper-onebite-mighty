"""
加载和验证配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 网站配置
    SITE_URL = os.getenv('SITE_URL')
    LOGIN_URL = os.getenv('LOGIN_URL')
    USERNAME = os.getenv('USERNAME')
    PASSWORD = os.getenv('PASSWORD')
    
    # 选择器
    USERNAME_SELECTOR = os.getenv('USERNAME_SELECTOR')
    PASSWORD_SELECTOR = os.getenv('PASSWORD_SELECTOR')
    LOGIN_BUTTON_SELECTOR = os.getenv('LOGIN_BUTTON_SELECTOR')
    LOGIN_SUCCESS_INDICATOR = os.getenv('LOGIN_SUCCESS_INDICATOR')
    
    # 设置
    HEADLESS = os.getenv('HEADLESS', 'False').lower() == 'true'
    TIMEOUT = int(os.getenv('TIMEOUT', 30000))
    WAIT_TIME = int(os.getenv('WAIT_TIME', 500))
    
    # 路径
    OUTPUT_DIR = Path('output')
    LOGS_DIR = Path('logs')
    AUTH_FILE = Path('auth.json')
    
    @classmethod
    def validate(cls):
        """验证必要配置"""
        required = ['SITE_URL', 'USERNAME', 'PASSWORD']
        missing = [k for k in required if not getattr(cls, k)]
        if missing:
            raise ValueError(f"缺少配置: {', '.join(missing)}")
        
        # 创建必要目录
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)
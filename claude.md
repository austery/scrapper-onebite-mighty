# Comment Scraper Project Specification v3.0

## 🎯 Project Overview

**Project Name:** Automated Comment Scraper  
**Purpose:** 自动登录网站，抓取指定帖子的所有评论，保存为结构化JSON文件  
**Language:** Python 3.8+  
**Core Library:** Playwright (async)  
**Mode:** 半自动化 - 自动登录 + 单帖处理

## 📁 Project Structure

comment_scraper/
├── claude.md              # 本文档
├── .env                   # 登录凭据（不提交Git）
├── .env.example           # 凭据模板
├── .gitignore            # Git忽略配置
├── requirements.txt       # Python依赖
├── test_urls.txt         # 测试URL列表
├── src/
│   ├── **init**.py
│   ├── config.py         # 配置管理
│   ├── login.py          # 自动登录模块
│   ├── scraper.py        # 评论抓取核心
│   └── main.py           # 主程序入口
├── output/               # JSON输出目录
│   └── [timestamp]_[post_id].json
└── logs/                 # 日志文件
    └── scraper.log


## 🔧 Phase 1: Environment Setup

### 1.1 Dependencies (requirements.txt)

```txt
playwright==1.40.0
python-dotenv==1.0.0
```

### 1.2 Configuration Files

**.env.example** (模板，可提交)

```env
# Website Configuration
SITE_URL=https://example.com
LOGIN_URL=https://example.com/login
USERNAME=your_username_here
PASSWORD=your_password_here

# Scraper Settings
HEADLESS=False
TIMEOUT=30000
WAIT_TIME=500

# Selectors (根据实际网站调整)
USERNAME_SELECTOR=input[name="username"]
PASSWORD_SELECTOR=input[name="password"]
LOGIN_BUTTON_SELECTOR=button[type="submit"]
LOGIN_SUCCESS_INDICATOR=.user-avatar
```

**.gitignore** (必须包含)

```gitignore
# Sensitive
.env
auth.json
*.session

# Output
output/
logs/

# Python
__pycache__/
*.py[cod]

# IDE
.vscode/
.idea/
```

**test_urls.txt** (测试用URL)

```txt
https://example.com/post/12345
```

## 🚀 Phase 2: Core Implementation

### 2.1 Configuration Module (src/config.py)

```python
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
```

### 2.2 Auto Login Module (src/login.py)

```python
"""
自动登录和会话管理
"""
async def auto_login(page, config):
    """
    自动登录流程
    Returns: bool - 登录是否成功
    """
    # 1. 访问登录页
    # 2. 填写凭据
    # 3. 点击登录
    # 4. 验证登录成功
    # 5. 保存会话状态
    pass

async def check_login_status(page, config):
    """
    检查登录状态是否有效
    Returns: bool
    """
    pass
```

### 2.3 Scraper Core (src/scraper.py)

#### 关键选择器（绝对不能使用nth-child）

```python
SELECTORS = {
    # 锚点：评论区容器
    'COMMENT_CONTAINER': '#sidebar-comments-region',
    
    # 加载更多评论按钮
    'LOAD_MORE_BUTTON': 'text="Previous Comments"',
    
    # 展开折叠内容链接
    'EXPAND_LINKS': 'a.more.text-color-grey-3-link',
    
    # 评论项（在容器内查找）
    'COMMENT_ITEMS': 'li',  # 必须在COMMENT_CONTAINER内使用
}
```

#### 双循环加载策略

```python
async def load_all_comments(page):
    """
    Phase 1: 循环点击"Previous Comments"直到全部加载
    Phase 2: 循环点击所有"more"链接直到全部展开
    """
    # Loop 1: 加载所有评论页
    while True:
        try:
            button = page.get_by_text('Previous Comments')
            if await button.is_visible():
                await button.click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(config.WAIT_TIME)
            else:
                break
        except:
            break
    
    # Loop 2: 展开所有折叠内容
    while True:
        links = await page.locator('a.more.text-color-grey-3-link').all()
        if not links:
            break
        for link in links:
            await link.click()
            await page.wait_for_timeout(config.WAIT_TIME)
```

#### 数据提取

```python
async def extract_comments(page):
    """
    提取评论数据，保持层级结构
    Returns: List[Dict] - 评论数据结构
    """
    # 定位评论容器
    container = page.locator('#sidebar-comments-region')
    
    # 获取所有根评论
    comments = []
    root_items = await container.locator('li').all()
    
    for item in root_items:
        comment_data = {
            'text': '',      # 评论正文
            'author': '',    # 作者（如果有）
            'timestamp': '', # 时间戳（如果有）
            'replies': []    # 回复列表
        }
        
        # TODO: 提取评论文本
        # TODO: 提取回复（嵌套的li或特定class）
        # TODO: 保持层级关系
        
        comments.append(comment_data)
    
    return comments
```

### 2.4 Main Entry (src/main.py)

```python
"""
主程序入口
"""
import json
import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

async def process_single_url(url):
    """
    处理单个URL的完整流程
    """
    async with async_playwright() as p:
        # 1. 启动浏览器
        browser = await p.chromium.launch(headless=Config.HEADLESS)
        
        # 2. 创建上下文（尝试使用已保存的会话）
        context_options = {'viewport': {'width': 1920, 'height': 1080}}
        if Config.AUTH_FILE.exists():
            context_options['storage_state'] = str(Config.AUTH_FILE)
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        # 3. 检查/执行登录
        if not Config.AUTH_FILE.exists() or not await check_login_status(page):
            await auto_login(page, Config)
        
        # 4. 访问目标URL
        await page.goto(url)
        
        # 5. 加载所有评论
        await load_all_comments(page)
        
        # 6. 提取数据
        comments = await extract_comments(page)
        
        # 7. 保存为JSON
        output_data = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'total_comments': len(comments),
            'comments': comments
        }
        
        # 生成文件名：时间戳_帖子ID.json
        post_id = url.split('/')[-1]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Config.OUTPUT_DIR / f"{timestamp}_{post_id}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存到: {output_file}")
        
        await browser.close()
        return output_data

async def main():
    """
    主函数：从test_urls.txt读取URL并处理
    """
    # 验证配置
    Config.validate()
    
    # 读取测试URL
    with open('test_urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        print("❌ test_urls.txt 中没有URL")
        return
    
    # 处理第一个URL作为测试
    test_url = urls[0]
    print(f"🔍 正在处理: {test_url}")
    
    try:
        result = await process_single_url(test_url)
        print(f"📊 抓取到 {result['total_comments']} 条评论")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 Phase 3: Output Format

### 3.1 JSON Structure (当前阶段)

```json
{
  "url": "https://example.com/post/12345",
  "scraped_at": "2024-12-20T15:30:00",
  "total_comments": 25,
  "comments": [
    {
      "text": "这是一条根评论的完整内容",
      "author": "用户A",
      "timestamp": "2024-12-20 14:00",
      "replies": [
        {
          "text": "这是回复1",
          "author": "用户B",
          "timestamp": "2024-12-20 14:30"
        },
        {
          "text": "这是回复2",
          "author": "用户C",
          "timestamp": "2024-12-20 14:45"
        }
      ]
    },
    {
      "text": "这是另一条根评论",
      "author": "用户D",
      "timestamp": "2024-12-20 15:00",
      "replies": []
    }
  ]
}
```

### 3.2 Future: Markdown Format (后续实现)

```markdown
# 帖子标题
URL: https://example.com/post/12345
抓取时间: 2024-12-20 15:30:00

## 评论 (25)

**用户A** - 2024-12-20 14:00
这是一条根评论的完整内容

---

> **用户B** - 2024-12-20 14:30
> 这是回复1

> **用户C** - 2024-12-20 14:45
> 这是回复2

=====================================

**用户D** - 2024-12-20 15:00
这是另一条根评论

=====================================
```

## ⚠️ Critical Rules

1. **NEVER use nth-child or position-based selectors**
2. **ALWAYS use try-except for element operations**
3. **NEVER commit .env file to Git**
4. **ALWAYS validate login status before scraping**
5. **Log every major operation for debugging**

## 🧪 Testing Strategy

### Step 1: Setup Test

```bash
# 1. 复制配置
cp .env.example .env
# 2. 填写真实凭据
nano .env
# 3. 添加测试URL
echo "https://example.com/post/12345" > test_urls.txt
```

### Step 2: Run Test

```bash
python src/main.py
```

### Expected Output

```
🔍 正在处理: https://example.com/post/12345
正在登录...
✅ 登录成功
加载评论中...
展开折叠内容...
提取评论数据...
✅ 已保存到: output/20241220_153000_12345.json
📊 抓取到 25 条评论
```

## 📝 Implementation Checklist

- [ ] Create project structure
- [ ] Setup .env configuration
- [ ] Implement auto-login
- [ ] Implement dual-loop loading
- [ ] Implement comment extraction
- [ ] Save to JSON
- [ ] Add error handling
- [ ] Add logging
- [ ] Test with real URL
- [ ] (Future) Add Markdown output

## 🚦 Next Steps

1. **当前阶段**: 实现JSON输出的基础功能
2. **下一阶段**: 优化数据提取，确保层级结构正确
3. **未来阶段**: 添加Markdown输出格式


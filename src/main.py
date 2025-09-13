"""
主程序入口
"""
import json
import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from playwright.async_api import async_playwright

from config import Config
from login import auto_login, check_login_status
from scraper import load_all_comments, extract_comments
from image_processor import process_images_in_content, process_images_in_content_obsidian, create_markdown_from_html
from obsidian_helpers import (
    parse_relative_time_to_date,
    sanitize_title_for_filename,
    generate_obsidian_filename,
    generate_yaml_frontmatter,
    OBSIDIAN_ARTICLES_DIR,
    OBSIDIAN_ATTACHMENTS_DIR
)
import re
from urllib.parse import urljoin



def extract_post_id(url: str) -> str:
    """
    从OneNewBite URL中提取帖子ID（仅限于简短的安全标识符）
    优先使用数字ID，避免超长文件名问题
    例如: https://onenewbite.com/posts/43168058 -> 43168058
    """
    import hashlib
    from urllib.parse import unquote
    
    # 尝试从URL中匹配数字ID（最优选择）
    match = re.search(r'/posts/(\d+)', url)
    if match:
        return match.group(1)
    
    # 如果没找到数字ID，生成基于URL的短哈希ID
    # 这避免了文件名过长的问题
    parts = url.rstrip('/').split('/')
    if parts:
        post_part = parts[-1]
        # 为超长URL生成安全的短ID
        url_hash = hashlib.md5(post_part.encode('utf-8')).hexdigest()[:12]
        return f"hash_{url_hash}"
    
    # 如果都失败了，使用时间戳作为后备
    return str(int(time.time()))


async def extract_post_id_from_page(page) -> str:
    """
    从页面HTML中提取帖子的数字ID
    优先使用URL，然后查找DOM属性
    """
    try:
        # 首先尝试从当前页面URL提取（最可靠的方法）
        current_url = page.url
        print(f"    调试: 当前页面URL: {current_url}")
        id_match = re.search(r'/posts/(\d+)', current_url)
        if id_match:
            extracted_id = id_match.group(1)
            print(f"    调试: 从URL提取到的ID: {extracted_id}")
            return extracted_id
        
        # 如果URL中没找到，再尝试DOM选择器（作为备选）
        selectors_to_try = [
            '[data-post-id]',
            '[data-id]', 
            '.post[data-id]',
            'article[data-post-id]',
            'article[data-id]',
            '[id*="post"]',
            'meta[property="og:url"]'
        ]
        
        for selector in selectors_to_try:
            try:
                element = await page.query_selector(selector)
                if element:
                    print(f"    调试: 选择器 {selector} 找到元素")
                    # 尝试获取data-post-id属性
                    post_id = await element.get_attribute('data-post-id')
                    if post_id and post_id.isdigit():
                        print(f"    调试: 从 data-post-id 获取到: {post_id}")
                        return post_id
                    
                    # 尝试获取data-id属性
                    post_id = await element.get_attribute('data-id')
                    if post_id and post_id.isdigit():
                        print(f"    调试: 从 data-id 获取到: {post_id}")
                        return post_id
                    
                    # 如果是meta标签，从content属性提取ID
                    if selector.startswith('meta'):
                        content = await element.get_attribute('content')
                        if content:
                            id_match = re.search(r'/posts/(\d+)', content)
                            if id_match:
                                return id_match.group(1)
            except Exception:
                continue
        
        # 如果DOM选择器也都没找到，返回None
            
    except Exception as e:
        print(f"⚠️ 从页面提取ID失败: {e}")
    
    return None


def sanitize_title_for_filename(title: str, max_length: int = 60) -> str:
    """
    清理标题并生成安全的文件名
    """
    if not title:
        return "Untitled"
    
    # 移除HTML标签
    import re
    title = re.sub(r'<[^>]+>', '', title)
    
    # 清理并规范化空白字符
    title = re.sub(r'\s+', ' ', title.strip())
    
    # 移除文件名非法字符
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    title = re.sub(illegal_chars, '', title)
    
    # 移除开头结尾的点和空格
    title = title.strip('. ')
    
    # 长度截断
    if len(title) > max_length:
        title = title[:max_length].rstrip() + "..."
    
    return title or "Untitled"


def generate_safe_markdown_filename(title: str, published_date: str = None) -> str:
    """
    生成安全的Markdown文件名
    格式: YYYY-MM-DD - [清理并截断后的标题].md
    """
    # 清理标题
    safe_title = sanitize_title_for_filename(title, max_length=60)
    
    # 如果没有提供日期，使用今天的日期
    if not published_date:
        from datetime import datetime
        published_date = datetime.now().strftime("%Y-%m-%d")
    
    # 生成文件名
    filename = f"{published_date} - {safe_title}.md"
    
    return filename


def get_output_filename(url: str) -> str:
    """
    根据URL生成输出文件名
    """
    post_id = extract_post_id(url)
    return f"post_{post_id}.json"


def is_already_processed(url: str, output_dir: Path) -> bool:
    """
    检查URL是否已经被处理过（输出文件是否存在）
    """
    filename = get_output_filename(url)
    output_file = output_dir / filename
    return output_file.exists()


def process_post_images_obsidian(post_content: dict, base_url: str) -> dict:
    """处理主帖内容中的图片（Obsidian统一附件管理模式）"""
    if not post_content or 'content' not in post_content:
        return post_content
    
    processed_content = post_content.copy()
    processed_content['content'] = process_images_in_content_obsidian(
        post_content['content'], base_url
    )
    return processed_content


def process_comment_replies_images_obsidian(replies: list, base_url: str) -> list:
    """递归处理回复中的图片（Obsidian统一附件管理模式）"""
    processed_replies = []
    for reply in replies:
        processed_reply = reply.copy()
        if 'text' in reply:
            processed_reply['text'] = process_images_in_content_obsidian(
                reply['text'], base_url
            )
        # 递归处理嵌套回复
        if 'replies' in reply and reply['replies']:
            processed_reply['replies'] = process_comment_replies_images_obsidian(reply['replies'], base_url)
        processed_replies.append(processed_reply)
    return processed_replies


def process_comments_images_obsidian(comments: list, base_url: str) -> list:
    """处理评论中的图片（Obsidian统一附件管理模式）"""
    processed_comments = []
    for comment in comments:
        processed_comment = comment.copy()
        if 'text' in comment:
            processed_comment['text'] = process_images_in_content_obsidian(
                comment['text'], base_url
            )
        # 处理回复
        if 'replies' in comment and comment['replies']:
            processed_comment['replies'] = process_comment_replies_images_obsidian(comment['replies'], base_url)
        processed_comments.append(processed_comment)
    return processed_comments


def process_post_images(post_content: dict, base_url: str, images_folder: Path) -> dict:
    """处理主帖内容中的图片（向后兼容）"""
    if not post_content or 'content' not in post_content:
        return post_content
    
    processed_content = post_content.copy()
    processed_content['content'] = process_images_in_content(
        post_content['content'], base_url, images_folder
    )
    return processed_content


def process_comments_images(comments: list, base_url: str, images_folder: Path) -> list:
    """处理评论中的图片（向后兼容）"""
    processed_comments = []
    for comment in comments:
        processed_comment = comment.copy()
        if 'text' in comment:
            processed_comment['text'] = process_images_in_content(
                comment['text'], base_url, images_folder
            )
        # 处理回复（向后兼容）
        if 'replies' in comment and comment['replies']:
            processed_comment['replies'] = process_comments_images(comment['replies'], base_url, images_folder)
        processed_comments.append(processed_comment)
    return processed_comments


def render_comment_replies(replies: list, indent_level: int = 1) -> str:
    """递归渲染评论回复"""
    if not replies:
        return ""
    
    reply_content = []
    indent = "  " * indent_level  # 缩进表示层级
    
    for reply in replies:
        if 'author' in reply:
            reply_content.append(f"\n{indent}**{reply['author']}** 回复：\n\n")
        
        if 'text' in reply:
            reply_markdown = create_markdown_from_html(reply['text'])
            # 为回复内容添加缩进
            indented_reply = '\n'.join(f"{indent}{line}" for line in reply_markdown.split('\n'))
            reply_content.append(indented_reply)
        
        if 'timestamp' in reply:
            reply_content.append(f"\n{indent}*发布时间: {reply['timestamp']}*\n\n")
        
        # 递归处理嵌套回复
        if 'replies' in reply and reply['replies']:
            reply_content.append(render_comment_replies(reply['replies'], indent_level + 1))
    
    return ''.join(reply_content)


def generate_obsidian_markdown_file(post_content: dict, comments: list, url: str, markdown_file: Path):
    """生成完全符合Obsidian标准的Markdown文件，包含YAML frontmatter"""
    markdown_content = []
    
    # 生成YAML frontmatter
    yaml_frontmatter = generate_yaml_frontmatter(post_content, url)
    markdown_content.append(yaml_frontmatter)
    
    # 添加标题和主帖内容
    if post_content and 'content' in post_content:
        markdown_content.append("# 主帖内容\n\n")
        post_markdown = create_markdown_from_html(post_content['content'])
        markdown_content.append(post_markdown)
        markdown_content.append("\n---\n\n")
    
    # 添加评论
    if comments:
        markdown_content.append("## 评论\n\n")
        for i, comment in enumerate(comments, 1):
            if 'author' in comment:
                markdown_content.append(f"### {comment['author']}\n\n")
            
            if 'text' in comment:
                comment_markdown = create_markdown_from_html(comment['text'])
                markdown_content.append(comment_markdown)
            
            if 'timestamp' in comment:
                markdown_content.append(f"\n*发布时间: {comment['timestamp']}*\n\n")
            
            # 添加回复
            if 'replies' in comment and comment['replies']:
                markdown_content.append(render_comment_replies(comment['replies']))
            
            markdown_content.append("---\n\n")
    
    # 写入文件
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(''.join(markdown_content))


def generate_markdown_file(post_content: dict, comments: list, markdown_file: Path):
    """向后兼容的Markdown生成函数"""
    # 使用新的Obsidian兼容函数
    url = ""  # 旧版本没有URL参数，使用空值
    generate_obsidian_markdown_file(post_content, comments, url, markdown_file)


async def check_playwright_installation():
    """
    检查 Playwright 浏览器是否正确安装
    """
    browsers_to_check = [
        ('firefox', 'Firefox'),
        ('chromium', 'Chromium')
    ]
    
    available_browsers = []
    
    for browser_type, browser_name in browsers_to_check:
        try:
            async with async_playwright() as p:
                print(f"🔍 检查 {browser_name} 浏览器安装状态...")
                if browser_type == 'firefox':
                    browser = await p.firefox.launch(headless=True, timeout=15000)
                else:
                    browser = await p.chromium.launch(
                        headless=True, 
                        args=['--no-sandbox'], 
                        timeout=15000
                    )
                await browser.close()
                print(f"✅ {browser_name} 浏览器可用")
                available_browsers.append(browser_type)
        except Exception as e:
            print(f"❌ {browser_name} 浏览器不可用: {e}")
    
    if available_browsers:
        print(f"✅ 可用浏览器: {', '.join(available_browsers)}")
        return True
    else:
        print("❌ 没有可用的浏览器")
        print("💡 尝试运行: playwright install")
        return False


async def process_single_url(url: str) -> dict:
    """
    处理单个URL的完整流程
    """
    print(f"🔍 正在处理: {url}")
    
    # 尝试使用 Firefox 而不是 Chromium
    async with async_playwright() as p:
        # 1. 启动浏览器
        # macOS 优化的浏览器启动参数
        browser_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-web-security', 
            '--disable-extensions',
            '--no-first-run',
            '--disable-default-apps',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--enable-features=NetworkService,NetworkServiceInProcess',
            '--force-color-profile=srgb',
            '--disable-background-networking',
            '--disable-client-side-phishing-detection',
            '--disable-component-update',
            '--disable-sync',
            '--metrics-recording-only',
            '--no-default-browser-check',
            '--no-service-autorun',
            '--password-store=basic',
            '--use-mock-keychain'
        ]
        
        print("🚀 启动浏览器...")
        browser = None
        
        # 尝试不同的浏览器和参数组合
        browser_attempts = [
            # 尝试1: Firefox（通常比 Chromium 更稳定）
            {
                'type': 'firefox',
                'args': [],
                'headless': Config.HEADLESS,
                'name': 'Firefox'
            },
            # 尝试2: Chromium 最小参数
            {
                'type': 'chromium', 
                'args': ['--no-sandbox'],
                'headless': True,
                'name': 'Chromium (最小参数)'
            },
            # 尝试3: Chromium 完整参数
            {
                'type': 'chromium',
                'args': browser_args,
                'headless': Config.HEADLESS,
                'name': 'Chromium (完整参数)'
            }
        ]
        
        for i, attempt in enumerate(browser_attempts, 1):
            try:
                print(f"🔄 尝试启动 {attempt['name']} (方案 {i}/{len(browser_attempts)})")
                
                if attempt['type'] == 'firefox':
                    browser = await p.firefox.launch(
                        headless=attempt['headless'],
                        timeout=60000
                    )
                else:  # chromium
                    browser = await p.chromium.launch(
                        headless=attempt['headless'],
                        args=attempt['args'],
                        timeout=60000
                    )
                
                print(f"✅ {attempt['name']} 启动成功")
                break
                
            except Exception as e:
                print(f"❌ {attempt['name']} 启动失败: {e}")
                if i == len(browser_attempts):
                    raise Exception("所有浏览器启动尝试都失败了")
                continue
        
        try:
            # 2. 创建上下文（尝试使用已保存的会话）
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'ignore_https_errors': True
            }
            
            # 先检查会话文件是否有效
            if Config.AUTH_FILE.exists():
                print("📂 找到保存的登录状态，尝试使用...")
                try:
                    with open(Config.AUTH_FILE, 'r') as f:
                        storage_state = json.load(f)
                    context_options['storage_state'] = storage_state
                except Exception as e:
                    print(f"⚠️  会话文件读取失败，将重新登录: {e}")
                    if Config.AUTH_FILE.exists():
                        Config.AUTH_FILE.unlink()  # 删除损坏的会话文件
            
            print("🔧 创建浏览器上下文...")
            context = await browser.new_context(**context_options)
            print("✅ 浏览器上下文创建成功")
            
            print("📄 创建新页面...")
            # 增加重试机制
            page = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    page = await context.new_page()
                    print("✅ 页面创建成功")
                    break
                except Exception as e:
                    print(f"⚠️ 页面创建失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        print("🔄 等待后重试...")
                        await asyncio.sleep(2)
                    else:
                        raise Exception(f"页面创建失败，已重试{max_retries}次: {e}")
            
            if not page:
                raise Exception("页面创建失败")
            
            # 设置超时
            page.set_default_timeout(Config.TIMEOUT)
            
            # 3. 检查/执行登录
            login_needed = True
            if Config.AUTH_FILE.exists():
                print("🔍 检查登录状态...")
                login_needed = not await check_login_status(page, Config)
            
            if login_needed:
                print("🔑 需要重新登录...")
                login_success = await auto_login(page, Config)
                if not login_success:
                    raise Exception("登录失败")
            else:
                print("✅ 已登录状态有效")
            
            # 4. 访问目标URL
            print(f"📖 访问目标页面: {url}")
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # 5. Phase 4: 健壮的ID提取
            # 首先尝试从页面HTML中提取数字ID
            page_post_id = await extract_post_id_from_page(page)
            if page_post_id:
                print(f"✅ 从页面HTML提取到数字ID: {page_post_id}")
                unique_post_id = page_post_id
            else:
                # 如果页面中没找到，使用URL的安全ID
                unique_post_id = extract_post_id(url)
                print(f"🔧 使用URL安全ID: {unique_post_id}")
            
            # 6. 提取主帖内容
            from scraper import extract_post_content
            post_content = await extract_post_content(page)
            
            # 7. 加载所有评论
            await load_all_comments(page, Config)
            
            # 8. 提取评论数据
            comments = await extract_comments(page)
            
            # 9. Phase 4: 安全的文件命名系统
            
            # 确保输出目录存在
            OBSIDIAN_ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
            OBSIDIAN_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
            
            # 使用Obsidian统一附件管理模式处理图片
            processed_content = process_post_images_obsidian(post_content, url)
            processed_comments = process_comments_images_obsidian(comments, url)
            
            # Phase 4: 从页面内容获取可读标题（不从URL解码）
            page_title = processed_content.get('title', '') or 'Untitled Post'
            print(f"📝 页面标题: {page_title}")
            
            # Phase 4: 生成安全的文件名
            relative_time = processed_content.get('timestamp', '')
            published_date = parse_relative_time_to_date(relative_time)
            safe_markdown_filename = generate_safe_markdown_filename(page_title, published_date)
            print(f"📄 安全文件名: {safe_markdown_filename}")
            
            # Phase 4: 使用安全的文件名
            markdown_file = OBSIDIAN_ARTICLES_DIR / safe_markdown_filename
            
            # 生成完整的Obsidian兼容Markdown文件
            generate_obsidian_markdown_file(processed_content, processed_comments, url, markdown_file)
            
            # Phase 4: 使用唯一数字ID作为文件夹名（向后兼容）
            legacy_output_folder = Config.OUTPUT_DIR / unique_post_id
            legacy_output_folder.mkdir(parents=True, exist_ok=True)
            
            # 构建完整的输出数据
            output_data = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'post': processed_content,
                'total_comments': len(processed_comments),
                'comments': processed_comments
            }
            
            # 保存JSON数据（向后兼容）
            json_file = legacy_output_folder / 'data.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # 报告输出结果
            print(f"✅ Obsidian文件已保存: {markdown_file.name}")
            print(f"📊 抓取到 {output_data['total_comments']} 条评论")
            print(f"📁 输出位置:")
            print(f"   📄 Obsidian文章: {markdown_file}")
            print(f"   📦 原始数据: {json_file}")
            
            if OBSIDIAN_ATTACHMENTS_DIR.exists() and any(OBSIDIAN_ATTACHMENTS_DIR.iterdir()):
                image_count = len(list(OBSIDIAN_ATTACHMENTS_DIR.glob('*')))
                print(f"🖼️  统一附件库: {image_count} 个图片")
            
            return output_data
            
        except Exception as e:
            print(f"❌ 处理过程中发生错误: {e}")
            raise
        finally:
            try:
                print("🔄 正在关闭浏览器...")
                await browser.close()
                print("✅ 浏览器已关闭")
            except Exception as e:
                print(f"⚠️  关闭浏览器时出错: {e}")


async def main():
    """
    主函数：从test_urls.txt读取URL并处理
    """
    try:
        # 检查 Playwright 安装
        if not await check_playwright_installation():
            print("❌ 请先安装 Playwright 浏览器")
            print("运行命令: playwright install chromium")
            return
        
        # 验证配置
        print("🔧 验证配置...")
        Config.validate()
        print("✅ 配置验证通过")
        
        # 读取测试URL
        # 优先使用test_fresh.txt进行新测试
        test_urls_file = Path('test_fresh.txt')
        if not test_urls_file.exists():
            test_urls_file = Path('test_enhanced.txt')
        if not test_urls_file.exists():
            test_urls_file = Path('test_fix.txt')
        if not test_urls_file.exists():
            test_urls_file = Path('test_urls.txt')
            
        if not test_urls_file.exists():
            print("❌ test_urls.txt 文件不存在")
            print("请创建 test_urls.txt 文件并添加要抓取的URL")
            return
        
        with open(test_urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        if not urls:
            print("❌ test_urls.txt 中没有有效的URL")
            return
        
        print(f"📋 找到 {len(urls)} 个URL待处理")
        
        # 检查每个URL的处理状态
        urls_to_process = []
        skipped_count = 0
        
        for url in urls:
            if is_already_processed(url, Config.OUTPUT_DIR):
                post_id = extract_post_id(url)
                print(f"⏭️ 跳过已处理的帖子: {post_id} (文件已存在)")
                skipped_count += 1
            else:
                urls_to_process.append(url)
        
        if skipped_count > 0:
            print(f"� 跳过了 {skipped_count} 个已处理的URL")
        
        if not urls_to_process:
            print("✅ 所有URL都已处理完成，无需重新抓取")
            return
            
        print(f"🎯 需要处理 {len(urls_to_process)} 个新URL")
        
        # 循环处理所有未处理的URL
        successful_count = 0
        failed_count = 0
        
        for i, url in enumerate(urls_to_process, 1):
            try:
                post_id = extract_post_id(url)
                print(f"\n🚀 开始处理第 {i}/{len(urls_to_process)} 个URL...")
                print(f"🔍 正在处理帖子: {post_id}")
                print(f"🌐 URL: {url}")
                
                result = await process_single_url(url)
                
                print(f"\n✅ 帖子 {post_id} 处理完成！")
                print(f"   评论数: {result['total_comments']}")
                print(f"   保存文件: {get_output_filename(url)}")
                
                successful_count += 1
                
                # 如果还有更多URL要处理，短暂等待
                if i < len(urls_to_process):
                    print("⏳ 等待2秒后处理下一个URL...")
                    await asyncio.sleep(2)
                    
            except Exception as e:
                post_id = extract_post_id(url)
                print(f"\n❌ 处理帖子 {post_id} 时发生错误: {e}")
                failed_count += 1
                
                # 继续处理下一个URL
                continue
        
        # 显示最终统计
        print(f"\n🎉 批量处理完成！")
        print(f"📊 统计信息:")
        print(f"   ✅ 成功处理: {successful_count} 个")
        print(f"   ❌ 处理失败: {failed_count} 个")
        print(f"   ⏭️ 已跳过: {skipped_count} 个")
        print(f"   📁 Obsidian文章目录: {OBSIDIAN_ARTICLES_DIR}")
        print(f"   🖼️  Obsidian附件目录: {OBSIDIAN_ATTACHMENTS_DIR}")
        print(f"   📦 原始数据目录: {Config.OUTPUT_DIR}")
        print(f"\n🚀 文件已准备好导入Obsidian知识库！")
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序执行错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置事件循环策略（在某些系统上可能需要）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
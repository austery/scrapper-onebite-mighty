"""
主程序入口
"""
import json
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

from config import Config
from login import auto_login, check_login_status
from scraper import load_all_comments, extract_comments
import re


def extract_post_id(url: str) -> str:
    """
    从OneNewBite URL中提取帖子ID
    例如: https://onenewbite.com/posts/43168058 -> 43168058
    """
    from urllib.parse import unquote
    
    # 尝试从URL中匹配数字ID
    match = re.search(r'/posts/(\d+)', url)
    if match:
        return match.group(1)
    
    # 如果没找到数字ID，使用URL的最后一部分
    parts = url.rstrip('/').split('/')
    if parts:
        post_part = parts[-1]
        # URL解码，处理中文字符
        decoded_part = unquote(post_part)
        # 如果解码后的字符串太长，使用原始字符串
        if len(decoded_part) <= 50:
            return decoded_part
        else:
            return post_part
    
    # 如果都失败了，使用时间戳作为后备
    return str(int(time.time()))


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
            
            # 5. 提取主帖内容
            from scraper import extract_post_content
            post_content = await extract_post_content(page)
            
            # 6. 加载所有评论
            await load_all_comments(page, Config)
            
            # 7. 提取评论数据
            comments = await extract_comments(page)
            
            # 8. 保存为JSON
            output_data = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'post': post_content,
                'total_comments': len(comments),
                'comments': comments
            }
            
            # 使用新的文件名生成规则
            filename = get_output_filename(url)
            output_file = Config.OUTPUT_DIR / filename
            
            # 确保输出目录存在
            Config.OUTPUT_DIR.mkdir(exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已保存到: {output_file}")
            print(f"📊 抓取到 {output_data['total_comments']} 条评论")
            
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
        # 优先使用test_enhanced.txt进行测试，然后test_fix.txt，最后test_urls.txt
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
        print(f"   📁 输出目录: {Config.OUTPUT_DIR}")
            
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
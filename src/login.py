"""
自动登录和会话管理
"""
import asyncio
import json
from pathlib import Path


async def auto_login(page, config):
    """
    自动登录流程 - 针对 OneNewBite 网站优化
    Returns: bool - 登录是否成功
    """
    try:
        print("🔑 开始登录 OneNewBite...")
        
        # 1. 访问主页
        print("📖 访问网站主页...")
        await page.goto(config.SITE_URL)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        
        # 2. 查找并点击 "Sign In" 按钮
        print("🔍 查找 Sign In 按钮...")
        
        sign_in_clicked = False
        
        # OneNewBite 的 Sign In 按钮选择器 - 优先使用最可能的选择器
        sign_in_selectors = [
            'text="Sign In"',  # Playwright 的文本选择器
            'button:has-text("Sign In")',  # 按钮包含 Sign In 文本
            'a:has-text("Sign In")',  # 链接包含 Sign In 文本  
            '[role="button"]:has-text("Sign In")',  # 任何作为按钮的元素
            'a[href*="/sign_in"]',  # 基于 URL 路径
            '.sign-in-btn',  # 可能的类名
            '#sign-in-button'  # 可能的ID
        ]
        
        for selector in sign_in_selectors:
            try:
                print(f"🔍 尝试选择器: {selector}")
                sign_in_element = page.locator(selector).first
                
                # 等待元素出现
                await sign_in_element.wait_for(state='visible', timeout=5000)
                
                if await sign_in_element.is_visible():
                    print(f"✅ 找到 Sign In 按钮: {selector}")
                    await sign_in_element.click()
                    print("🔄 点击 Sign In 按钮，等待页面加载...")
                    await page.wait_for_load_state('networkidle')
                    await page.wait_for_timeout(3000)
                    sign_in_clicked = True
                    break
            except Exception as e:
                print(f"⚠️ 选择器 {selector} 失败: {e}")
                continue
        
        # 如果没有点击成功，直接访问登录页面  
        if not sign_in_clicked:
            print("🔄 未找到 Sign In 按钮，直接访问登录页面...")
            await page.goto("https://onenewbite.com/sign_in")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(2000)
        
        # 调试：截图查看当前状态
        try:
            await page.screenshot(path="debug_login_page.png")
            print("📷 已保存登录页面截图: debug_login_page.png")
            print(f"🌐 当前登录页面URL: {page.url}")
            print(f"📄 当前登录页面标题: {await page.title()}")
            
            # 检查登录表单是否存在
            email_inputs = await page.locator('input[type="email"], input[name="email"]').count()
            password_inputs = await page.locator('input[type="password"]').count()
            print(f"📧 找到 {email_inputs} 个email输入框")
            print(f"🔐 找到 {password_inputs} 个password输入框")
        except Exception as e:
            print(f"调试截图失败: {e}")
        
        # 3. 等待登录表单出现并填写 EMAIL
        print("📝 查找并填写 email 字段...")
        
        # 确保我们有 email 地址 (从环境变量的 USERNAME 读取，它实际上应该是 email)
        email_address = config.USERNAME
        if not email_address:
            print("❌ 环境变量中未找到 USERNAME (email)，请在 .env 文件中设置")
            return False
            
        print(f"📧 使用 email: {email_address}")
        
        email_filled = False
        
        # OneNewBite 的 email 输入框选择器
        email_selectors = [
            'input[name="email"]',  # 最常见的
            'input[type="email"]',  # HTML5 email 类型
            'input[id="email"]',    # 可能的 ID
            'input[placeholder*="email" i]',  # 占位符包含 email
            'input[placeholder*="Email" i]',  # 占位符包含 Email (大写)
            'input[name="user_email"]',  # 可能的变体
            'input[name="login"]',   # 可能用作登录字段
            '#user_email',  # 可能的 ID 变体
            '.email-input'  # 可能的类名
        ]
        
        for selector in email_selectors:
            try:
                print(f"🔍 尝试 email 选择器: {selector}")
                email_input = page.locator(selector).first
                
                # 等待元素出现
                await email_input.wait_for(state='visible', timeout=5000)
                
                if await email_input.is_visible():
                    print(f"✅ 找到 email 输入框: {selector}")
                    await email_input.clear()  # 清空可能存在的内容
                    await email_input.fill(email_address)
                    await page.wait_for_timeout(500)
                    
                    # 验证填写成功
                    filled_value = await email_input.input_value()
                    if filled_value == email_address:
                        print("✅ Email 填写成功")
                        email_filled = True
                        break
                    else:
                        print(f"⚠️ Email 填写验证失败: 期望 '{email_address}', 实际 '{filled_value}'")
                        
            except Exception as e:
                print(f"⚠️ email 选择器 {selector} 失败: {e}")
                continue
        
        if not email_filled:
            print("❌ 未找到或填写 email 输入框失败")
            return False
        
        # 4. 填写密码
        print("🔐 查找并填写 password 字段...")
        
        # 确保我们有密码 (从环境变量读取)
        password = config.PASSWORD
        if not password:
            print("❌ 环境变量中未找到 PASSWORD，请在 .env 文件中设置")
            return False
            
        print("🔐 密码已从环境变量读取")
        
        password_filled = False
        
        # OneNewBite 的 password 输入框选择器
        password_selectors = [
            'input[name="password"]',  # 最常见的
            'input[type="password"]',  # HTML 密码类型
            'input[id="password"]',    # 可能的 ID
            'input[placeholder*="password" i]',  # 占位符包含 password
            'input[placeholder*="Password" i]',  # 占位符包含 Password (大写)
            'input[name="user_password"]',  # 可能的变体
            '#user_password',  # 可能的 ID 变体
            '.password-input'  # 可能的类名
        ]
        
        for selector in password_selectors:
            try:
                print(f"🔍 尝试 password 选择器: {selector}")
                password_input = page.locator(selector).first
                
                # 等待元素出现
                await password_input.wait_for(state='visible', timeout=5000)
                
                if await password_input.is_visible():
                    print(f"✅ 找到 password 输入框: {selector}")
                    await password_input.clear()  # 清空可能存在的内容
                    await password_input.fill(password)
                    await page.wait_for_timeout(500)
                    
                    # 验证填写成功 (不显示密码内容，只检查长度)
                    filled_value = await password_input.input_value()
                    if len(filled_value) == len(password):
                        print("✅ Password 填写成功")
                        password_filled = True
                        break
                    else:
                        print(f"⚠️ Password 填写验证失败: 长度不匹配")
                        
            except Exception as e:
                print(f"⚠️ password 选择器 {selector} 失败: {e}")
                continue
        
        if not password_filled:
            print("❌ 未找到或填写 password 输入框失败")
            return False
        
        # 5. 点击登录按钮
        print("🚀 查找并点击登录按钮...")
        login_button_clicked = False
        
        # 尝试多种可能的登录按钮选择器
        login_button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Sign In")',
            'button:has-text("Sign in")',
            'button:has-text("Login")',
            'button:has-text("登录")',
            'button:has-text("提交")',
            '.login-button',
            '.signin-button',
            '#login-button',
            '#signin-button',
            '[data-testid="login-button"]',
            '[data-testid="signin-button"]'
        ]
        
        for selector in login_button_selectors:
            try:
                login_button = page.locator(selector)
                if await login_button.is_visible():
                    print(f"✅ 找到登录按钮: {selector}")
                    await login_button.click()
                    login_button_clicked = True
                    break
            except Exception as e:
                print(f"⚠️ 尝试登录按钮选择器 {selector} 失败: {e}")
                continue
        
        if not login_button_clicked:
            print("❌ 未找到登录按钮，尝试按 Enter 键...")
            await page.keyboard.press('Enter')
        
        # 6. 等待页面跳转或加载
        print("⏳ 等待登录完成...")
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(3000)
        
                # 7. 验证登录成功
        print("🔍 验证登录是否成功...")
        await page.wait_for_timeout(3000)  # 等待页面稳定和重定向
        
        # 检查当前页面状态
        current_url = page.url
        current_title = await page.title()
        print(f"📄 当前页面: {current_url}")
        print(f"📝 页面标题: {current_title}")
        
        login_success = False
        
        # 第一步：检查是否已经离开登录页面
        if not ('sign_in' in current_url or 'login' in current_url):
            print("✅ 已离开登录页面")
            login_success = True
        
        # 第二步：检查 OneNewBite 特有的登录成功指示器
        if not login_success:
            success_indicators = [
                # 用户相关元素
                '.user-avatar', '.profile', '.user-menu', '.account-menu',
                # 导航相关
                'a[href*="/profile"]', 'a[href*="/dashboard"]', 'a[href*="/account"]',
                # 退出登录相关
                'a[href*="logout"]', 'a[href*="sign_out"]', 'text="Logout"', 'text="Sign Out"',
                # 可能的用户信息显示
                '.username', '.user-name', '.current-user',
                # OneNewBite 特有的元素
                '.navigation', '.main-nav', '.header-user'
            ]
            
            for indicator in success_indicators:
                try:
                    element = page.locator(indicator).first
                    if await element.is_visible():
                        print(f"✅ 找到登录成功指示器: {indicator}")
                        login_success = True
                        break
                except Exception:
                    continue
        
        # 第三步：检查页面内容变化
        if not login_success:
            # 如果没有找到特定指示器，但URL已经改变且不包含登录相关词汇，认为可能成功
            if (current_url != "https://onenewbite.com/sign_in" and 
                'sign_in' not in current_url and 
                'login' not in current_url.lower()):
                print(f"✅ URL变化显示可能登录成功: {current_url}")
                login_success = True
        
        if login_success:
            print("🎉 登录成功！")
            # 8. 保存会话状态
            print("💾 保存登录状态...")
            await page.context.storage_state(path=str(config.AUTH_FILE))
            return True
        else:
            print("❌ 登录失败，请检查凭据或网站变化")
            # 截图以便调试
            try:
                await page.screenshot(path="login_failed.png")
                print("📷 已保存登录失败截图: login_failed.png")
            except:
                pass
            return False
            
    except Exception as e:
        print(f"❌ 登录过程发生错误: {e}")
        return False


async def check_login_status(page, config):
    """
    检查登录状态是否有效 - 针对 OneNewBite 优化
    Returns: bool
    """
    try:
        print("🔍 检查当前登录状态...")
        
        # 访问网站主页
        await page.goto(config.SITE_URL)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        
        current_url = page.url
        print(f"📄 检查页面: {current_url}")
        
        # 方法1: 检查是否有登录指示器
        success_indicators = [
            # 用户相关
            '.user-avatar', '.profile', '.user-menu', '.account-menu',
            # 退出登录
            'a[href*="logout"]', 'a[href*="sign_out"]', 'text="Logout"', 'text="Sign Out"',
            # 用户信息
            '.username', '.user-name', '.current-user',
            # OneNewBite 可能的导航元素
            '.navigation', '.main-nav', '.header-user'
        ]
        
        for indicator in success_indicators:
            try:
                element = page.locator(indicator).first
                if await element.is_visible():
                    print(f"✅ 找到登录状态指示器: {indicator}")
                    return True
            except Exception:
                continue
        
        # 方法2: 检查是否被重定向到登录页面
        if 'sign_in' in current_url or 'login' in current_url.lower():
            print("❌ 已被重定向到登录页面，需要重新登录")
            return False
        
        # 方法3: 尝试访问需要登录的页面来测试
        try:
            # 如果当前就在主页且没有被重定向到登录，可能已登录
            if current_url == config.SITE_URL or 'onenewbite.com' in current_url:
                # 查找 "Sign In" 按钮，如果找到说明未登录
                sign_in_buttons = await page.locator('text="Sign In"').count()
                if sign_in_buttons > 0:
                    print("❌ 页面显示 Sign In 按钮，需要登录")
                    return False
                else:
                    print("✅ 页面无 Sign In 按钮，可能已登录")
                    return True
        except Exception:
            pass
        
        # 默认认为需要重新登录
        print("❓ 无法确定登录状态，建议重新登录")
        return False
            
    except Exception as e:
        print(f"❌ 检查登录状态时发生错误: {e}")
        return False
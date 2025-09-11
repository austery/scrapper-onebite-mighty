#!/usr/bin/env python3
"""
网站可用性测试脚本
测试 OneNewBite 网站当前是否可以访问帖子内容
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def test_site_accessibility():
    """
    测试网站可访问性
    """
    print("🧪 OneNewBite 网站可用性测试")
    print("=" * 50)
    
    test_url = "https://onenewbite.com/posts/43168058"
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"📖 访问帖子页面: {test_url}")
            await page.goto(test_url)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)
            
            # 检查页面标题
            title = await page.title()
            print(f"📄 页面标题: {title}")
            
            # 检查当前URL
            current_url = page.url
            print(f"🌐 当前URL: {current_url}")
            
            # 检查是否被重定向到登录/landing页面
            if 'login' in current_url or 'landing' in current_url:
                print("⚠️  页面被重定向到登录/landing页面")
                print("🔒 需要登录才能访问内容")
                
                # 截图保存
                await page.screenshot(path="test_post_access.png")
                print("📷 已保存截图: test_post_access.png")
                
            else:
                print("✅ 可以直接访问帖子内容！")
                
                # 查找评论区
                try:
                    comments_section = page.locator('#sidebar-comments-region, .comments, [class*="comment"]')
                    if await comments_section.count() > 0:
                        print("💬 找到评论区域")
                        comments_count = await comments_section.count()
                        print(f"📊 评论区域数量: {comments_count}")
                    else:
                        print("❌ 未找到评论区域")
                        
                    # 截图保存
                    await page.screenshot(path="test_post_access.png")
                    print("📷 已保存截图: test_post_access.png")
                    
                except Exception as e:
                    print(f"⚠️  检查评论区域时出错: {e}")
                    
        except Exception as e:
            print(f"❌ 访问失败: {e}")
            
        finally:
            await browser.close()

async def test_login_page():
    """
    测试登录页面状态
    """
    print("\n🔑 登录页面状态测试")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("📖 访问登录页面...")
            await page.goto("https://onenewbite.com/sign_in")
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)
            
            title = await page.title()
            current_url = page.url
            
            print(f"📄 页面标题: {title}")
            print(f"🌐 当前URL: {current_url}")
            
            # 检查是否有登录表单
            email_input = page.locator('input[type="email"], input[name="email"]')
            password_input = page.locator('input[type="password"], input[name="password"]')
            
            email_count = await email_input.count()
            password_count = await password_input.count()
            
            print(f"📧 Email输入框数量: {email_count}")
            print(f"🔐 Password输入框数量: {password_count}")
            
            if email_count > 0 and password_count > 0:
                print("✅ 登录表单可用！")
            else:
                print("❌ 登录表单不可用")
                
            # 截图保存
            await page.screenshot(path="test_login_page.png")
            print("📷 已保存截图: test_login_page.png")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            
        finally:
            await browser.close()

async def main():
    """
    运行所有测试
    """
    await test_site_accessibility()
    await test_login_page()
    
    print("\n🎯 测试总结")
    print("=" * 50)
    print("请查看生成的截图来了解网站当前状态：")
    print("- test_post_access.png: 帖子页面访问状态")
    print("- test_login_page.png: 登录页面状态")

if __name__ == "__main__":
    asyncio.run(main())
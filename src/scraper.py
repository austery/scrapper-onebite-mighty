"""
评论抓取核心模块
"""
import asyncio
import re
from typing import List, Dict, Any


# 关键选择器 - 基于实际网站结构（OneNewBite）
SELECTORS = {
    # 锚点：评论区容器
    'COMMENT_CONTAINER': '#sidebar-comments-region',
    
    # Previous Comments 按钮 - 根据用户提供的实际选择器
    'PREVIOUS_COMMENTS_BUTTON': '#sidebar-comments-region > div > div.comments-region > div > div.load-more-wrapper-previous > a',
    
    # More 展开链接 - 展开被折叠的长评论（避免使用 nth-child）
    'EXPAND_MORE_LINKS': '#sidebar-comments-region .comment-body.mighty-wysiwyg-content.fr-view.wysiwyg-comment.long.is-truncated > a',
    
    # 更通用的 More 链接选择器作为备选
    'EXPAND_LINKS_FALLBACK': 'a.more.text-color-grey-3-link',
    
    # 评论项（在容器内查找）
    'COMMENT_ITEMS': 'li',  # 必须在COMMENT_CONTAINER内使用
    
    # 评论区域选择器
    'COMMENTS_REGION': '.comments-region',
    'COMMENT_BODY_CONTAINER': '.comment-body-container',
    'COMMENT_BODY_TRUNCATED': '.comment-body.is-truncated'
}


async def debug_page_structure(page):
    """
    调试函数：分析页面结构，帮助找到正确的选择器
    """
    print("🔍 调试: 分析页面结构...")
    
    try:
        # 检查评论区是否存在
        comment_region = page.locator('#sidebar-comments-region')
        if await comment_region.count() > 0:
            print("✅ 找到评论区容器")
            
            # 检查 Previous Comments 按钮
            prev_buttons = await page.locator('a:has-text("Previous Comments")').count()
            print(f"📄 Previous Comments 按钮数量: {prev_buttons}")
            
            # 检查 More 链接
            more_links_1 = await page.locator('a:has-text("more")').count()
            more_links_2 = await page.locator('a.more').count()
            print(f"📄 More 链接数量 (文本匹配): {more_links_1}")
            print(f"📄 More 链接数量 (类选择器): {more_links_2}")
            
            # 检查评论项
            comment_items = await comment_region.locator('li').count()
            print(f"📄 评论项数量: {comment_items}")
            
        else:
            print("❌ 未找到评论区容器")
            
    except Exception as e:
        print(f"调试过程出错: {e}")


async def load_all_comments(page, config):
    """
    双循环加载策略
    Phase 1: 循环点击"Previous Comments"直到全部加载
    Phase 2: 循环点击所有"more"链接直到全部展开
    """
    print("开始加载所有评论...")
    
    # 先进行调试分析
    await debug_page_structure(page)
    
    # Phase 1: 加载 Previous Comments（往前加载更早的评论）
    print("Phase 1: 加载 Previous Comments...")
    
    previous_comments_count = 0
    max_attempts = 20  # 防止无限循环
    
    for attempt in range(max_attempts):
        try:
            # 使用精确的选择器查找 Previous Comments 按钮
            previous_button = page.locator(SELECTORS['PREVIOUS_COMMENTS_BUTTON'])
            
            # 检查按钮是否存在且可见
            if await previous_button.count() > 0 and await previous_button.is_visible():
                print(f"  找到 Previous Comments 按钮，准备点击...")
                
                # 确保按钮可以点击
                await previous_button.wait_for(state='visible', timeout=5000)
                await previous_button.scroll_into_view_if_needed()
                await page.wait_for_timeout(1000)  # 等待页面稳定
                
                # 点击按钮
                await previous_button.click()
                previous_comments_count += 1
                print(f"    已点击 Previous Comments {previous_comments_count} 次")
                
                # 等待新内容加载
                await page.wait_for_load_state('networkidle', timeout=10000)
                await page.wait_for_timeout(config.WAIT_TIME)
                
            else:
                print(f"  没有更多 Previous Comments 按钮，共加载了 {previous_comments_count} 页")
                break
                
        except Exception as e:
            print(f"  Previous Comments 加载出错 (尝试 {attempt + 1}): {e}")
            if previous_comments_count > 0:
                print(f"  已成功加载 {previous_comments_count} 页，继续下一阶段")
            break
    
    print(f"  Phase 1 完成: 加载了 {previous_comments_count} 页 Previous Comments")
    
    # Phase 2: 展开所有折叠的评论内容（More 链接）
    print("Phase 2: 展开所有折叠的评论内容...")
    expand_count = 0
    max_iterations = 10  # 防止无限循环
    iteration = 0
    
    while iteration < max_iterations:
        try:
            # 使用更精确的选择器查找 More 链接
            more_links = []
            
            # 尝试主要的 More 链接选择器
            primary_links = await page.locator(SELECTORS['EXPAND_MORE_LINKS']).all()
            more_links.extend(primary_links)
            
            # 如果主要选择器没找到，尝试备选选择器
            if not more_links:
                fallback_links = await page.locator(SELECTORS['EXPAND_LINKS_FALLBACK']).all()
                more_links.extend(fallback_links)
            
            if not more_links:
                print(f"  没有找到更多折叠内容，共展开了 {expand_count} 项")
                break
                
            print(f"  找到 {len(more_links)} 个折叠内容")
            
            # 逐个点击展开链接
            links_clicked = 0
            for i, link in enumerate(more_links):
                try:
                    # 检查链接是否可见
                    if await link.is_visible():
                        print(f"    准备点击第 {i+1} 个 More 链接...")
                        
                        # 滚动到元素
                        await link.scroll_into_view_if_needed()
                        await page.wait_for_timeout(1000)
                        
                        # 尝试多种点击方式
                        click_success = False
                        
                        # 方法1: 普通点击
                        try:
                            await link.click(timeout=3000, force=True)
                            click_success = True
                            print(f"    ✅ 方法1成功点击第 {i+1} 个 More 链接")
                        except Exception:
                            pass
                        
                        # 方法2: JavaScript 点击
                        if not click_success:
                            try:
                                await link.evaluate("element => element.click()")
                                click_success = True
                                print(f"    ✅ 方法2成功点击第 {i+1} 个 More 链接")
                            except Exception:
                                pass
                        
                        # 方法3: 触发事件
                        if not click_success:
                            try:
                                await link.dispatch_event('click')
                                click_success = True
                                print(f"    ✅ 方法3成功点击第 {i+1} 个 More 链接")
                            except Exception:
                                pass
                        
                        if click_success:
                            links_clicked += 1
                            expand_count += 1
                            # 等待内容展开
                            await page.wait_for_timeout(1500)
                        else:
                            print(f"    ❌ 所有方法都无法点击第 {i+1} 个 More 链接")
                            
                    else:
                        print(f"    ⚠️ 第 {i+1} 个链接不可见，跳过")
                        
                except Exception as e:
                    print(f"    ❌ 处理第 {i+1} 个 More 链接时出错: {str(e)[:100]}...")
                    continue
            
            if links_clicked == 0:
                print(f"  本轮没有成功点击任何链接，结束展开")
                break
                
            print(f"  本轮成功展开 {links_clicked} 个折叠内容")
            
            # 等待页面稳定
            await page.wait_for_timeout(config.WAIT_TIME)
            
            # 检查是否还有新的 More 链接出现
            # 如果连续几轮点击数量相同，可能说明页面没有新内容加载
            if iteration > 2 and links_clicked == len(more_links):
                print(f"  检测到可能的重复点击，尝试额外等待...")
                await page.wait_for_timeout(2000)
                
                # 重新检查是否有新的链接
                new_more_links = await page.locator(SELECTORS['EXPAND_MORE_LINKS']).count()
                fallback_links = await page.locator(SELECTORS['EXPAND_LINKS_FALLBACK']).count()
                total_new_links = new_more_links + fallback_links
                
                if total_new_links <= len(more_links):
                    print(f"  没有检测到新的 More 链接，结束展开")
                    break
            
            iteration += 1
            
        except Exception as e:
            print(f"  展开折叠内容时发生错误: {e}")
            break
    
    print(f"评论加载完成！共展开了 {expand_count} 项折叠内容")


async def extract_post_content(page) -> Dict[str, Any]:
    """
    提取主帖内容
    Returns: Dict - 主帖数据
    """
    print("开始提取主帖内容...")
    
    post_data = {
        'title': '',
        'content': '',
        'author': '',
        'timestamp': '',
        'url': page.url
    }
    
    try:
        # 尝试提取帖子标题
        title_selectors = [
            'h1',
            '.post-title',
            '.article-title',
            '[data-testid="post-title"]'
        ]
        
        for selector in title_selectors:
            try:
                title_element = page.locator(selector).first
                if await title_element.count() > 0:
                    post_data['title'] = await title_element.text_content()
                    print(f"✅ 找到标题: {post_data['title'][:50]}...")
                    break
            except:
                continue
        
        # 尝试提取帖子内容 - 使用用户提供的准确选择器
        content_selectors = [
            '#detail-layout > div.detail-layout-content-wrapper > div.detail-layout-description.mighty-wysiwyg-content.mighty-max-content-width.fr-view',
            '.detail-layout-description.mighty-wysiwyg-content',
            '.detail-layout-description',
            '.mighty-wysiwyg-content',
            '.post-content .content',
            '.post-content',
            '.post-body .content',
            '.post-body',
            '[data-testid="post-content"]',
            '.main-post .content',
            '.content',
            '.main-content',
            '[class*="content"]'
        ]
        
        for selector in content_selectors:
            try:
                content_element = page.locator(selector).first
                if await content_element.count() > 0:
                    content_text = await content_element.text_content()
                    if content_text and len(content_text.strip()) > 20:  # 确保不是空内容
                        post_data['content'] = content_text.strip()
                        print(f"✅ 找到内容: {post_data['content'][:100]}...")
                        break
            except:
                continue
        
        # 尝试提取作者信息
        author_selectors = [
            '.post-author',
            '.author-name',
            '.user-name',
            '[data-testid="author"]'
        ]
        
        for selector in author_selectors:
            try:
                author_element = page.locator(selector).first
                if await author_element.count() > 0:
                    post_data['author'] = await author_element.text_content()
                    print(f"✅ 找到作者: {post_data['author']}")
                    break
            except:
                continue
        
        # 尝试提取发布时间
        time_selectors = [
            '.post-time',
            '.timestamp',
            '.published-date',
            'time'
        ]
        
        for selector in time_selectors:
            try:
                time_element = page.locator(selector).first
                if await time_element.count() > 0:
                    post_data['timestamp'] = await time_element.text_content()
                    print(f"✅ 找到时间: {post_data['timestamp']}")
                    break
            except:
                continue
        
        return post_data
        
    except Exception as e:
        print(f"❌ 提取主帖内容时出错: {e}")
        return post_data


async def extract_comments(page) -> List[Dict[str, Any]]:
    """
    提取评论数据，保持正确的层级结构
    Returns: List[Dict] - 评论数据结构，只包含根评论，回复嵌套在内
    """
    print("开始提取评论数据...")
    
    try:
        # 定位评论容器
        container = page.locator('#sidebar-comments-region')
        
        if not await container.is_visible():
            print("❌ 未找到评论区容器")
            return []
        
        # 使用更精确的方法来查找根级评论
        # 首先尝试直接定位根级评论
        root_comment_items = await container.locator('> div > div.comments-region > ul > li').all()
        
        if not root_comment_items:
            # 备用方法：查找所有 li，但要过滤出根级评论
            all_items = await container.locator('li').all()
            print(f"找到 {len(all_items)} 个总评论项，开始过滤根级评论...")
            
            # 过滤根级评论：检查每个 li 是否有嵌套的 ul（说明它有回复）
            # 或者检查它是否在另一个 li 内部（说明它是回复）
            root_comment_items = []
            for item in all_items:
                try:
                    # 检查这个评论是否在另一个 li 的 ul 内部（即是回复）
                    parent_li = item.locator('xpath=ancestor::li[1]')  
                    if await parent_li.count() == 0:  # 没有父级 li，说明是根评论
                        root_comment_items.append(item)
                except:
                    # 如果检查失败，保险起见加入到根评论中
                    root_comment_items.append(item)
            
            print(f"过滤后得到 {len(root_comment_items)} 个根级评论")
        
        print(f"准备处理 {len(root_comment_items)} 个评论项")
        
        root_comments = []
        
        for i, item in enumerate(root_comment_items):
            try:
                print(f"  处理评论 {i+1}...")
                comment_data = await extract_single_comment_with_replies(item)
                if comment_data and comment_data.get('text', '').strip():
                    root_comments.append(comment_data)
                    print(f"    ✅ 评论 {i+1} 处理完成")
                else:
                    print(f"    ⚠️ 评论 {i+1} 内容为空，跳过")
                    
            except Exception as e:
                print(f"    ❌ 处理评论 {i+1} 时出错: {e}")
                continue
        
        print(f"✅ 成功提取 {len(root_comments)} 条根评论")
        return root_comments
        
    except Exception as e:
        print(f"❌ 提取评论数据时发生错误: {e}")
        return []


async def extract_single_comment_with_replies(item) -> Dict[str, Any]:
    """
    提取单个评论及其回复的数据
    """
    comment_data = {
        'text': '',
        'author': '',
        'timestamp': '',
        'replies': []
    }
    
    try:
        # 提取主评论文本 - 只提取当前层级的内容，不包括回复
        comment_body = item.locator('.comment-body').first
        if await comment_body.count() > 0:
            # 获取评论文本，但排除嵌套的回复内容
            comment_text = await comment_body.text_content()
            comment_data['text'] = clean_comment_text(comment_text)
        
        # 提取作者信息
        author_selectors = [
            '.comment-author',
            '.user-name', 
            '.author-name',
            '.comment-header .name'
        ]
        
        for selector in author_selectors:
            try:
                author_element = item.locator(selector).first
                if await author_element.count() > 0:
                    comment_data['author'] = await author_element.text_content()
                    break
            except:
                continue
        
        # 提取时间戳
        time_selectors = [
            '.timestamp',
            '.comment-time',
            '.time-ago',
            'time'
        ]
        
        for selector in time_selectors:
            try:
                time_element = item.locator(selector).first
                if await time_element.count() > 0:
                    comment_data['timestamp'] = await time_element.text_content()
                    break
            except:
                continue
        
        # 提取回复 - 查找嵌套的 ul > li 结构
        try:
            replies_container = item.locator('ul li')  # 直接子级的回复
            if await replies_container.count() > 0:
                reply_items = await replies_container.all()
                print(f"    找到 {len(reply_items)} 个回复")
                
                for reply_item in reply_items:
                    reply_data = await extract_single_reply(reply_item)
                    if reply_data and reply_data.get('text', '').strip():
                        comment_data['replies'].append(reply_data)
        except Exception as e:
            print(f"    提取回复时出错: {e}")
        
        return comment_data
        
    except Exception as e:
        print(f"    提取评论数据时出错: {e}")
        return comment_data


async def extract_single_reply(item) -> Dict[str, Any]:
    """
    提取单个回复的数据
    """
    reply_data = {
        'text': '',
        'author': '',
        'timestamp': '',
        'replies': []  # 支持多层嵌套回复
    }
    
    try:
        # 提取回复文本
        reply_body = item.locator('.comment-body').first
        if await reply_body.count() > 0:
            reply_text = await reply_body.text_content()
            reply_data['text'] = clean_comment_text(reply_text)
        
        # 提取作者
        author_selectors = [
            '.comment-author',
            '.user-name',
            '.author-name'
        ]
        
        for selector in author_selectors:
            try:
                author_element = item.locator(selector).first
                if await author_element.count() > 0:
                    reply_data['author'] = await author_element.text_content()
                    break
            except:
                continue
        
        # 提取时间戳
        time_selectors = [
            '.timestamp',
            '.comment-time', 
            '.time-ago',
            'time'
        ]
        
        for selector in time_selectors:
            try:
                time_element = item.locator(selector).first
                if await time_element.count() > 0:
                    reply_data['timestamp'] = await time_element.text_content()
                    break
            except:
                continue
        
        return reply_data
        
    except Exception as e:
        print(f"    提取回复数据时出错: {e}")
        return reply_data


def clean_comment_text(text: str) -> str:
    """
    清理评论文本，移除多余的空白和格式字符
    """
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text.strip())
    # 移除可能的系统文本
    text = re.sub(r'(Reply|回复|删除|Delete|编辑|Edit)', '', text)
    return text.strip()


async def extract_single_comment(item) -> Dict[str, Any]:
    """
    提取单个评论的数据 (旧版本，保持兼容性)
    """
    comment_data = {
        'text': '',
        'author': '',
        'timestamp': '',
        'replies': []
    }
    
    try:
        # 提取评论文本
        # 尝试多种可能的文本选择器
        text_selectors = [
            '.comment-text',
            '.comment-content', 
            '.content',
            'p',
            '.text'
        ]
        
        comment_text = ""
        for selector in text_selectors:
            try:
                text_elements = await item.locator(selector).all()
                if text_elements:
                    for element in text_elements:
                        text = await element.inner_text()
                        if text and text.strip():
                            comment_text += text.strip() + " "
                    if comment_text.strip():
                        break
            except:
                continue
        
        # 如果没有找到特定选择器，获取整个item的文本
        if not comment_text.strip():
            try:
                comment_text = await item.inner_text()
            except:
                comment_text = ""
        
        # 清理文本
        comment_text = clean_text(comment_text)
        comment_data['text'] = comment_text
        
        # 提取作者信息 (通常在链接或特定class中)
        author_selectors = [
            '.author',
            '.username', 
            '.user',
            'a[href*="user"]',
            '.comment-author',
            'strong',
            'b'
        ]
        
        for selector in author_selectors:
            try:
                author_element = item.locator(selector).first
                if await author_element.is_visible():
                    author = await author_element.inner_text()
                    if author and author.strip():
                        comment_data['author'] = author.strip()
                        break
            except:
                continue
        
        # 提取时间戳
        time_selectors = [
            '.timestamp',
            '.time',
            '.date',
            'time',
            '.comment-time',
            '[datetime]'
        ]
        
        for selector in time_selectors:
            try:
                time_element = item.locator(selector).first
                if await time_element.is_visible():
                    timestamp = await time_element.inner_text()
                    if timestamp and timestamp.strip():
                        comment_data['timestamp'] = timestamp.strip()
                        break
            except:
                continue
        
        # 提取回复 (查找嵌套的li或特定class)
        try:
            # 查找嵌套的评论列表
            nested_comments = await item.locator('ul li, ol li, .replies li, .nested-comments li').all()
            
            for nested_item in nested_comments:
                try:
                    nested_comment = await extract_single_comment(nested_item)
                    if nested_comment and nested_comment.get('text', '').strip():
                        comment_data['replies'].append(nested_comment)
                except:
                    continue
                    
        except:
            pass  # 如果没有回复就跳过
        
        return comment_data
        
    except Exception as e:
        print(f"    提取单个评论数据时出错: {e}")
        return comment_data


def clean_text(text: str) -> str:
    """
    清理和格式化文本
    """
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除首尾空白
    text = text.strip()
    
    # 移除一些常见的无用文本
    unwanted_phrases = [
        'Reply',
        'Like',
        'Share', 
        'More',
        'Show more',
        'Show less',
        '回复',
        '点赞',
        '分享',
        '更多'
    ]
    
    for phrase in unwanted_phrases:
        if text.strip() == phrase:
            return ""
    
    return text
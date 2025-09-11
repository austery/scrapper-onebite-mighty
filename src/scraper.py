"""
评论抓取核心模块
"""
import asyncio
import re
from typing import List, Dict, Any


# 关键选择器（绝对不能使用nth-child）- 根据实际网站结构更新
SELECTORS = {
    # 锚点：评论区容器
    'COMMENT_CONTAINER': '#sidebar-comments-region',
    
    # 加载更多评论按钮 - 往前展开的按钮
    'LOAD_MORE_BUTTON': 'text="Previous Comments"',
    
    # 展开折叠内容链接 - 往后展开跟帖
    'EXPAND_LINKS': 'a.more.text-color-grey-3-link',
    
    # 评论项（在容器内查找）
    'COMMENT_ITEMS': 'li',  # 必须在COMMENT_CONTAINER内使用
    
    # 其他可能的加载按钮（如果有多种展开方式）
    'LOAD_NEXT_BUTTON': 'text="Next Comments"',  # 可能的往后展开按钮
    'EXPAND_REPLIES': 'text="Show replies"',     # 可能的展开回复按钮
    'LOAD_OLDER': 'text="Load older"',           # 可能的加载更早评论按钮
    'LOAD_NEWER': 'text="Load newer"',           # 可能的加载更新评论按钮
}


async def load_all_comments(page, config):
    """
    双循环加载策略
    Phase 1: 循环点击"Previous Comments"直到全部加载
    Phase 2: 循环点击所有"more"链接直到全部展开
    """
    print("开始加载所有评论...")
    
    # Loop 1: 加载所有评论页 (往前和往后展开)
    print("Phase 1: 加载所有评论页...")
    
    # 定义不同类型的加载按钮
    load_buttons = [
        ('Previous Comments', '往前加载'),
        ('Next Comments', '往后加载'), 
        ('Load older', '加载更早评论'),
        ('Load newer', '加载更新评论'),
        ('Show more comments', '显示更多评论')
    ]
    
    total_loads = 0
    
    # 尝试所有类型的加载按钮，直到没有更多可加载的
    for button_text, description in load_buttons:
        print(f"  尝试 {description} 按钮...")
        button_count = 0
        
        while True:
            try:
                # 查找当前类型的按钮
                button = page.get_by_text(button_text)
                if await button.is_visible():
                    await button.click()
                    button_count += 1
                    total_loads += 1
                    print(f"    {description}: 已点击 {button_count} 次")
                    await page.wait_for_load_state('networkidle')
                    await page.wait_for_timeout(config.WAIT_TIME)
                else:
                    if button_count > 0:
                        print(f"    {description}: 已完成，共点击 {button_count} 次")
                    break
            except Exception as e:
                if button_count > 0:
                    print(f"    {description}: 出错停止，共点击 {button_count} 次，错误: {e}")
                break
    
    print(f"  Phase 1 完成: 共执行了 {total_loads} 次加载操作")
    
    # Loop 2: 展开所有折叠内容
    print("Phase 2: 展开所有折叠内容...")
    expand_count = 0
    max_iterations = 50  # 防止无限循环
    iteration = 0
    
    while iteration < max_iterations:
        try:
            # 查找所有"more"链接
            links = await page.locator('a.more.text-color-grey-3-link').all()
            if not links:
                print(f"  没有找到更多折叠内容，共展开了 {expand_count} 项")
                break
                
            print(f"  找到 {len(links)} 个折叠内容")
            
            # 点击所有找到的链接
            for i, link in enumerate(links):
                try:
                    if await link.is_visible():
                        await link.click()
                        expand_count += 1
                        await page.wait_for_timeout(config.WAIT_TIME // 2)  # 更短的等待时间
                except Exception as e:
                    print(f"    点击第 {i+1} 个展开链接时失败: {e}")
                    continue
            
            # 等待内容加载
            await page.wait_for_timeout(config.WAIT_TIME)
            iteration += 1
            
        except Exception as e:
            print(f"  展开折叠内容时发生错误: {e}")
            break
    
    print(f"评论加载完成！共展开了 {expand_count} 项折叠内容")


async def extract_comments(page) -> List[Dict[str, Any]]:
    """
    提取评论数据，保持层级结构
    Returns: List[Dict] - 评论数据结构
    """
    print("开始提取评论数据...")
    
    try:
        # 定位评论容器
        container = page.locator('#sidebar-comments-region')
        
        if not await container.is_visible():
            print("❌ 未找到评论区容器")
            return []
        
        # 获取所有评论项 (li元素)
        comment_items = await container.locator('li').all()
        print(f"找到 {len(comment_items)} 个评论项")
        
        comments = []
        
        for i, item in enumerate(comment_items):
            try:
                print(f"  处理第 {i+1} 个评论...")
                comment_data = await extract_single_comment(item)
                if comment_data and comment_data.get('text', '').strip():
                    comments.append(comment_data)
                    
            except Exception as e:
                print(f"    处理第 {i+1} 个评论时出错: {e}")
                continue
        
        print(f"✅ 成功提取 {len(comments)} 条有效评论")
        return comments
        
    except Exception as e:
        print(f"❌ 提取评论数据时发生错误: {e}")
        return []


async def extract_single_comment(item) -> Dict[str, Any]:
    """
    提取单个评论的数据
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
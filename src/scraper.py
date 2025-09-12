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
    
    # More 展开链接 - 只针对评论内容的展开，避免点击图片和其他元素
    'EXPAND_MORE_LINKS': '#sidebar-comments-region .comment-body.mighty-wysiwyg-content.fr-view.wysiwyg-comment.long.is-truncated > a:has-text("more")',
    
    # 更通用的 More 链接选择器作为备选 - 限制在评论区域内
    'EXPAND_LINKS_FALLBACK': '#sidebar-comments-region a.more.text-color-grey-3-link:has-text("more")',
    
    # 评论项（在容器内查找）
    'COMMENT_ITEMS': 'li',  # 必须在COMMENT_CONTAINER内使用
    
    # 评论区域选择器
    'COMMENTS_REGION': '.comments-region',
    'COMMENT_BODY_CONTAINER': '.comment-body-container',
    'COMMENT_BODY_TRUNCATED': '.comment-body.is-truncated'
}


async def get_expected_comment_count(page):
    """
    从评论头部获取期望的评论总数
    """
    try:
        # 使用用户提供的选择器
        header_selectors = [
            '#flyout-right-drawer-region > div.comments-sidebar-layout > div.comment-sidebar-header > div.comment-count',
            '#flyout-right-drawer-region > div.comments-sidebar-layout > div.comment-sidebar-header > h2',
            '.comment-count',
            '.comments-count'
        ]
        
        for selector in header_selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    text = await element.text_content()
                    # 尝试提取数字
                    import re
                    numbers = re.findall(r'\d+', text or '')
                    if numbers:
                        count = int(numbers[0])
                        print(f"📊 从评论头部获取到期望评论数: {count}")
                        return count
            except:
                continue
        
        print("⚠️ 无法从评论头部获取评论数量")
        return None
        
    except Exception as e:
        print(f"获取期望评论数时出错: {e}")
        return None


async def debug_page_structure(page):
    """
    调试：分析页面结构，帮助确认选择器
    """
    try:
        print("🔍 调试: 分析页面结构...")
        
        # 获取期望的评论数量
        expected_count = await get_expected_comment_count(page)
        
        # 检查评论区容器
        comment_region = page.locator('#sidebar-comments-region')
        if await comment_region.count() > 0:
            print("✅ 找到评论区容器")
            
            # 检查 Previous Comments 按钮
            previous_buttons = await page.locator(SELECTORS['PREVIOUS_COMMENTS_BUTTON']).count()
            print(f"📄 Previous Comments 按钮数量: {previous_buttons}")
            
            # 检查 More 链接
            more_links_1 = await page.locator('a:has-text("more")').count()
            more_links_2 = await page.locator('a.more').count()
            print(f"📄 More 链接数量 (文本匹配): {more_links_1}")
            print(f"📄 More 链接数量 (类选择器): {more_links_2}")
            
            # 检查评论项
            comment_items = await comment_region.locator('li').count()
            print(f"📄 评论项数量: {comment_items}")
            
            # 比较期望数量和实际数量
            if expected_count:
                print(f"📊 期望评论数: {expected_count}, 当前评论项数: {comment_items}")
                if comment_items < expected_count:
                    print(f"⚠️ 可能还有 {expected_count - comment_items} 个评论未加载")
            
        else:
            print("❌ 未找到评论区容器")
            
    except Exception as e:
        print(f"调试过程出错: {e}")


async def load_all_previous_comments(page, config):
    """
    递归加载所有层级的 Previous Comments
    包括根级别和嵌套在回复中的 Previous Comments
    """
    total_loaded = 0
    max_iterations = 10  # 防止无限循环
    
    for iteration in range(max_iterations):
        # 查找所有可见的 Previous Comments 按钮（包括嵌套的）
        all_previous_buttons = await page.locator('a:has-text("Previous Comments")').all()
        
        if not all_previous_buttons:
            # 如果没找到，尝试其他可能的选择器
            all_previous_buttons = await page.locator(SELECTORS['PREVIOUS_COMMENTS_BUTTON']).all()
        
        if not all_previous_buttons:
            print(f"  第 {iteration + 1} 轮：没有找到更多 Previous Comments 按钮")
            break
        
        # 过滤出可见的按钮
        visible_buttons = []
        for button in all_previous_buttons:
            try:
                if await button.is_visible():
                    visible_buttons.append(button)
            except:
                continue
        
        if not visible_buttons:
            print(f"  第 {iteration + 1} 轮：没有可见的 Previous Comments 按钮")
            break
        
        print(f"  第 {iteration + 1} 轮：找到 {len(visible_buttons)} 个 Previous Comments 按钮")
        
        # 点击所有可见的按钮
        buttons_clicked = 0
        for i, button in enumerate(visible_buttons):
            try:
                print(f"    点击第 {i+1} 个 Previous Comments 按钮...")
                await button.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
                await button.click()
                buttons_clicked += 1
                total_loaded += 1
                
                # 每次点击后等待内容加载
                await page.wait_for_timeout(1500)
                
            except Exception as e:
                print(f"    点击第 {i+1} 个按钮失败: {e}")
                continue
        
        if buttons_clicked == 0:
            print(f"  第 {iteration + 1} 轮：没有成功点击任何按钮，结束加载")
            break
        
        print(f"  第 {iteration + 1} 轮：成功点击了 {buttons_clicked} 个按钮")
        
        # 等待页面稳定
        await page.wait_for_load_state('networkidle', timeout=10000)
        await page.wait_for_timeout(config.WAIT_TIME)
    
    return total_loaded


async def expand_remaining_more_links(page, config, max_iterations=3):
    """
    展开剩余的More链接（用于Previous Comments加载后的额外处理）
    """
    expand_count = 0
    
    for iteration in range(max_iterations):
        try:
            # 查找More链接
            more_links = []
            
            primary_links = await page.locator(SELECTORS['EXPAND_MORE_LINKS']).all()
            more_links.extend(primary_links)
            
            if not more_links:
                fallback_links = await page.locator(SELECTORS['EXPAND_LINKS_FALLBACK']).all()
                more_links.extend(fallback_links)
            
            if not more_links:
                break
                
            print(f"    找到 {len(more_links)} 个More链接")
            
            links_clicked = 0
            for i, link in enumerate(more_links):
                try:
                    if await link.is_visible():
                        await link.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        await link.click(force=True)
                        links_clicked += 1
                        expand_count += 1
                        await page.wait_for_timeout(1000)
                except Exception as e:
                    continue
            
            if links_clicked == 0:
                break
                
            await page.wait_for_timeout(config.WAIT_TIME)
            
        except Exception as e:
            print(f"    展开剩余More链接时出错: {e}")
            break
    
    return expand_count


async def scroll_and_discover_comments(page, config):
    """
    通过页面滚动和视角调整来发现隐藏的评论
    """
    print("  🔍 执行页面滚动和视角调整以发现隐藏评论...")
    
    try:
        # 首先滚动到评论区域
        await page.locator('#sidebar-comments-region').scroll_into_view_if_needed()
        await page.wait_for_timeout(1000)
        
        # 1. 向下缓慢滚动，触发懒加载
        print("    📜 执行缓慢滚动以触发懒加载...")
        for i in range(3):
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(1500)
            
        # 2. 滚动到评论区域底部
        print("    ⬇️ 滚动到评论区域底部...")
        await page.evaluate("""
            const commentRegion = document.querySelector('#sidebar-comments-region');
            if (commentRegion) {
                commentRegion.scrollTop = commentRegion.scrollHeight;
            }
        """)
        await page.wait_for_timeout(2000)
        
        # 3. 回到评论区域顶部
        print("    ⬆️ 回到评论区域顶部...")
        await page.evaluate("""
            const commentRegion = document.querySelector('#sidebar-comments-region');
            if (commentRegion) {
                commentRegion.scrollTop = 0;
            }
        """)
        await page.wait_for_timeout(1000)
        
        # 4. 尝试调整页面缩放比例
        print("    🔍 调整页面缩放比例...")
        # 先缩小到90%查看更多内容
        await page.evaluate("document.body.style.zoom = '0.9'")
        await page.wait_for_timeout(1000)
        
        # 然后恢复正常大小
        await page.evaluate("document.body.style.zoom = '1.0'")
        await page.wait_for_timeout(1000)
        
        print("    ✅ 页面滚动和视角调整完成")
        
    except Exception as e:
        print(f"    ⚠️ 页面滚动和视角调整时出错: {e}")


async def load_all_comments(page, config):
    """
    增强的双循环加载策略
    Phase 0: 页面滚动和视角调整
    Phase 1: 循环点击"Previous Comments"直到全部加载
    Phase 2: 循环点击所有"more"链接直到全部展开
    """
    print("开始加载所有评论...")
    
    # Phase 0: 页面滚动和视角调整 (新增)
    print("Phase 0: 页面滚动和视角调整...")
    await scroll_and_discover_comments(page, config)
    
    # 重新进行调试分析（滚动后可能发现新内容）
    await debug_page_structure(page)
    
    # Phase 1: 加载所有层级的 Previous Comments
    print("Phase 1: 加载所有层级的 Previous Comments...")
    
    total_previous_loaded = await load_all_previous_comments(page, config)
    print(f"  Phase 1 完成: 总共加载了 {total_previous_loaded} 个 Previous Comments")
    
    # Phase 2: 展开所有折叠的评论内容（More 链接）
    print("Phase 2: 展开所有折叠的评论内容...")
    expand_count = 0
    max_iterations = 8  # 限制最大迭代次数防止无限循环
    iteration = 0
    
    # 无限循环检测变量
    previous_link_count = 0
    no_change_count = 0  # 连续无变化次数
    
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
                
            current_link_count = len(more_links)
            print(f"  找到 {current_link_count} 个折叠内容")
            
            # 无限循环检测：如果链接数量没有变化，可能陷入循环
            if current_link_count == previous_link_count:
                no_change_count += 1
                print(f"  ⚠️ 检测到链接数量未变化（连续 {no_change_count} 次）")
                if no_change_count >= 3:  # 连续3次无变化就停止
                    print(f"  🛑 检测到可能的无限循环，停止More链接展开")
                    break
            else:
                no_change_count = 0  # 重置计数器
                
            previous_link_count = current_link_count
            
            # 逐个点击展开链接
            links_clicked = 0
            for i, link in enumerate(more_links):
                try:
                    # 检查链接是否可见且文本确实是"more"
                    if await link.is_visible():
                        link_text = await link.text_content()
                        if not link_text or "more" not in link_text.lower():
                            print(f"    ⚠️ 第 {i+1} 个链接文本不匹配 ('{link_text}')，跳过")
                            continue
                            
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
            
            iteration += 1
            
            # 早期退出检查：如果迭代次数超过限制
            if iteration >= max_iterations:
                print(f"  🛑 达到最大迭代次数 {max_iterations}，停止展开防止无限循环")
                break
            
        except Exception as e:
            print(f"  展开折叠内容时发生错误: {e}")
            break
    
    print(f"评论加载完成！共展开了 {expand_count} 项折叠内容")
    
    # Phase 3: 展开More链接后，重新检查是否有新的Previous Comments出现
    print("Phase 3: 检查展开后是否有新的 Previous Comments...")
    additional_previous = await load_all_previous_comments(page, config)
    if additional_previous > 0:
        print(f"  发现并加载了额外的 {additional_previous} 个 Previous Comments")
        
        # 如果加载了新的Previous Comments，可能需要重新展开More链接
        print("  重新检查是否有新的More链接需要展开...")
        additional_expand = await expand_remaining_more_links(page, config, max_iterations=3)
        print(f"  额外展开了 {additional_expand} 项内容")
    else:
        print("  没有发现新的 Previous Comments")
    
    # Phase 4: 最终发现阶段 - 再次滚动和搜索
    print("Phase 4: 最终发现阶段 - 再次滚动和搜索...")
    await scroll_and_discover_comments(page, config)
    
    # 最终检查是否还有未发现的Previous Comments
    final_previous = await load_all_previous_comments(page, config)
    if final_previous > 0:
        print(f"  最终发现了额外的 {final_previous} 个 Previous Comments")
        # 再次展开可能的More链接
        final_expand = await expand_remaining_more_links(page, config, max_iterations=2)
        print(f"  最终额外展开了 {final_expand} 项内容")
    else:
        print("  最终检查：没有发现更多Previous Comments")


async def final_comment_verification(page, extracted_count):
    """
    最终验证评论提取的完整性
    """
    try:
        expected_count = await get_expected_comment_count(page)
        if expected_count:
            if extracted_count < expected_count:
                shortage = expected_count - extracted_count
                print(f"⚠️ 评论提取可能不完整:")
                print(f"   期望: {expected_count} 条")
                print(f"   实际: {extracted_count} 条")  
                print(f"   缺少: {shortage} 条")
                print(f"💡 建议: 可能需要手动检查页面是否有未展开的评论区域")
            elif extracted_count >= expected_count:
                print(f"✅ 评论提取完整: {extracted_count}/{expected_count}")
            else:
                print(f"📊 评论提取统计: {extracted_count} 条 (期望: {expected_count})")
    except Exception as e:
        print(f"验证过程出错: {e}")


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
        # 尝试提取帖子标题 - 使用更精确的选择器避免混淆
        title_selectors = [
            '#detail-layout > div.detail-layout-content-wrapper > div.detail-layout-title',
            '.detail-layout-title',
            '#detail-layout h1',
            '.post-title',
            '.article-title', 
            'h1',
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
                    content_html = await content_element.inner_html()
                    if content_html and len(content_html.strip()) > 20:  # 确保不是空内容
                        post_data['content'] = content_html.strip()
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
        
        # 计算总评论数（包括所有嵌套回复）
        total_extracted_comments = count_all_comments_recursively(root_comments)
        print(f"📊 总评论数统计: 根评论 {len(root_comments)} 条, 总计 {total_extracted_comments} 条 (包括所有回复)")
        
        # 最终验证：检查是否达到期望数量
        await final_comment_verification(page, total_extracted_comments)
        
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
            # 获取评论HTML，保留格式信息
            comment_html = await comment_body.inner_html()
            comment_data['text'] = clean_comment_html(comment_html)
        
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
            reply_html = await reply_body.inner_html()
            reply_data['text'] = clean_comment_html(reply_html)
        
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


def count_all_comments_recursively(comments_list):
    """
    递归计算所有评论的总数（包括嵌套回复）
    """
    total = 0
    for comment in comments_list:
        total += 1  # 计算当前评论
        if comment.get('replies'):
            total += count_all_comments_recursively(comment['replies'])  # 递归计算回复
    return total


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


def clean_comment_html(html: str) -> str:
    """
    清理评论HTML，保留格式标签但移除无用的系统元素
    """
    if not html:
        return ""
    
    # 移除可能的系统按钮和链接
    html = re.sub(r'<a[^>]*href[^>]*>[\s\S]*?(Reply|回复|删除|Delete|编辑|Edit|more|更多)[\s\S]*?</a>', '', html, flags=re.IGNORECASE)
    
    # 移除空的段落和div标签
    html = re.sub(r'<(p|div)[^>]*>\s*</\1>', '', html, flags=re.IGNORECASE)
    
    # 清理多余的空白但保留HTML结构
    html = re.sub(r'\s+', ' ', html.strip())
    
    return html.strip()


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
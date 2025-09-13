#!/usr/bin/env python3
"""
将现有的Phase 3真实抓取数据转换为Phase 4 Obsidian优化格式
"""

import json
import sys
import shutil
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from obsidian_helpers import (
    parse_relative_time_to_date,
    generate_obsidian_filename,
    generate_yaml_frontmatter,
    OBSIDIAN_ARTICLES_DIR,
    OBSIDIAN_ATTACHMENTS_DIR
)
from image_processor import create_markdown_from_html

def clean_html_to_markdown(html_content):
    """
    将HTML内容转换为干净的Markdown格式
    """
    if not html_content or not html_content.strip():
        return ""
    
    try:
        from bs4 import BeautifulSoup
        from markdownify import markdownify as md
        
        # 首先用BeautifulSoup清理无意义的链接
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 移除OneNewBite内部链接，保留纯文本
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if 'onenewbite.com' in href:
                # 如果是会员链接或内部链接，只保留文本内容
                if '/members/' in href or '/spaces/' in href or 'mighty-mention' in link.get('class', []):
                    link.replace_with(link.get_text())
                # 如果是帖子链接，也只保留文本
                elif '/posts/' in href:
                    link.replace_with(link.get_text())
        
        # 转换清理后的HTML为Markdown
        markdown_content = md(
            str(soup), 
            heading_style="ATX",  # 使用 # ## ### 格式
            bullets="-",          # 使用 - 作为列表符号
            strip=['div', 'span']  # 只移除这些标签但保留内容
        )
        
        # 清理多余的空行
        lines = markdown_content.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            line = line.strip()
            if line == "":
                if not prev_empty:
                    cleaned_lines.append("")
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        
        return '\n'.join(cleaned_lines).strip()
        
    except ImportError:
        # 如果markdownify不可用，进行简单的HTML清理
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 处理常见HTML标签
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        for p in soup.find_all('p'):
            p.replace_with(p.get_text() + '\n\n')
            
        for strong in soup.find_all(['strong', 'b']):
            strong.replace_with(f"**{strong.get_text()}**")
            
        for em in soup.find_all(['em', 'i']):
            em.replace_with(f"*{em.get_text()}*")
        
        # 获取纯文本并清理
        text = soup.get_text()
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # 移除空行
        
        return '\n\n'.join(lines).strip()
    except Exception as e:
        print(f"    ⚠️ HTML转换失败: {e}")
        # 降级到BeautifulSoup纯文本提取
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text().strip()

def convert_images_to_obsidian_paths(html_content, source_images_dir, filename_prefix):
    """
    将HTML中的图片路径转换为Obsidian统一附件格式
    同时复制图片到统一附件目录
    """
    if not html_content:
        return html_content
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    img_tags = soup.find_all('img')
    
    for img_tag in img_tags:
        src = img_tag.get('src')
        if src and src.startswith('images/'):
            # 提取原始文件名
            original_filename = src.replace('images/', '')
            source_path = source_images_dir / original_filename
            
            if source_path.exists():
                # 生成新的文件名以避免冲突
                new_filename = f"{filename_prefix}_{original_filename}"
                target_path = OBSIDIAN_ATTACHMENTS_DIR / new_filename
                
                # 确保目标目录存在
                OBSIDIAN_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
                
                # 复制图片到统一附件目录
                if not target_path.exists():
                    shutil.copy2(source_path, target_path)
                    print(f"    📷 复制图片: {source_path.name} -> {target_path.name}")
                
                # 更新HTML中的路径
                img_tag['src'] = f"../attachments/{new_filename}"
    
    return str(soup)

def convert_single_post(data_json_path):
    """转换单个帖子的数据"""
    try:
        print(f"\n🔄 处理: {data_json_path}")
        
        # 读取JSON数据
        with open(data_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        post_data = data.get('post', {})
        comments = data.get('comments', [])
        url = data.get('url', '')
        
        # 清理标题
        title = post_data.get('title', '').strip()
        if title.startswith('\n') and title.endswith('\n'):
            title = title[1:-1].strip()
        
        # 计算发布日期
        timestamp = post_data.get('timestamp', '').strip()
        if timestamp.startswith('\n') and timestamp.endswith('\n'):
            timestamp = timestamp[1:-1].strip()
        
        published_date = parse_relative_time_to_date(timestamp)
        
        # 生成文件名
        obsidian_filename = generate_obsidian_filename(title, published_date)
        
        print(f"    📝 标题: {title}")
        print(f"    📅 发布日期: {published_date}")
        print(f"    📄 文件名: {obsidian_filename}.md")
        
        # 处理图片路径
        source_folder = data_json_path.parent
        images_folder = source_folder / 'images'
        filename_prefix = source_folder.name[:20]  # 使用文件夹名作为前缀
        
        # 转换主帖内容中的图片
        processed_content = post_data.copy()
        if 'content' in processed_content:
            processed_content['content'] = convert_images_to_obsidian_paths(
                processed_content['content'], images_folder, filename_prefix
            )
        
        # 转换评论中的图片
        processed_comments = []
        for comment in comments:
            processed_comment = comment.copy()
            if 'content' in comment:
                processed_comment['content'] = convert_images_to_obsidian_paths(
                    comment['content'], images_folder, filename_prefix
                )
            elif 'text' in comment:
                # 有些评论用text字段而不是content
                processed_comment['text'] = convert_images_to_obsidian_paths(
                    comment['text'], images_folder, filename_prefix
                )
            processed_comments.append(processed_comment)
        
        # 生成YAML frontmatter
        yaml_frontmatter = generate_yaml_frontmatter(processed_content, url)
        
        # 生成Markdown内容
        markdown_content = [yaml_frontmatter]
        
        # 添加主帖内容
        if processed_content and 'content' in processed_content:
            markdown_content.append("# 主帖内容\n\n")
            post_markdown = clean_html_to_markdown(processed_content['content'])
            markdown_content.append(post_markdown)
            markdown_content.append("\n\n---\n\n")
        
        # 添加评论
        if processed_comments:
            markdown_content.append("## 评论\n\n")
            for i, comment in enumerate(processed_comments, 1):
                if 'author' in comment:
                    markdown_content.append(f"### {i}. {comment['author']}\n\n")
                
                # 处理评论内容 - 优先使用text，其次content（因为实际数据显示评论在text字段）
                comment_text = comment.get('text') or comment.get('content', '')
                if comment_text:
                    # 转换HTML为干净的Markdown
                    comment_markdown = clean_html_to_markdown(comment_text)
                    if comment_markdown:
                        markdown_content.append(comment_markdown)
                        markdown_content.append("\n\n")
                
                # 添加时间戳
                if 'timestamp' in comment:
                    timestamp_clean = comment['timestamp'].strip()
                    if timestamp_clean.startswith('\n') and timestamp_clean.endswith('\n'):
                        timestamp_clean = timestamp_clean[1:-1].strip()
                    markdown_content.append(f"*发布时间: {timestamp_clean}*\n\n")
                
                # 处理回复
                if 'replies' in comment and comment['replies']:
                    for j, reply in enumerate(comment['replies'], 1):
                        if 'author' in reply:
                            markdown_content.append(f"#### 回复 {i}.{j} - {reply['author']}\n\n")
                        
                        reply_text = reply.get('text') or reply.get('content', '')
                        if reply_text:
                            reply_markdown = clean_html_to_markdown(reply_text)
                            if reply_markdown:
                                markdown_content.append(reply_markdown)
                                markdown_content.append("\n\n")
                        
                        if 'timestamp' in reply:
                            reply_timestamp = reply['timestamp'].strip()
                            if reply_timestamp.startswith('\n') and reply_timestamp.endswith('\n'):
                                reply_timestamp = reply_timestamp[1:-1].strip()
                            markdown_content.append(f"*发布时间: {reply_timestamp}*\n\n")
                
                markdown_content.append("---\n\n")
        
        # 确保输出目录存在
        OBSIDIAN_ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存Markdown文件
        markdown_file = OBSIDIAN_ARTICLES_DIR / f"{obsidian_filename}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(''.join(markdown_content))
        
        print(f"    ✅ 已转换: {markdown_file}")
        
        return True
        
    except Exception as e:
        print(f"    ❌ 转换失败: {e}")
        return False

def main():
    """主函数：转换所有现有的JSON数据"""
    print("🚀 开始将Phase 3真实数据转换为Phase 4 Obsidian格式...\n")
    
    # 查找所有data.json文件
    output_dir = Path('output')
    json_files = list(output_dir.glob('*/data.json'))
    
    if not json_files:
        print("❌ 没有找到任何data.json文件")
        return
    
    print(f"📋 找到 {len(json_files)} 个JSON文件待转换")
    
    # 清理旧的示例文件
    if OBSIDIAN_ARTICLES_DIR.exists():
        for file in OBSIDIAN_ARTICLES_DIR.glob('*.md'):
            if file.stat().st_size < 1000:  # 小文件可能是示例
                file.unlink()
                print(f"🗑️  删除旧示例文件: {file.name}")
    
    if OBSIDIAN_ATTACHMENTS_DIR.exists():
        for file in OBSIDIAN_ATTACHMENTS_DIR.glob('*'):
            if file.stat().st_size < 100:  # 小文件可能是示例
                file.unlink()
                print(f"🗑️  删除旧示例文件: {file.name}")
    
    # 转换所有文件
    successful_count = 0
    failed_count = 0
    
    for json_file in json_files:
        if convert_single_post(json_file):
            successful_count += 1
        else:
            failed_count += 1
    
    # 显示最终统计
    print(f"\n🎉 转换完成！")
    print(f"📊 统计信息:")
    print(f"   ✅ 成功转换: {successful_count} 个")
    print(f"   ❌ 转换失败: {failed_count} 个")
    print(f"   📁 Obsidian文章目录: {OBSIDIAN_ARTICLES_DIR}")
    print(f"   🖼️  Obsidian附件目录: {OBSIDIAN_ATTACHMENTS_DIR}")
    
    print(f"\n🎯 现在你可以将 'output/articles' 和 'output/attachments' 复制到Obsidian库中使用！")

if __name__ == "__main__":
    main()
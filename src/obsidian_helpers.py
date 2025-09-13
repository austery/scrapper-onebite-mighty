"""
Obsidian integration helper functions
Separated from main.py to enable testing without playwright dependencies
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

# Obsidian integration configuration
OBSIDIAN_ARTICLES_DIR = Path('output/articles')
OBSIDIAN_ATTACHMENTS_DIR = Path('output/attachments')


def parse_relative_time_to_date(relative_time: str) -> str:
    """
    将相对时间转换为绝对日期
    例如: "2w" -> "2024-03-15", "1y" -> "2023-01-20"
    
    Args:
        relative_time: 相对时间字符串，如 "2w", "1y", "3d"
    
    Returns:
        str: YYYY-MM-DD 格式的日期
    """
    if not relative_time:
        return datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 提取数字和单位
        match = re.match(r'(\d+)([wdmy])', relative_time.lower().strip())
        if not match:
            return datetime.now().strftime('%Y-%m-%d')
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        now = datetime.now()
        
        if unit == 'd':  # days
            target_date = now - timedelta(days=amount)
        elif unit == 'w':  # weeks
            target_date = now - timedelta(weeks=amount)
        elif unit == 'm':  # months (approximate)
            target_date = now - timedelta(days=amount * 30)
        elif unit == 'y':  # years (approximate)
            target_date = now - timedelta(days=amount * 365)
        else:
            target_date = now
        
        return target_date.strftime('%Y-%m-%d')
        
    except Exception as e:
        print(f"⚠️ 解析相对时间失败 '{relative_time}': {e}")
        return datetime.now().strftime('%Y-%m-%d')


def sanitize_title_for_filename(title: str) -> str:
    """
    清理标题，使其适合作为文件名
    
    Args:
        title: 原始标题
    
    Returns:
        str: 清理后的标题
    """
    if not title:
        return "Untitled"
    
    # 移除或替换不安全的字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        title = title.replace(char, '')
    
    # 移除控制字符和多余的空白
    title = ''.join(char for char in title if ord(char) >= 32)
    title = ' '.join(title.split())  # 标准化空白字符
    
    # 限制长度
    if len(title) > 100:
        title = title[:100].rstrip()
    
    return title or "Untitled"


def generate_obsidian_filename(title: str, published_date: str) -> str:
    """
    生成符合Obsidian规范的文件名
    
    Args:
        title: 文章标题
        published_date: 发布日期 (YYYY-MM-DD)
    
    Returns:
        str: 格式化的文件名 (不包含扩展名)
    """
    clean_title = sanitize_title_for_filename(title)
    return f"{published_date} - {clean_title}"


def generate_yaml_frontmatter(post_data: dict, url: str) -> str:
    """
    生成Obsidian兼容的YAML frontmatter
    
    Args:
        post_data: 帖子数据
        url: 帖子URL
    
    Returns:
        str: YAML frontmatter字符串
    """
    title = post_data.get('title', '').strip() or 'Untitled'
    author = post_data.get('author', '').strip()
    relative_time = post_data.get('timestamp', '').strip()
    published_date = parse_relative_time_to_date(relative_time)
    
    yaml_content = f"""---
title: {title}
source: {url}
author: {author}
published: {published_date}
summary:
tags:
  - t-clipping
  - mighty_import
updated:
status: inbox
insight:
aliases:
---

"""
    
    return yaml_content
"""
图片处理模块
实现图片发现、下载和HTML路径替换功能
支持Obsidian统一附件管理
"""
import os
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Any

# Import the unified configuration
from obsidian_helpers import OBSIDIAN_ATTACHMENTS_DIR


def process_images_in_content_obsidian(html_content: str, base_url: str) -> str:
    """
    处理HTML内容中的图片（Obsidian统一附件管理模式）
    
    Args:
        html_content: 原始HTML内容
        base_url: 文章的基础URL，用于处理相对路径
    
    Returns:
        str: 处理后的HTML内容，图片路径已替换为Obsidian兼容的相对路径
    """
    if not html_content or not html_content.strip():
        print("⚠️ HTML内容为空，跳过图片处理")
        return html_content
    
    print("🖼️ 开始处理HTML内容中的图片（Obsidian模式）...")
    
    # 确保统一附件文件夹存在
    OBSIDIAN_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有img标签
    img_tags = soup.find_all('img')
    
    if not img_tags:
        print("📄 未找到图片标签")
        return html_content
    
    print(f"🔍 发现 {len(img_tags)} 个图片标签")
    
    downloaded_count = 0
    
    for i, img_tag in enumerate(img_tags, 1):
        try:
            # 获取图片URL
            img_url = img_tag.get('src')
            if not img_url:
                print(f"  ⚠️ 第 {i} 个图片标签没有src属性，跳过")
                continue
            
            print(f"  📥 处理第 {i} 个图片: {img_url}")
            
            # 处理相对路径和绝对路径
            absolute_img_url = urljoin(base_url, img_url)
            print(f"    🌐 绝对URL: {absolute_img_url}")
            
            # 下载图片到统一附件目录
            local_filename = download_image_obsidian(absolute_img_url, i)
            
            if local_filename:
                # 替换HTML中的图片路径为Obsidian兼容的相对路径
                # 从 articles/ 目录指向 attachments/ 目录
                img_tag['src'] = f'../attachments/{local_filename}'
                downloaded_count += 1
                print(f"    ✅ 已下载并更新路径: ../attachments/{local_filename}")
            else:
                print(f"    ❌ 下载失败，保持原路径")
                
        except Exception as e:
            print(f"    ❌ 处理第 {i} 个图片时出错: {e}")
            continue
    
    print(f"🎉 图片处理完成！成功下载 {downloaded_count}/{len(img_tags)} 个图片")
    
    # 返回修改后的HTML
    return str(soup)


def process_images_in_content(html_content: str, base_url: str, images_folder: Path) -> str:
    """
    处理HTML内容中的图片：发现、下载、替换路径（向后兼容）
    
    Args:
        html_content: 原始HTML内容
        base_url: 文章的基础URL，用于处理相对路径
        images_folder: 图片保存文件夹路径
    
    Returns:
        str: 处理后的HTML内容，图片路径已替换为本地相对路径
    """
    if not html_content or not html_content.strip():
        print("⚠️ HTML内容为空，跳过图片处理")
        return html_content
    
    print("🖼️ 开始处理HTML内容中的图片...")
    
    # 确保图片文件夹存在
    images_folder.mkdir(parents=True, exist_ok=True)
    
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有img标签
    img_tags = soup.find_all('img')
    
    if not img_tags:
        print("📄 未找到图片标签")
        return html_content
    
    print(f"🔍 发现 {len(img_tags)} 个图片标签")
    
    downloaded_count = 0
    
    for i, img_tag in enumerate(img_tags, 1):
        try:
            # 获取图片URL
            img_url = img_tag.get('src')
            if not img_url:
                print(f"  ⚠️ 第 {i} 个图片标签没有src属性，跳过")
                continue
            
            print(f"  📥 处理第 {i} 个图片: {img_url}")
            
            # 处理相对路径和绝对路径
            absolute_img_url = urljoin(base_url, img_url)
            print(f"    🌐 绝对URL: {absolute_img_url}")
            
            # 下载图片
            local_filename = download_image(absolute_img_url, images_folder, i)
            
            if local_filename:
                # 替换HTML中的图片路径为本地相对路径
                img_tag['src'] = f'images/{local_filename}'
                downloaded_count += 1
                print(f"    ✅ 已下载并更新路径: images/{local_filename}")
            else:
                print(f"    ❌ 下载失败，保持原路径")
                
        except Exception as e:
            print(f"    ❌ 处理第 {i} 个图片时出错: {e}")
            continue
    
    print(f"🎉 图片处理完成！成功下载 {downloaded_count}/{len(img_tags)} 个图片")
    
    # 返回修改后的HTML
    return str(soup)


def download_image_obsidian(img_url: str, img_index: int) -> str:
    """
    下载单个图片到Obsidian统一附件目录
    
    Args:
        img_url: 图片URL
        img_index: 图片索引（用于生成唯一文件名）
    
    Returns:
        str: 本地文件名，如果下载失败返回None
    """
    try:
        # 发送HTTP请求下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(img_url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
        
        # 生成本地文件名
        parsed_url = urlparse(img_url)
        original_filename = os.path.basename(parsed_url.path)
        
        # 如果URL中没有文件名，生成一个
        if not original_filename or '.' not in original_filename:
            # 尝试从Content-Type获取文件扩展名
            content_type = response.headers.get('content-type', '')
            if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                ext = '.jpg'
            elif 'image/png' in content_type:
                ext = '.png'
            elif 'image/gif' in content_type:
                ext = '.gif'
            elif 'image/webp' in content_type:
                ext = '.webp'
            else:
                ext = '.jpg'  # 默认扩展名
            
            original_filename = f'image_{img_index}{ext}'
        
        # 确保文件名安全
        safe_filename = sanitize_filename(original_filename)
        
        # 避免文件名冲突
        local_path = OBSIDIAN_ATTACHMENTS_DIR / safe_filename
        counter = 1
        while local_path.exists():
            name, ext = os.path.splitext(safe_filename)
            safe_filename = f"{name}_{counter}{ext}"
            local_path = OBSIDIAN_ATTACHMENTS_DIR / safe_filename
            counter += 1
        
        # 保存图片
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"    💾 图片已保存到统一附件库: {local_path}")
        return safe_filename
        
    except requests.exceptions.RequestException as e:
        print(f"    ❌ 网络错误: {e}")
        return None
    except Exception as e:
        print(f"    ❌ 保存图片时出错: {e}")
        return None


def download_image(img_url: str, images_folder: Path, img_index: int) -> str:
    """
    下载单个图片（向后兼容）
    
    Args:
        img_url: 图片URL
        images_folder: 图片保存文件夹
        img_index: 图片索引（用于生成唯一文件名）
    
    Returns:
        str: 本地文件名，如果下载失败返回None
    """
    try:
        # 发送HTTP请求下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(img_url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
        
        # 生成本地文件名
        parsed_url = urlparse(img_url)
        original_filename = os.path.basename(parsed_url.path)
        
        # 如果URL中没有文件名，生成一个
        if not original_filename or '.' not in original_filename:
            # 尝试从Content-Type获取文件扩展名
            content_type = response.headers.get('content-type', '')
            if 'image/jpeg' in content_type or 'image/jpg' in content_type:
                ext = '.jpg'
            elif 'image/png' in content_type:
                ext = '.png'
            elif 'image/gif' in content_type:
                ext = '.gif'
            elif 'image/webp' in content_type:
                ext = '.webp'
            else:
                ext = '.jpg'  # 默认扩展名
            
            original_filename = f'image_{img_index}{ext}'
        
        # 确保文件名安全
        safe_filename = sanitize_filename(original_filename)
        
        # 避免文件名冲突
        local_path = images_folder / safe_filename
        counter = 1
        while local_path.exists():
            name, ext = os.path.splitext(safe_filename)
            safe_filename = f"{name}_{counter}{ext}"
            local_path = images_folder / safe_filename
            counter += 1
        
        # 保存图片
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"    💾 图片已保存: {local_path}")
        return safe_filename
        
    except requests.exceptions.RequestException as e:
        print(f"    ❌ 网络错误: {e}")
        return None
    except Exception as e:
        print(f"    ❌ 保存图片时出错: {e}")
        return None


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全的字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 清理后的安全文件名
    """
    # 移除或替换不安全的字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # 移除控制字符
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename


def create_markdown_from_html(html_content: str, title: str = "") -> str:
    """
    将HTML内容转换为Markdown格式
    
    Args:
        html_content: HTML内容
        title: 文章标题
    
    Returns:
        str: Markdown内容
    """
    try:
        import re
        from markdownify import markdownify as md
        
        # 预处理：移除mighty-hashtag链接，只保留hashtag文本
        # 将 <a class="navigate mighty-hashtag" href="...#hashtag">text</a> 转换为纯文本
        processed_html = re.sub(
            r'<a[^>]*class="[^"]*mighty-hashtag[^"]*"[^>]*href="[^"]*"[^>]*>(.*?)</a>',
            r'\1',
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # 转换HTML为Markdown
        markdown_content = md(processed_html, heading_style="ATX", bullets="-")
        
        # 如果有标题，添加到开头
        if title:
            markdown_content = f"# {title}\n\n{markdown_content}"
        
        return markdown_content
        
    except ImportError:
        print("⚠️ markdownify库未安装，无法转换为Markdown")
        return html_content
    except Exception as e:
        print(f"❌ 转换Markdown时出错: {e}")
        return html_content
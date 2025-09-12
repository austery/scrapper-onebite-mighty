"""
HTML to Markdown 转换器
将抓取到的HTML内容转换为Markdown格式，实现用户友好的文档输出
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from markdownify import markdownify as md
import argparse


def convert_html_to_markdown(html_content: str) -> str:
    """
    将HTML内容转换为Markdown格式
    
    Args:
        html_content: 需要转换的HTML内容
        
    Returns:
        转换后的Markdown文本
    """
    if not html_content:
        return ""
    
    # 使用markdownify进行转换
    # heading_style="ATX" 生成 #, ## 这种标题格式
    # wrap=True 自动换行
    # convert=['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'br']
    markdown_content = md(
        html_content, 
        heading_style="ATX",
        bullets="-",
        strong_mark="**",
        emphasis_mark="*"
    )
    
    # 清理多余的空行
    lines = markdown_content.split('\n')
    cleaned_lines = []
    prev_empty = False
    
    for line in lines:
        line = line.strip()
        if not line:  # 空行
            if not prev_empty:  # 只保留一个空行
                cleaned_lines.append('')
                prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False
    
    return '\n'.join(cleaned_lines).strip()


def convert_comment_to_markdown(comment: Dict[str, Any], level: int = 0) -> str:
    """
    递归转换评论及其回复为Markdown格式
    
    Args:
        comment: 评论数据
        level: 嵌套层级，用于缩进
        
    Returns:
        Markdown格式的评论文本
    """
    if not comment.get('text'):
        return ""
    
    # 为不同层级的评论添加缩进
    indent = "  " * level if level > 0 else ""
    
    # 转换评论内容
    comment_markdown = convert_html_to_markdown(comment['text'])
    
    # 构建评论格式
    result = f"{indent}**{comment.get('author', '匿名用户')}** *({comment.get('timestamp', '')})*\n"
    
    # 添加评论内容，为嵌套评论增加缩进
    if level > 0:
        # 为嵌套评论的每一行添加缩进
        content_lines = comment_markdown.split('\n')
        indented_content = '\n'.join(f"{indent}{line}" for line in content_lines)
        result += f"{indented_content}\n"
    else:
        result += f"{comment_markdown}\n"
    
    # 递归处理回复
    if comment.get('replies'):
        result += "\n"
        for reply in comment['replies']:
            reply_markdown = convert_comment_to_markdown(reply, level + 1)
            if reply_markdown:
                result += reply_markdown + "\n"
    
    return result


def process_json_to_markdown(json_file_path: str, output_dir: str = None) -> str:
    """
    处理JSON文件，将其转换为Markdown格式
    
    Args:
        json_file_path: 输入的JSON文件路径
        output_dir: 输出目录，如果为None则使用input文件同级的markdown目录
        
    Returns:
        生成的Markdown文件路径
    """
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 获取帖子信息
    post = data.get('post', {})
    comments = data.get('comments', [])
    
    # 开始构建Markdown内容
    markdown_content = []
    
    # 添加标题
    title = post.get('title', '未知标题')
    markdown_content.append(f"# {title}\n")
    
    # 添加帖子元信息
    author = post.get('author', '')
    timestamp = post.get('timestamp', '')
    url = post.get('url', '')
    
    if author or timestamp or url:
        markdown_content.append("## 帖子信息\n")
        if author:
            markdown_content.append(f"**作者:** {author}")
        if timestamp:
            markdown_content.append(f"**发布时间:** {timestamp}")
        if url:
            markdown_content.append(f"**原文链接:** {url}")
        markdown_content.append("")
    
    # 添加帖子内容
    post_content = post.get('content', '')
    if post_content:
        markdown_content.append("## 正文内容\n")
        post_markdown = convert_html_to_markdown(post_content)
        markdown_content.append(post_markdown)
        markdown_content.append("")
    
    # 添加评论区
    if comments:
        total_comments = data.get('total_comments', len(comments))
        markdown_content.append(f"## 评论区 ({total_comments} 条评论)\n")
        
        for i, comment in enumerate(comments, 1):
            markdown_content.append(f"### 评论 {i}\n")
            comment_markdown = convert_comment_to_markdown(comment)
            if comment_markdown:
                markdown_content.append(comment_markdown)
            markdown_content.append("---\n")
    
    # 合并所有内容
    final_content = '\n'.join(markdown_content).strip()
    
    # 确定输出文件路径
    if output_dir is None:
        json_path = Path(json_file_path)
        output_dir = json_path.parent / "markdown"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 生成输出文件名
    json_filename = Path(json_file_path).stem
    output_filename = f"{json_filename}.md"
    output_path = output_dir / output_filename
    
    # 保存Markdown文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    return str(output_path)


def batch_convert_directory(input_dir: str, output_dir: str = None):
    """
    批量转换目录中的所有JSON文件
    
    Args:
        input_dir: 包含JSON文件的目录
        output_dir: 输出目录
    """
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"❌ 输入目录不存在: {input_dir}")
        return
    
    # 查找所有JSON文件
    json_files = list(input_path.glob("*.json"))
    
    if not json_files:
        print(f"❌ 在 {input_dir} 中没有找到JSON文件")
        return
    
    print(f"📋 找到 {len(json_files)} 个JSON文件")
    
    # 确定输出目录
    if output_dir is None:
        output_dir = input_path / "markdown"
    
    # 批量转换
    success_count = 0
    for json_file in json_files:
        try:
            print(f"🔄 正在转换: {json_file.name}")
            output_path = process_json_to_markdown(str(json_file), output_dir)
            print(f"✅ 已生成: {Path(output_path).name}")
            success_count += 1
        except Exception as e:
            print(f"❌ 转换失败 {json_file.name}: {e}")
    
    print(f"\n🎉 批量转换完成!")
    print(f"📊 成功转换: {success_count}/{len(json_files)} 个文件")
    print(f"📁 输出目录: {output_dir}")


def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(
        description="将OneNewBite抓取的JSON文件转换为Markdown格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 转换单个文件
  python src/html_to_markdown.py output/post_43168058.json
  
  # 批量转换整个目录
  python src/html_to_markdown.py output/ --batch
  
  # 指定输出目录
  python src/html_to_markdown.py output/ --batch --output markdown_output/
        """
    )
    
    parser.add_argument('input', help='输入文件或目录路径')
    parser.add_argument('--batch', '-b', action='store_true', 
                       help='批量处理目录中的所有JSON文件')
    parser.add_argument('--output', '-o', 
                       help='输出目录路径（可选）')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ 输入路径不存在: {args.input}")
        return
    
    try:
        if args.batch or input_path.is_dir():
            # 批量处理模式
            print("🚀 启动批量转换模式...")
            batch_convert_directory(str(input_path), args.output)
        else:
            # 单文件处理模式
            print(f"🚀 转换单个文件: {input_path.name}")
            output_path = process_json_to_markdown(str(input_path), args.output)
            print(f"✅ 转换完成!")
            print(f"📄 输出文件: {output_path}")
    
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")


if __name__ == "__main__":
    main()
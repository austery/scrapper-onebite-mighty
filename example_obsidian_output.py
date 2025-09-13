#!/usr/bin/env python3
"""
Example script showing the new Obsidian-optimized output format
Creates a sample article and attachment structure
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from obsidian_helpers import (
    generate_obsidian_filename,
    generate_yaml_frontmatter,
    OBSIDIAN_ARTICLES_DIR,
    OBSIDIAN_ATTACHMENTS_DIR
)

def create_example_output():
    """Create example Obsidian output structure"""
    print("🚀 Creating example Obsidian output structure...\n")
    
    # Ensure directories exist
    OBSIDIAN_ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sample post data
    sample_posts = [
        {
            'title': 'Yian的读书帖-持续买进',
            'author': 'Yian',
            'timestamp': '2w',
            'content': '<p>这是一篇关于投资的文章...</p><img src="../attachments/investment-chart.png" alt="投资图表" />',
            'url': 'https://onenewbite.com/posts/12345'
        },
        {
            'title': '我的2024年度投资展望',
            'author': 'InvestmentGuru',
            'timestamp': '1y',
            'content': '<p>2024年市场展望...</p><img src="../attachments/market-outlook.jpg" alt="市场展望" />',
            'url': 'https://onenewbite.com/posts/67890'
        }
    ]
    
    # Create sample attachments
    sample_attachments = [
        'investment-chart.png',
        'market-outlook.jpg',
        'economic-data.webp'
    ]
    
    print("📁 Creating sample attachments...")
    for attachment in sample_attachments:
        attachment_path = OBSIDIAN_ATTACHMENTS_DIR / attachment
        with open(attachment_path, 'w') as f:
            f.write(f"# Sample attachment: {attachment}")
        print(f"  ✅ Created: {attachment_path}")
    
    print(f"\n📄 Creating sample articles...")
    for post in sample_posts:
        # Generate Obsidian filename
        from obsidian_helpers import parse_relative_time_to_date
        published_date = parse_relative_time_to_date(post['timestamp'])
        filename = generate_obsidian_filename(post['title'], published_date)
        
        # Generate YAML frontmatter
        yaml_frontmatter = generate_yaml_frontmatter(post, post['url'])
        
        # Create markdown content
        markdown_content = f"""{yaml_frontmatter}# 主帖内容

{post['content']}

---

## 评论

### 示例评论作者
这是一条示例评论内容...

*发布时间: 1d*

---
"""
        
        # Save file
        article_path = OBSIDIAN_ARTICLES_DIR / f"{filename}.md"
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"  ✅ Created: {article_path}")
    
    print("\n🎉 Example structure created successfully!")
    print("\n📂 Final structure:")
    print("output/")
    print("├── attachments/")
    for attachment in sorted(OBSIDIAN_ATTACHMENTS_DIR.glob('*')):
        print(f"│   ├── {attachment.name}")
    print("└── articles/")
    for article in sorted(OBSIDIAN_ARTICLES_DIR.glob('*.md')):
        print(f"    └── {article.name}")
    
    print("\n🚀 Ready for Obsidian import!")
    print("To import into Obsidian:")
    print("1. Copy the 'output' folder to your Obsidian vault")
    print("2. The articles will appear with proper metadata")
    print("3. All images will be in the unified attachments folder")
    print("4. Relative links between articles and attachments work automatically")

if __name__ == "__main__":
    create_example_output()
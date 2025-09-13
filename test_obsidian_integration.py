#!/usr/bin/env python3
"""
Test script for Obsidian integration functionality
Tests date parsing, filename generation, and YAML frontmatter
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from obsidian_helpers import (
    parse_relative_time_to_date,
    sanitize_title_for_filename,
    generate_obsidian_filename,
    generate_yaml_frontmatter,
    OBSIDIAN_ARTICLES_DIR,
    OBSIDIAN_ATTACHMENTS_DIR
)

def test_date_parsing():
    """Test relative time to absolute date conversion"""
    print("🔍 Testing date parsing...")
    
    test_cases = [
        ("2w", "should be ~14 days ago"),
        ("1y", "should be ~365 days ago"),
        ("3d", "should be ~3 days ago"),
        ("1m", "should be ~30 days ago"),
        ("", "should be today"),
        ("invalid", "should be today"),
    ]
    
    for relative_time, expected in test_cases:
        result = parse_relative_time_to_date(relative_time)
        print(f"  '{relative_time}' -> {result} ({expected})")
    
    print("✅ Date parsing test completed\n")

def test_title_sanitization():
    """Test title sanitization for filenames"""
    print("🔍 Testing title sanitization...")
    
    test_cases = [
        ("这是一个正常的标题", "这是一个正常的标题"),
        ("Title with / slash", "Title with  slash"),
        ("Title: with colon", "Title with colon"),
        ("Title with | pipe", "Title with  pipe"),
        ("   Extra   Spaces   ", "Extra Spaces"),
        ("", "Untitled"),
        ("A" * 150, "Should be truncated to 100 chars"),
    ]
    
    for title, expected_note in test_cases:
        result = sanitize_title_for_filename(title)
        print(f"  '{title}' -> '{result}' ({expected_note})")
    
    print("✅ Title sanitization test completed\n")

def test_obsidian_filename_generation():
    """Test Obsidian filename generation"""
    print("🔍 Testing Obsidian filename generation...")
    
    test_cases = [
        ("Yian的读书帖-持续买进", "2024-03-15", "2024-03-15 - Yian的读书帖-持续买进"),
        ("我的2024年度投资展望", "2025-01-20", "2025-01-20 - 我的2024年度投资展望"),
        ("Title with: special chars", "2024-01-01", "2024-01-01 - Title with special chars"),
    ]
    
    for title, date, expected in test_cases:
        result = generate_obsidian_filename(title, date)
        print(f"  '{title}' + '{date}' -> '{result}'")
        assert result == expected, f"Expected '{expected}', got '{result}'"
    
    print("✅ Obsidian filename generation test completed\n")

def test_yaml_frontmatter():
    """Test YAML frontmatter generation"""
    print("🔍 Testing YAML frontmatter generation...")
    
    sample_post_data = {
        'title': 'Yian的读书帖-持续买进',
        'author': 'Yian',
        'timestamp': '2w'
    }
    
    url = "https://onenewbite.com/posts/12345"
    
    result = generate_yaml_frontmatter(sample_post_data, url)
    print("Generated YAML frontmatter:")
    print(result)
    
    # Verify key components are present
    assert "title: Yian的读书帖-持续买进" in result
    assert "source: https://onenewbite.com/posts/12345" in result
    assert "author: Yian" in result
    assert "published:" in result
    assert "tags:" in result
    assert "- t-clipping" in result
    assert "- mighty_import" in result
    assert "status: inbox" in result
    
    print("✅ YAML frontmatter test completed\n")

def test_directory_setup():
    """Test that directories can be created"""
    print("🔍 Testing directory setup...")
    
    print(f"Articles directory: {OBSIDIAN_ARTICLES_DIR}")
    print(f"Attachments directory: {OBSIDIAN_ATTACHMENTS_DIR}")
    
    # Create directories
    OBSIDIAN_ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    assert OBSIDIAN_ARTICLES_DIR.exists(), "Articles directory should exist"
    assert OBSIDIAN_ATTACHMENTS_DIR.exists(), "Attachments directory should exist"
    
    print("✅ Directory setup test completed\n")

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting Obsidian integration tests...\n")
    
    try:
        test_date_parsing()
        test_title_sanitization()
        test_obsidian_filename_generation()
        test_yaml_frontmatter()
        test_directory_setup()
        
        print("🎉 All tests passed! Obsidian integration is ready.")
        print("\nExpected output structure:")
        print("output/")
        print("├── attachments/")
        print("│   └── (all images)")
        print("└── articles/")
        print("    └── YYYY-MM-DD - Article Title.md")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
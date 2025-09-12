# Claude Technical Specification - OneNewBite Scraper

## Core Philosophy

### 1. "Simplicity is the Soul of Wisdom"

- If a function exceeds 30 lines, redesign it
- If you need more than 3 levels of nesting, your data structure is wrong
- Never write 100 lines for what can be done in 10

### 2. "Never Break Existing Functionality"

- Any change must not break working code
- Backward compatibility is sacred
- New features are nice-to-have, stability is life-or-death

### 3. "Pragmatism Above All"

- Solve real problems, not imaginary threats
- User wants comments scraped? Focus on scraping comments, no fancy bullshit
- Code serves production, not technology showcase

## Technical Standards

### Selector Specification

```python
# ❌ Garbage code - NEVER do this
selector = '#sidebar-comments-region > div:nth-child(2) > div:nth-child(1)'

# ✅ Good taste - Stable and reliable
selector = '#sidebar-comments-region .comments-region'
```

**Iron Rules:**

- **NEVER** use nth-child or position-based selectors
- **NEVER** hardcode array indices to locate elements
- **ALWAYS** use semantic selectors (IDs, classes, attributes)

### Async Operation Standards

```python
# ❌ Garbage code - No exception handling
await page.click(button)

# ✅ Good taste - Defensive programming
try:
    if await button.is_visible():
        await button.click()
        await page.wait_for_load_state('networkidle')
except Exception as e:
    # Explicit error handling, not swallowing exceptions
    print(f"Click failed: {e}")
    return False
```

### Data Structure Design

```python
# ❌ Garbage design - Chaotic nesting
comments = {
    'data': {
        'items': [
            {'comment': {'text': '...', 'meta': {...}}}
        ]
    }
}

# ✅ Good taste - Flat and clear
comments = [
    {
        'text': '...',
        'author': '...',
        'timestamp': '...',
        'replies': []  # Only nesting allowed here - it's business logic
    }
]
```

## Code Review Standards

### Layer 1: Is This a Real Problem?

Before writing any code, ask yourself:

- Does the user actually need this feature?
- Is there a simpler solution?
- Will this break anything?

### Layer 2: Data Flow Analysis

```text
Good code has clear data flow:
Input(URL) → Login → Load Page → Extract Data → Output(JSON)

Each step should be independent, testable, side-effect free
```

### Layer 3: Complexity Review

- Functions do one thing and do it well
- Eliminate all unnecessary conditional branches
- Use data structures instead of complex logic

## Practical Standards

### Handling OneNewBite Specific Issues

#### 1. Multi-level Previous Comments

```python
# Don't assume single level
# Recursively find all levels, including nested in replies
async def load_all_previous_comments(page):
    """Simple, brutal, but effective"""
    for _ in range(MAX_ITERATIONS):
        buttons = await page.locator('a:has-text("Previous Comments")').all()
        if not buttons:
            break
        for button in buttons:
            if await button.is_visible():
                await button.click()
                await page.wait_for_timeout(1500)
```

#### 2. Comment Completeness Verification

```python
# Always verify your assumptions
expected = await get_expected_count(page)
actual = count_all_comments(extracted)
if actual < expected * 0.8:  # 80% is acceptable threshold
    print(f"⚠️ Possibly missing comments: {expected - actual}")
```

#### 3. Batch Processing Deduplication

```python
# Simple and direct dedup logic
def is_processed(url):
    filename = f"post_{extract_id(url)}.json"
    return Path(f"output/{filename}").exists()
```

## Error Handling Philosophy

### 1. Fail Fast

```python
# Don't try to "fix" bad data
if not config.USERNAME or not config.PASSWORD:
    raise ValueError("No credentials, no scraping")
```

### 2. Clear Error Messages

```python
# ❌ Garbage message
print("Error occurred")

# ✅ Useful information
print(f"Login failed: username field {selector} doesn't exist at {page.url}")
```

### 3. Graceful Degradation

```python
# If partial functionality fails, ensure obtained data can be saved
try:
    comments = await extract_all_comments(page)
except Exception as e:
    comments = await extract_visible_comments(page)  # Fallback
    print(f"Full extraction failed, returning visible comments: {e}")
```

## Debugging Principles

### 1. Observability

Log every critical operation:

```python
print(f"🔍 Processing post: {post_id}")
print(f"📊 Expected comments: {expected}, Actual: {actual}")
print(f"✅ Saved to: {filename}")
```

### 2. Reproducibility

Save enough information to reproduce issues:

- Screenshot critical page states
- Save HTML for offline debugging
- Log selector match results

### 3. Progressive Debugging

```python
# Ensure basics work first
await test_login()
await test_single_comment_extraction()
await test_full_page_extraction()
# Then handle edge cases
```

## Performance Guidelines

### 1. Avoid Unnecessary Waits

```python
# ❌ Stupid fixed waits
await page.wait_for_timeout(5000)

# ✅ Smart waiting
await page.wait_for_selector('.comment', state='visible')
```

### 2. Batch Operations

```python
# ❌ Process one by one
for url in urls:
    result = await process(url)
    save(result)

# ✅ Failures don't affect others
results = []
for url in urls:
    try:
        results.append(await process(url))
    except Exception as e:
        print(f"Skipping failed URL: {url}")
        continue
save_all(results)
```

## Bottom Line Principles

1. **Reliability > Features** - Better fewer features than instability
2. **Simple > Clever** - Future you will thank present you for simple code
3. **Explicit > Implicit** - Don't make people guess what code does
4. **Practical > Perfect** - 85% success rate beats pursuing 100% but failing often

## Forbidden List

**NEVER:**

- Commit .env files with passwords
- Use nth-child selectors
- Ignore exceptions without logging
- Assume page structure won't change
- Turn off headless mode in production
- Trust websites to work as expected

**ALWAYS:**

- Verify every assumption
- Prepare for failure
- Keep code readable
- Test edge cases
- Document why, not just what

---

*"Talk is cheap. Show me the code." - Linus Torvalds*

Remember: We write code not to show off intelligence, but to solve problems. If code doesn't run reliably, it's garbage no matter how elegant.

# mini-praw


`mini-praw` is a tiny, **unauthenticated**, read-only Python client for Reddit’s public JSON endpoints, inspired by PRAW but intentionally lightweight and dependency-free.

- 🚫 **No Reddit login, client ID, or secret needed**
- 📦 **One single file (`mini_praw.py`)**
- 🔎 Subreddit search
- ♨️ Subreddit listings: `hot`, `new`, `top`
- 📝 Submission details + **full comment tree**
- 🎞️ Extracts **media URLs** (images, videos, galleries)
- 🛑 Built-in **rate limiting** to avoid hammering Reddit
- 🧩 Optionally include the **full raw JSON** for any call

`mini-praw` is ideal for learning, exploration, academic scraping, content analysis, and small personal tools — all without needing Reddit OAuth credentials.

---

## ❓ Why Unauthenticated Scraping?

In **2025**, Reddit introduced the **Responsible Builder Policy** and a new approval process for API access for developers, moderators, and researchers. Self-service creation of new OAuth apps is no longer available; instead, you must submit a **support ticket** and wait for manual approval.

In the discussion on this policy, some developers and researchers have reported concerns such as:

- ❌ Requests taking a long time to receive a response  
- ❌ Requests being denied or apparently “blackholed”  
- ❌ Uncertainty about which research or tooling use-cases will be approved  

Because of these new restrictions, **unauthenticated access via public JSON endpoints** has become an important fallback for lightweight, ethical, read-only research tasks, especially when dealing with:

- Public subreddit data  
- Non-sensitive comment analysis  
- Small-scale text mining  
- Teaching, prototyping, or exploratory analysis  

`mini-praw` exists to support these workflows while remaining simple, transparent, and respectful of Reddit’s servers.

---

## Installation

Simply download or copy the file:

```
mini_praw.py
```

into your project directory:

```
your-project/
├── mini_praw.py
└── your_script.py
```

Import it:

```python
from mini_praw import Reddit
```

No installation, no dependencies, no authentication.

---

## Quick Start

```python
from mini_praw import Reddit

reddit = Reddit(
    user_agent="mini-praw-demo/0.1 (by u/yourusername)",
    request_interval=1.0,
    return_full=False,
)
```

---

## Features

### 🔎 Search for subreddits

```python
subs = reddit.search_subreddits("environment", limit=5)
for s in subs:
    print(s["name"], s["subscribers"])
```

Want full raw JSON?

```python
subs = reddit.search_subreddits("environment", limit=5, full=True)
print(subs[0]["raw"])
```

---

### ♨️ Browse subreddit posts

```python
sub = reddit.subreddit("environment")

for post in sub.hot(limit=3):
    print("[HOT]", post["title"], post["ups"])

for post in sub.new(limit=3):
    print("[NEW]", post["title"])

for post in sub.top(limit=3, time_filter="week"):
    print("[TOP/week]", post["title"], post["score"])
```

Each post is a simple `dict` with keys like:

```python
{
    "id": "1p6got5",
    "title": "...",
    "selftext": "",
    "permalink": "/r/environment/comments/...",
    "url": "https://...",
    "created_utc": 1764087480.0,
    "author": "username",
    "score": 1244,
    "ups": 1244,
    "upvote_ratio": 0.93,
    "num_comments": 210,
    "media_urls": [...],
    "primary_media_url": "...",
}
```

---

### 📝 Fetch a submission + comments

```python
submission = reddit.submission(
    id="1p6got5",
    more_limit=10,
    full=True
)

print(submission["title"])
print("Comments:", len(submission["comments"]))
```

Comments are returned as a flat list:

```python
{
    "id": "h3k4l9a",
    "author": "user123",
    "body": "Comment text...",
    "created_utc": 1700000000,
    "ups": 42,
    "downs": 0,
    "depth": 2
}
```

---

### 🎞️ Media Extraction

`mini-praw` extracts URLs from:

- `preview`
- `media_metadata`
- `gallery_data`
- `reddit_video`
- direct media links

---

### 🛑 Safe by default

```python
reddit = Reddit(request_interval=1.0)
```

Keeps scraping polite and reduces risk of rate blocking.

---

## License (CC0 1.0 Universal)

```
mini-praw  by Carsten Schwemmer is released under CC0 1.0 Universal.
You may use, modify, and distribute this software without restriction.
```

Full license text: https://creativecommons.org/publicdomain/zero/1.0/

---

## Contributing

Issues, ideas, and PRs welcome!

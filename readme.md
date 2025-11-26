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

`mini-praw` is made for learning, exploration, academic scraping, content analysis, and small personal tools.

---

## ❓ Why Unauthenticated Scraping?

In **2025**, Reddit introduced the [Responsible Builder Policy](https://www.reddit.com/r/redditdev/comments/1oug31u/introducing_the_responsible_builder_policy_new/) and a new approval process for API access for developers, moderators, and researchers. Self-service creation of new OAuth apps is no longer available; instead, you must submit a support ticket and wait for manual approval.

Some developers and researchers have reported concerns such as:

- requests taking a long time to receive a response  
- requests being denied or apparently “blackholed”  
- uncertainty about which research or tooling use-cases will be approved  

Because of these new restrictions, unauthenticated access via public JSON endpoints has become an important fallback for lightweight, ethical, read-only research tasks, especially when dealing with:

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
    user_agent="Carsten Schwemmer - Researcher at University of Munich (LMU)",
    request_interval=1.0,
    return_full=False,
)
```
It is recommended to provide a transparent user agent string and set a responsible request interval (such as the default of 1 second). For experienced users, ```return_Full=True``` will result in all data retrievals to include the raw JSON data returned by Reddit. Otherwise, only selected metadata will be returned.
---

## Features

### 🔎 Search for subreddits

```python
subs = reddit.search_subreddits("environment", limit=5)
for s in subs:
    print(s["name"], s["subscribers"])
```

If you want full JSON metadata for only selected data, you can use ```full=True``` for single function calls.

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

Each post is a simple Python `dict` with keys like:

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

The ``more_limit`` parameter defines how many batches of comments will be retrieved. Setting it to ```None``` will try to extract all available comments. Note that neither this function nor any other component of mini-praw allows data retrieval beyond the rate limits of Reddit (usually a maximum of 1.000 items).

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
{'id': 'nqm9boy',
 'author': 'Moustached92',
 'body': 'Sounds like and episode of "Love, Death + Robots"',
 'created_utc': 1764028089.0,
 'ups': 34,
 'downs': 0,
 'depth': 3,
 'parent_fullname': 't1_nqm5e6h',
 'parent_id': 'nqm5e6h',
 'in_reply_to': 'nqm5e6h',
 'is_top_level': False}
```
Hierarchies of comments can be reconstructed using ```parent_id``` and ```in_reply_to```.

---

### 🎞️ Media Extraction

`mini-praw` extracts URLs from:

- `preview`
- `media_metadata`
- `gallery_data`
- `reddit_video`
- direct media links

These URLs can then be used to download the corresponding media files, e.g. via the Python package ```requests```.
---


## License (CC0 1.0 Universal)

```
mini-praw  by Carsten Schwemmer is released under CC0 1.0 Universal.
You may use, modify, and distribute this software without restriction.
```

Full license text: https://creativecommons.org/publicdomain/zero/1.0/

---

## Contributing

Issues, ideas, and PRs are all welcome to improve mini-praw! :)

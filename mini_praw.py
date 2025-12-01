import time
import requests
from typing import List, Optional, Generator, Dict, Any
from datetime import datetime

BASE_URL = "https://www.reddit.com"
DEFAULT_UA = "mini-praw"

def _format_date(ts: float) -> str:
    """Convert UNIX timestamp → 'YYYY-MM-DD'."""
    try:
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return None
        
class RedditHTTPError(Exception):
    """Custom exception for HTTP errors when talking to Reddit."""


class Reddit:
    """
    Lightweight, unauthenticated client for Reddit's public JSON endpoints.

    Top-level API:
      - search_subreddits(query, limit, full=None)
      - subreddit(name).hot(limit, full=None)
      - subreddit(name).new(limit, full=None)
      - subreddit(name).top(limit, time_filter, full=None)
      - submission(id, more_limit=None, full=None)

    `full` parameter behavior:
      - If full is None, use the client-wide default `self.return_full`.
      - If full is True/False, override the default for that call.

    All data returned is plain Python types (dicts, lists, etc.).
    """

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        request_interval: float = 1.0,
        return_full: bool = False,
    ):
        """
        Parameters
        ----------
        user_agent : str
            User-Agent header used for all requests.
        request_interval : float
            Minimum number of seconds between two HTTP requests.
            Default 1.0s ≈ 60 requests/min.
        return_full : bool
            Global default for whether to include raw JSON on all endpoints.
            - False (default): only selected fields.
            - True: add 'raw' / 'raw_response' / etc. by default.
        """
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        self.request_interval = float(request_interval)
        self._last_request_ts: Optional[float] = None

        self.return_full = bool(return_full)

    def _get(self, path: str, params: Optional[dict] = None) -> Dict[str, Any]:
        """
        Internal helper to GET JSON from a Reddit path
        with simple rate limiting.
        """
        # Client-side throttling
        now = time.time()
        if self._last_request_ts is not None:
            elapsed = now - self._last_request_ts
            if elapsed < self.request_interval:
                time.sleep(self.request_interval - elapsed)

        url = BASE_URL + path
        resp = self.session.get(url, params=params, timeout=10)
        self._last_request_ts = time.time()

        if not resp.ok:
            raise RedditHTTPError(
                f"Error {resp.status_code} for {url} with params={params}"
            )

        return resp.json()

    # ------------------------------------------------------------------
    # (1) Subreddit search → list of dicts
    # ------------------------------------------------------------------
    def search_subreddits(
        self,
        query: str,
        limit: Optional[int] = 20,
        full: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rough equivalent of reddit.subreddits.search(query, limit=limit).

        Parameters
        ----------
        query : str
        limit : Optional[int]
            Total number of results to return (across pages).
        full : Optional[bool]
            - None: use client default self.return_full.
            - True/False: override for this call.

        Returns
        -------
        List[dict]
            Each dict has selected fields plus, if full=True, a 'raw' key
            with the original listing 'data' from Reddit.
        """
        if full is None:
            full = self.return_full

        results: List[Dict[str, Any]] = []
        after: Optional[str] = None
        remaining = limit

        while True:
            params = {
                "q": query,
                "limit": min(remaining, 100) if remaining is not None else 100,
            }
            if after:
                params["after"] = after

            data = self._get("/subreddits/search.json", params=params)
            children = data["data"]["children"]

            for child in children:
                info = child["data"]
                sub_dict: Dict[str, Any] = {
                    "id": info["id"],
                    "name": info["display_name"],
                    "title": info.get("title"),
                    "subscribers": info.get("subscribers"),
                    "public_description": info.get("public_description"),
                    "url": info.get("url"),
                }
                if full:
                    sub_dict["raw"] = info  # full original JSON for the subreddit

                results.append(sub_dict)

                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        return results

            after = data["data"].get("after")
            if not after or not children:
                break

        return results

    # ------------------------------------------------------------------
    # (2) Subreddit object (top-level interface only)
    # ------------------------------------------------------------------
    def subreddit(self, name: str) -> "Subreddit":
        """
        Return a Subreddit wrapper.

        Example:
            for post in reddit.subreddit("environment").hot(limit=3):
                ...
        """
        return Subreddit(self, name=name)

    # ------------------------------------------------------------------
    # (3) Submission by ID → dict with comments as list[dict]
    # ------------------------------------------------------------------
    def submission(
        self,
        id: str,
        more_limit: Optional[int] = None,
        full: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Fetch a submission (thread) by its base36 ID and return a dict.

        Parameters
        ----------
        id : str
            Base36 submission ID (e.g. "17fm7nl").
        more_limit : Optional[int]
            Max number of 'more' objects to expand (like PRAW's replace_more limit).
              - None (default): expand all available 'more' objects.
              - 0: do not expand any 'more' objects (only initial comments).
              - k > 0: expand at most k 'more' objects.
        full : Optional[bool]
            - None: use client default self.return_full.
            - True/False: override for this call.

        Returns
        -------
        dict
            Submission with selected fields + 'comments' (flattened list of dicts).
            If full=True, also includes:
              - 'raw_response': the full list returned by /comments/{id}.json
              - 'raw_link': the original link 'data' dict
              - 'raw_comments_listing': the original comments listing children
        """
        if full is None:
            full = self.return_full

        # /comments/{id}.json returns [link_listing, comments_listing]
        raw = self._get(f"/comments/{id}.json", params={"limit": 500})
        link_info = raw[0]["data"]["children"][0]["data"]
        comments_listing = raw[1]["data"]["children"]

        media_info = _extract_media(link_info)

        submission_dict: Dict[str, Any] = {
            "id": link_info["id"],
            "title": link_info.get("title", ""),
            "selftext": link_info.get("selftext", ""),
            "permalink": link_info.get("permalink", ""),
            "url": link_info.get("url", ""),
            "created_utc": link_info.get("created_utc", 0.0),
            "created_date": _format_date(link_info.get("created_utc", 0.0)),
            "author": (link_info.get("author") or None),
            "score": link_info.get("score"),

            # extra fields
            "ups": link_info.get("ups"),
            "upvote_ratio": link_info.get("upvote_ratio"),
            "num_comments": link_info.get("num_comments"),

            # media convenience
            "thumbnail": link_info.get("thumbnail"),
            "is_video": link_info.get("is_video"),
            "media": link_info.get("media"),
            "preview": link_info.get("preview"),
            "gallery_data": link_info.get("gallery_data"),
            "media_metadata": link_info.get("media_metadata"),

            "media_urls": media_info["media_urls"],
            "primary_media_url": media_info["primary_media_url"],
        }

        # Fullname of the submission, e.g. "t3_17fm7nl"
        link_fullname = link_info.get("name") or f"t3_{link_info['id']}"

        comments_flat = _flatten_comments(
            reddit=self,
            children=comments_listing,
            link_id=link_fullname,
            more_limit=more_limit,
        )
        submission_dict["comments"] = comments_flat

        if full:
            submission_dict["raw_response"] = raw
            submission_dict["raw_link"] = link_info
            submission_dict["raw_comments_listing"] = comments_listing

        return submission_dict


# ----------------------------------------------------------------------
# Internal helpers for comments (returning dicts)
# ----------------------------------------------------------------------
def _fetch_more_children(
    reddit: Reddit,
    link_id: str,
    child_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    Fetch additional comments for a 'more' object using /api/morechildren.json.
    """
    if not child_ids:
        return []

    params = {
        "api_type": "json",
        "link_id": link_id,
        "children": ",".join(child_ids),
        "limit_children": False,
        "sort": "confidence",
    }
    data = reddit._get("/api/morechildren.json", params=params)
    things = data.get("json", {}).get("data", {}).get("things", [])
    return things


def _flatten_comments(
    reddit: Reddit,
    children: List[Dict[str, Any]],
    link_id: str,
    depth: int = 0,
    more_limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Convert nested Reddit comment JSON into a flat list of dicts with depth.

    - Walks the initial comment tree.
    - For 'more' objects, calls _fetch_more_children().
    - Stops expanding 'more' when `more_limit` is reached (if not None).
    """
    comments: List[Dict[str, Any]] = []
    more_used = 0  # how many 'more' objects have been expanded

    def walk(children_inner, depth_inner: int):
        nonlocal more_used

        for child in children_inner:
            kind = child.get("kind")
            data = child.get("data", {})
            if kind == "t1":  # comment
                parent_fullname = data.get("parent_id") 
                parent_comment_id = None
                is_top_level = False

                if parent_fullname:
                    if parent_fullname.startswith("t1_"):
                        parent_comment_id = parent_fullname[3:]  # strip "t1_"
                    elif parent_fullname.startswith("t3_"):
                        # parent is the submission itself
                        is_top_level = True

                comments.append(
                    {
                        "id": data["id"],
                        "author": (data.get("author") or None),
                        "body": data.get("body", ""),
                        "created_utc": data.get("created_utc", 0.0),
                        "created_date": _format_date(data.get("created_utc", 0.0)),
                        "ups": data.get("ups"),
                        "downs": data.get("downs"),
                        "depth": depth_inner,
                        "parent_fullname": parent_fullname,       # raw Reddit parent_id
                        "parent_id": parent_comment_id,           # comment id or None
                        "in_reply_to": parent_comment_id,         # alias for convenience
                        "is_top_level": is_top_level,             # True if reply to submission
                    }
                )

                replies = data.get("replies")
                if isinstance(replies, dict) and replies.get("data"):
                    walk(replies["data"]["children"], depth_inner + 1)

            elif kind == "more":
                # Respect more_limit
                if more_limit is not None and more_used >= more_limit:
                    continue

                child_ids = data.get("children") or []
                if not child_ids:
                    continue

                more_used += 1
                more_things = _fetch_more_children(reddit, link_id, child_ids)
                if more_things:
                    # These appear at the same depth as this 'more'
                    walk(more_things, depth_inner)

    walk(children, depth)
    return comments


# ----------------------------------------------------------------------
# Media extraction helper
# ----------------------------------------------------------------------
def _extract_media(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Try to extract useful media URLs from a Reddit submission JSON dict.

    Returns a dict with:
      - media_urls: list of URLs (images/videos)
      - primary_media_url: first URL or None
    """
    media_urls: List[str] = []

    # 1) Simple case: direct link that looks like media
    url = info.get("url") or ""
    if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webm"]):
        media_urls.append(url)

    # 2) Preview images
    preview = info.get("preview")
    if isinstance(preview, dict):
        images = preview.get("images") or []
        for img in images:
            src = (img.get("source") or {}).get("url")
            if src:
                src = src.replace("&amp;", "&")
                media_urls.append(src)

            for res in img.get("resolutions") or []:
                u = res.get("url")
                if u:
                    media_urls.append(u.replace("&amp;", "&"))

    # 3) Gallery posts
    gallery_data = info.get("gallery_data")
    media_metadata = info.get("media_metadata")
    if isinstance(gallery_data, dict) and isinstance(media_metadata, dict):
        for item in gallery_data.get("items", []):
            media_id = item.get("media_id")
            meta = media_metadata.get(media_id) or {}
            src = (meta.get("s") or {}).get("u")
            if src:
                media_urls.append(src.replace("&amp;", "&"))

    # 4) Reddit-hosted videos
    media = info.get("media") or info.get("secure_media")
    if isinstance(media, dict):
        rv = media.get("reddit_video") or {}
        fallback_url = rv.get("fallback_url")
        if fallback_url:
            media_urls.append(fallback_url)

    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for u in media_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    return {
        "media_urls": deduped,
        "primary_media_url": deduped[0] if deduped else None,
    }


# ----------------------------------------------------------------------
# Subreddit wrapper (top-level interface only; returns dicts)
# ----------------------------------------------------------------------
class Subreddit:
    """
    Minimal Subreddit wrapper that supports .hot(), .new(), .top().

    All methods yield dicts representing submissions. Example dict:

        {
          "id": ...,
          "title": ...,
          "selftext": ...,
          "permalink": ...,
          "url": ...,
          "created_utc": ...,
          "author": ...,
          "score": ...,
          "ups": ...,
          "upvote_ratio": ...,
          "num_comments": ...,
          "media_urls": [...],
          "primary_media_url": ...,
          ...
        }

    If full=True, each dict also has a 'raw' key with the original
    Reddit JSON for that submission.
    """

    def __init__(self, reddit: Reddit, name: str):
        self.reddit = reddit
        self.name = name

    def _listing(
        self,
        sort: str = "hot",
        limit: Optional[int] = 10,
        time_filter: Optional[str] = None,
        full: Optional[bool] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Generic listing generator for subreddit posts.
        """
        if full is None:
            full = self.reddit.return_full

        path = f"/r/{self.name}/{sort}.json"
        after: Optional[str] = None
        remaining = limit

        while True:
            params: Dict[str, Any] = {
                "limit": min(remaining, 100) if remaining is not None else 100,
            }
            if after:
                params["after"] = after
            if time_filter and sort == "top":
                params["t"] = time_filter

            data = self.reddit._get(path, params=params)
            children = data["data"]["children"]

            for child in children:
                if child.get("kind") != "t3":  # t3 = link / submission
                    continue
                info = child["data"]

                media_info = _extract_media(info)

                submission_dict: Dict[str, Any] = {
                    "id": info["id"],
                    "title": info.get("title", ""),
                    "selftext": info.get("selftext", ""),
                    "permalink": info.get("permalink", ""),
                    "url": info.get("url", ""),
                    "created_utc": info.get("created_utc", 0.0),
                    "created_date": _format_date(info.get("created_utc", 0.0)),
                    "author": (info.get("author") or None),
                    "score": info.get("score"),

                    "ups": info.get("ups"),
                    "upvote_ratio": info.get("upvote_ratio"),
                    "num_comments": info.get("num_comments"),

                    "thumbnail": info.get("thumbnail"),
                    "is_video": info.get("is_video"),
                    "media": info.get("media"),
                    "preview": info.get("preview"),
                    "gallery_data": info.get("gallery_data"),
                    "media_metadata": info.get("media_metadata"),

                    "media_urls": media_info["media_urls"],
                    "primary_media_url": media_info["primary_media_url"],
                }

                if full:
                    submission_dict["raw"] = info  # original JSON for this post

                yield submission_dict

                if remaining is not None:
                    remaining -= 1
                    if remaining <= 0:
                        return

            after = data["data"].get("after")
            if not after or not children:
                break

    # public methods mimic PRAW names, but yield dicts
    def hot(
        self,
        limit: Optional[int] = 10,
        full: Optional[bool] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Return submissions from /r/{name}/hot as dicts."""
        return self._listing("hot", limit=limit, full=full)

    def new(
        self,
        limit: Optional[int] = 10,
        full: Optional[bool] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Return submissions from /r/{name}/new as dicts."""
        return self._listing("new", limit=limit, full=full)

    def top(
        self,
        limit: Optional[int] = 10,
        time_filter: str = "day",
        full: Optional[bool] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Return submissions from /r/{name}/top with an optional time_filter.
        time_filter ∈ {"hour","day","week","month","year","all"}.
        """
        return self._listing("top", limit=limit, time_filter=time_filter, full=full)

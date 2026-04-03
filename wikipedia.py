# wikipedia.py — fetch and cache Wikipedia page summaries
import json, os, re, urllib.request, urllib.parse

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")


def _cache_path(title: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", title)
    return os.path.join(CACHE_DIR, f"wiki_{safe}.json")


def fetch_wiki_summary(title: str) -> dict | None:
    """
    Fetch a Wikipedia page summary using the REST v1 API.
    Returns a dict with keys: extract, content_urls, thumbnail (optional).
    Results are cached to cache/wiki_<title>.json so subsequent calls are instant.
    Returns None if the page is not found or the request fails.
    """
    path = _cache_path(title)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "MatSciExplorer/1.0 (educational tool)"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data
    except Exception:
        return None

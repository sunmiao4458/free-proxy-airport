from __future__ import annotations

import base64
import os
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests
import yaml


OUTPUT_PATH = os.path.join("output", "clash.yaml")
HTTP_TIMEOUT = 25
MAX_RETRIES = 3

DIRECT_SOURCES = [
    {
        "name": "Flikify Free Node",
        "url": "https://raw.githubusercontent.com/a2470982985/getNode/main/clash.yaml",
    },
]

DISCOVERY_SOURCES = [
    {
        "name": "openRunner clash-freenode",
        "index_url": "https://free.datiya.com/",
        "post_pattern": r'href="([^"]+/post/\d{8}/?)"',
        "yaml_pattern": r"https://free\.datiya\.com/uploads/\d{8}-clash\.yaml",
        "limit": 5,
    },
    {
        "name": "free-clash-v2ray GitHub Pages",
        "index_url": "https://raw.githubusercontent.com/free-clash-v2ray/free-clash-v2ray.github.io/main/README.md",
        "post_pattern": None,
        "yaml_pattern": r"https://free-clash-v2ray\.github\.io/uploads/\d{4}/\d{2}/[0-9]-\d{8}\.yaml",
        "limit": 8,
    },
]


def fetch_text(url: str, retries: int = MAX_RETRIES) -> str:
    headers = {
        "User-Agent": "free-proxy-airport/4.0 (+https://github.com/)",
        "Accept": "text/plain, text/yaml, application/yaml, text/html, */*",
    }
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def unique_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def discover_urls(source: dict[str, Any]) -> list[str]:
    index_url = source["index_url"]
    try:
        index_text = fetch_text(index_url)
    except Exception as exc:
        print(f"[WARN] {source['name']}: discovery index failed: {exc}")
        return []

    texts = [index_text]
    post_pattern = source.get("post_pattern")
    if post_pattern:
        post_urls = re.findall(post_pattern, index_text)
        post_urls = [urljoin(index_url, url) for url in unique_ordered(post_urls)]
        for post_url in post_urls[: source.get("limit", 5)]:
            try:
                texts.append(fetch_text(post_url))
            except Exception as exc:
                print(f"[WARN] {source['name']}: post failed {post_url}: {exc}")

    urls: list[str] = []
    yaml_pattern = source["yaml_pattern"]
    for text in texts:
        urls.extend(re.findall(yaml_pattern, text))
    return unique_ordered(urls)[: source.get("limit", 8)]


def maybe_base64_decode(text: str) -> str:
    compact = "".join(text.split())
    if not compact or len(compact) % 4 != 0:
        return text
    if not re.fullmatch(r"[A-Za-z0-9+/=]+", compact):
        return text
    try:
        decoded = base64.b64decode(compact, validate=True).decode("utf-8")
    except Exception:
        return text
    return decoded if "proxies:" in decoded or "://" in decoded else text


def load_yaml_document(text: str) -> Any:
    text = maybe_base64_decode(text)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def extract_proxies(text: str) -> list[dict[str, Any]]:
    document = load_yaml_document(text)
    if isinstance(document, dict):
        proxies = document.get("proxies", [])
    elif isinstance(document, list):
        proxies = document
    else:
        proxies = []

    clean: list[dict[str, Any]] = []
    for proxy in proxies:
        if not isinstance(proxy, dict):
            continue
        if "name" not in proxy or "type" not in proxy:
            continue
        clean.append(dict(proxy))
    return clean


def collect_proxies() -> list[dict[str, Any]]:
    urls: list[tuple[str, str]] = [(source["name"], source["url"]) for source in DIRECT_SOURCES]
    for source in DISCOVERY_SOURCES:
        discovered = discover_urls(source)
        urls.extend((source["name"], url) for url in discovered)

    proxies: list[dict[str, Any]] = []
    for source_name, url in unique_ordered_pairs(urls):
        try:
            text = fetch_text(url)
            found = extract_proxies(text)
            print(f"[OK] {source_name}: {len(found)} proxies from {url}")
            proxies.extend(found)
        except Exception as exc:
            print(f"[WARN] {source_name}: skipped {url}: {exc}")
    return deduplicate_by_name(proxies)


def unique_ordered_pairs(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for source_name, url in items:
        if url not in seen:
            seen.add(url)
            result.append((source_name, url))
    return result


def deduplicate_by_name(proxies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, proxy in enumerate(proxies, start=1):
        name = str(proxy.get("name", "")).strip()
        if not name:
            name = f"proxy-{index}"
            proxy["name"] = name
        if name in seen:
            continue
        seen.add(name)
        result.append(proxy)
    return result


def existing_output() -> dict[str, Any] | None:
    if not os.path.exists(OUTPUT_PATH):
        return None
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def build_config(proxies: list[dict[str, Any]]) -> dict[str, Any]:
    names = [str(proxy["name"]) for proxy in proxies]
    return {
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",
        "generated-at": datetime.now(timezone.utc).isoformat(),
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "AUTO",
                "type": "url-test",
                "proxies": names,
                "url": "http://www.gstatic.com/generate_204",
                "interval": 120,
            }
        ],
        "rules": [
            "GEOIP,CN,DIRECT",
            "MATCH,AUTO",
        ],
    }


def write_config(config: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)


def main() -> None:
    proxies = collect_proxies()
    if not proxies:
        previous = existing_output()
        if previous and previous.get("proxies"):
            print("[WARN] no fresh proxies found; keeping existing output/clash.yaml")
            return
        raise SystemExit("no proxies found from any source")

    config = build_config(proxies)
    write_config(config)
    print(f"[DONE] wrote {OUTPUT_PATH} with {len(proxies)} unique proxies")


if __name__ == "__main__":
    main()

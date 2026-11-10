#!/usr/bin/env python3
"""Add email addresses to the clinic leads by checking each clinic's own website
(home page plus a few contact/about pages) for mailto links and visible emails.

Usage: python3 scripts/find_emails.py leads/aesthetics_clinics_mobiles.csv leads/aesthetics_clinics_with_emails.csv
"""
import csv
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}")
CF_RE = re.compile(r'data-cfemail="([0-9a-fA-F]+)"')
LINK_RE = re.compile(r'href=["\']([^"\'#]+)["\']', re.I)
CONTACT_WORDS = ("contact", "about", "get-in-touch", "enquir", "book", "find-us", "privacy")
# Sites that are booking platforms / social profiles, not the clinic's own site
SKIP_HOSTS = ("facebook.", "instagram.", "fresha.", "treatwell.", "booksy.", "linktr.ee",
              "tiktok.", "phorest.", "setmore.", "square.site", "wa.me", "google.")
BAD_EMAIL = re.compile(
    r"(\.(png|jpe?g|gif|webp|svg|css|js)$|example\.|sentry|wixpress|domain\.com|yourdomain|"
    r"email\.com$|@sentry|godaddy|squarespace|wordpress|@2x|u00|noreply|no-reply)", re.I)


def cf_decode(h):
    k = int(h[:2], 16)
    return "".join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))


def emails_in(html):
    found = set(EMAIL_RE.findall(urllib.parse.unquote(html)))
    found |= {cf_decode(h) for h in CF_RE.findall(html)}
    return {e.strip(".").lower() for e in found if not BAD_EMAIL.search(e)}


def fetch(s, url):
    # This environment only proxies HTTPS, so try the https:// form first.
    tries = [url]
    if url.startswith("http://"):
        tries = ["https://" + url[7:], url]
    for u in tries:
        try:
            r = s.get(u, timeout=12, allow_redirects=True)
            if r.ok and "html" in r.headers.get("content-type", "html"):
                return r.url, r.text[:800_000]
        except Exception:
            continue
    return None, ""


def lookup(site):
    host = urllib.parse.urlparse(site).netloc.lower()
    if not host or any(h in host for h in SKIP_HOSTS):
        return [], "no own website"
    s = requests.Session()
    s.headers["User-Agent"] = UA
    final, html = fetch(s, site)
    if not final:
        return [], "site unreachable"
    found = emails_in(html)
    base_host = urllib.parse.urlparse(final).netloc
    pages = []
    for href in LINK_RE.findall(html):
        u = urllib.parse.urljoin(final, href)
        p = urllib.parse.urlparse(u)
        if p.netloc == base_host and any(w in p.path.lower() for w in CONTACT_WORDS) and u not in pages:
            pages.append(u)
    if not found:
        pages += [urllib.parse.urljoin(final, x) for x in ("/contact", "/contact-us")]
    for u in pages[:4]:
        if found and len(pages) > 2 and "privacy" in u:
            continue
        _, h = fetch(s, u)
        found |= emails_in(h)
    dom = base_host.removeprefix("www.")
    # Prefer emails on the clinic's own domain, then other addresses
    ranked = sorted(found, key=lambda e: (not e.endswith(dom), len(e)))
    return ranked[:3], "found" if ranked else "no email on site"


def main():
    src, dst = sys.argv[1], sys.argv[2]
    rows = list(csv.DictReader(open(src)))
    with ThreadPoolExecutor(32) as ex:
        results = list(ex.map(lambda r: lookup(r["website"]) if r["website"] else ([], "no website"), rows))
    for r, (emails, status) in zip(rows, results):
        r["email"] = emails[0] if emails else ""
        r["other_emails"] = "; ".join(emails[1:])
        r["email_status"] = status
    cols = ["city", "name", "mobile", "email", "other_emails", "email_status"] + \
        [c for c in rows[0] if c not in ("city", "name", "mobile", "email", "other_emails", "email_status")]
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter(r["email_status"] for r in rows))


if __name__ == "__main__":
    main()

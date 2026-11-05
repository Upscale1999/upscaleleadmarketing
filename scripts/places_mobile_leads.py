#!/usr/bin/env python3
"""Pull aesthetics clinics from the Google Places API (New) and keep only those
whose listed phone number is a UK mobile (07xxx / +44 7xxx).

Coverage: Text Search caps each query at 60 results, so every city is split into
a grid of small rectangles and several search terms are run per cell. Results
are de-duplicated by Google place ID.

Usage:
    GOOGLE_MAPS_API_KEY=... python3 scripts/places_mobile_leads.py [out_dir]

If GOOGLE_MAPS_API_KEY is unset, the request is sent without a key (useful when
a proxy injects the X-Goog-Api-Key header).
"""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.nationalPhoneNumber", "places.internationalPhoneNumber",
    "places.websiteUri", "places.googleMapsUri", "places.rating",
    "places.userRatingCount", "places.businessStatus", "places.types",
    "nextPageToken",
])

# (south, west, north, east) bounding boxes covering each city + inner suburbs
CITIES = {
    "Liverpool": (53.33, -3.05, 53.50, -2.82),
    "Manchester": (53.38, -2.35, 53.56, -2.13),
    "Leeds": (53.72, -1.70, 53.88, -1.40),
}
GRID = 4  # 4x4 cells per city
QUERIES = [
    "aesthetics clinic", "aesthetic clinic", "botox and fillers",
    "lip fillers", "skin clinic", "anti wrinkle injections",
    "medical aesthetics", "dermal fillers",
]


def is_uk_mobile(num: str) -> bool:
    d = re.sub(r"\D", "", num or "")
    if d.startswith("44"):
        d = "0" + d[2:]
    if len(d) != 11 or not d.startswith("07"):
        return False
    # 070 = personal numbering, 076 = pagers (except 07624 Isle of Man mobile)
    if d.startswith("070") or (d.startswith("076") and not d.startswith("07624")):
        return False
    return True


def search(body: dict, key: str | None) -> dict:
    headers = {"Content-Type": "application/json", "X-Goog-FieldMask": FIELDS}
    if key:
        headers["X-Goog-Api-Key"] = key
    req = urllib.request.Request(ENDPOINT, json.dumps(body).encode(), headers)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")
            if e.code in (429, 500, 503) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise SystemExit(f"Places API error {e.code}: {msg}")
    return {}


def cells(box):
    s, w, n, e = box
    dy, dx = (n - s) / GRID, (e - w) / GRID
    for i in range(GRID):
        for j in range(GRID):
            yield (s + i * dy, w + j * dx, s + (i + 1) * dy, w + (j + 1) * dx)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "leads"
    os.makedirs(out_dir, exist_ok=True)
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    seen: dict[str, dict] = {}
    calls = 0
    for city, box in CITIES.items():
        for cs, cw, cn, ce in cells(box):
            for q in QUERIES:
                body = {
                    "textQuery": q, "pageSize": 20, "regionCode": "GB",
                    "locationRestriction": {"rectangle": {
                        "low": {"latitude": cs, "longitude": cw},
                        "high": {"latitude": cn, "longitude": ce}}},
                }
                while True:
                    data = search(body, key)
                    calls += 1
                    for p in data.get("places", []):
                        if p["id"] not in seen:
                            p["_city"] = city
                            seen[p["id"]] = p
                    tok = data.get("nextPageToken")
                    if not tok:
                        break
                    body = {**body, "pageToken": tok}
                    time.sleep(1.5)
        print(f"{city}: {sum(1 for p in seen.values() if p['_city'] == city)} places (calls so far {calls})")

    with open(os.path.join(out_dir, "all_places_raw.json"), "w") as f:
        json.dump(list(seen.values()), f, indent=1)

    rows = []
    for p in seen.values():
        phone = p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber") or ""
        if not is_uk_mobile(phone) or p.get("businessStatus") == "CLOSED_PERMANENTLY":
            continue
        rows.append({
            "city": p["_city"],
            "name": p.get("displayName", {}).get("text", ""),
            "mobile": phone,
            "mobile_e164": "+44" + re.sub(r"\D", "", phone).lstrip("0")[-10:],
            "address": p.get("formattedAddress", ""),
            "website": p.get("websiteUri", ""),
            "rating": p.get("rating", ""),
            "reviews": p.get("userRatingCount", ""),
            "google_maps_url": p.get("googleMapsUri", ""),
            "place_id": p["id"],
        })
    rows.sort(key=lambda r: (r["city"], r["name"].lower()))
    path = os.path.join(out_dir, "aesthetics_clinics_mobiles.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["city"])
        w.writeheader()
        w.writerows(rows)
    print(f"API calls: {calls}; unique places: {len(seen)}; with mobile: {len(rows)} -> {path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch Yandex.Metrika stats and write to stats/data.json."""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

COUNTER_ID = "109555301"
DAYS = 30
BASE = "https://api-metrika.yandex.net/stat/v1/data"
OUT_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def get(token: str, params: dict) -> dict:
    params["ids"] = COUNTER_ID
    params.setdefault("date1", f"{DAYS}daysAgo")
    params.setdefault("date2", "today")
    url = f"{BASE}?{urlencode(params)}"
    req = Request(url, headers={"Authorization": f"OAuth {token}"})
    with urlopen(req) as r:
        return json.load(r)


def fetch(token: str) -> dict:
    # Summary
    s = get(token, {
        "metrics": ",".join([
            "ym:s:visits",
            "ym:s:users",
            "ym:s:pageviews",
            "ym:s:bounceRate",
            "ym:s:avgVisitDurationSeconds",
        ]),
    })
    totals = s.get("totals", [[0, 0, 0, 0, 0]])[0]
    summary = {
        "active_users":          int(totals[1]),
        "sessions":              int(totals[0]),
        "page_views":            int(totals[2]),
        "avg_session_duration":  round(float(totals[4]), 1),
        "bounce_rate":           round(float(totals[3]) / 100, 4),
    }

    # Daily chart
    d = get(token, {
        "dimensions": "ym:s:date",
        "metrics": "ym:s:visits,ym:s:users",
        "sort": "ym:s:date",
        "limit": DAYS,
    })
    daily = [
        {
            "date":     row["dimensions"][0]["name"],
            "sessions": int(row["metrics"][0]),
            "users":    int(row["metrics"][1]),
        }
        for row in d.get("data", [])
    ]

    # Top pages
    p = get(token, {
        "dimensions": "ym:s:URLPath",
        "metrics": "ym:s:pageviews,ym:s:users",
        "sort": "-ym:s:pageviews",
        "limit": 10,
    })
    top_pages = [
        {
            "path":  row["dimensions"][0]["name"],
            "views": int(row["metrics"][0]),
            "users": int(row["metrics"][1]),
        }
        for row in p.get("data", [])
    ]

    # Devices
    dv = get(token, {
        "dimensions": "ym:s:deviceCategory",
        "metrics": "ym:s:visits",
        "sort": "-ym:s:visits",
    })
    devices = [
        {
            "device":   row["dimensions"][0]["name"],
            "sessions": int(row["metrics"][0]),
        }
        for row in dv.get("data", [])
    ]

    # Countries
    c = get(token, {
        "dimensions": "ym:s:regionCountry",
        "metrics": "ym:s:users",
        "sort": "-ym:s:users",
        "limit": 10,
    })
    countries = [
        {
            "country": row["dimensions"][0]["name"],
            "users":   int(row["metrics"][0]),
        }
        for row in c.get("data", [])
    ]

    return {
        "updated_at":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period_days": DAYS,
        "summary":     summary,
        "daily":       daily,
        "top_pages":   top_pages,
        "devices":     devices,
        "countries":   countries,
    }


if __name__ == "__main__":
    token = os.environ.get("YM_TOKEN")
    if not token:
        sys.exit("YM_TOKEN env var is not set")
    try:
        data = fetch(token)
    except HTTPError as e:
        sys.exit(f"Metrika API error {e.code}: {e.read().decode()[:400]}")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_FILE}")
    print(f"Summary: {data['summary']}")

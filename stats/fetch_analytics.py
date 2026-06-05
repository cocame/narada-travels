#!/usr/bin/env python3
"""Fetch Google Analytics 4 data and write to stats/data.json."""

import json
import os
import sys
from datetime import datetime, timezone

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account

PROPERTY_ID = "396354995"
DAYS = 30
OUT_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def build_client() -> BetaAnalyticsDataClient:
    key_json = os.environ.get("GA_SERVICE_ACCOUNT_KEY")
    if not key_json:
        sys.exit("GA_SERVICE_ACCOUNT_KEY env var is not set")
    info = json.loads(key_json)
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=creds)


def run(client: BetaAnalyticsDataClient) -> dict:
    period = f"{DAYS}daysAgo"
    dr = DateRange(start_date=period, end_date="today")

    # Summary metrics
    summary_resp = client.run_report(RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[dr],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
        ],
    ))
    row = summary_resp.rows[0].metric_values if summary_resp.rows else None
    summary = {
        "active_users":           int(row[0].value)             if row else 0,
        "sessions":               int(row[1].value)             if row else 0,
        "page_views":             int(row[2].value)             if row else 0,
        "avg_session_duration":   round(float(row[3].value), 1) if row else 0,
        "bounce_rate":            round(float(row[4].value), 4) if row else 0,
    }

    # Daily visitors (last 30 days)
    daily_resp = client.run_report(RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[dr],
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="activeUsers"), Metric(name="sessions")],
        order_bys=[{"dimension": {"dimension_name": "date"}}],
    ))
    daily = [
        {
            "date":     r.dimension_values[0].value,
            "users":    int(r.metric_values[0].value),
            "sessions": int(r.metric_values[1].value),
        }
        for r in daily_resp.rows
    ]

    # Top pages
    pages_resp = client.run_report(RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[dr],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews"), Metric(name="activeUsers")],
        order_bys=[{"metric": {"metric_name": "screenPageViews"}, "desc": True}],
        limit=10,
    ))
    top_pages = [
        {
            "path":  r.dimension_values[0].value,
            "views": int(r.metric_values[0].value),
            "users": int(r.metric_values[1].value),
        }
        for r in pages_resp.rows
    ]

    # Device breakdown
    device_resp = client.run_report(RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[dr],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name="sessions")],
        order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}],
    ))
    devices = [
        {
            "device":   r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value),
        }
        for r in device_resp.rows
    ]

    # Top countries
    country_resp = client.run_report(RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[dr],
        dimensions=[Dimension(name="country")],
        metrics=[Metric(name="activeUsers")],
        order_bys=[{"metric": {"metric_name": "activeUsers"}, "desc": True}],
        limit=10,
    ))
    countries = [
        {
            "country": r.dimension_values[0].value,
            "users":   int(r.metric_values[0].value),
        }
        for r in country_resp.rows
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
    client = build_client()
    data = run(client)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_FILE}")
    print(f"Summary: {data['summary']}")

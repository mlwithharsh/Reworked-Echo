from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local smoke test for the HELIX marketing agent.")
    parser.add_argument("--base-url", default=os.getenv("HELIX_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--api-token", default=os.getenv("HELIX_API_TOKEN", "dev-token"))
    parser.add_argument("--platforms", default="webhook,telegram,x,linkedin")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(
        {
            "x-api-token": args.api_token,
            "Content-Type": "application/json",
        }
    )

    platforms = [item.strip() for item in args.platforms.split(",") if item.strip()]
    now = datetime.now(timezone.utc)
    run_at = (now + timedelta(minutes=1)).isoformat()

    print(f"Using backend: {args.base_url}")
    health = get(session, args.base_url, "/api/marketing/platform-health")
    print("Platform health:")
    for item in health:
        print(f"  - {item['platform']}: configured={item['configured']} message={item['message']}")

    brand = post(
        session,
        args.base_url,
        "/api/marketing/brand-profiles",
        {
            "brand_name": "Helix Smoke Brand",
            "voice_style": "clear, direct, local-first",
            "preferred_vocabulary": ["efficient", "reliable", "local-first"],
            "banned_phrases": ["guaranteed virality"],
            "signature_patterns": ["one insight, one CTA"],
            "default_cta_style": "reply for rollout details",
            "audience_notes": "technical operators and startup founders",
            "positioning": "autonomous local marketing engine",
        },
    )
    print(f"Created brand profile: {brand['id']}")

    campaign = post(
        session,
        args.base_url,
        "/api/marketing/campaigns",
        {
            "name": "Smoke Test Campaign",
            "goal": "Promote Helix as a local-first autonomous marketing engine",
            "target_audience": "startup founders and AI operators",
            "brand_profile_id": brand["id"],
            "brand_voice": "bold and clear",
            "offer_summary": "One workspace for strategy, scheduling, and platform execution",
            "strategy_summary": "",
            "content_mix": {},
            "posting_frequency": "",
            "status": "draft",
        },
    )
    print(f"Created campaign: {campaign['id']}")

    strategy = post(session, args.base_url, f"/api/marketing/campaigns/{campaign['id']}/strategy", None)
    print(f"Strategy: {strategy['strategy_summary']}")

    generated = post(
        session,
        args.base_url,
        f"/api/marketing/campaigns/{campaign['id']}/generate",
        {
            "platforms": platforms,
            "experiment_labels": ["A", "B"],
            "desired_tone": "confident and useful",
            "cta_style": "ask for the rollout",
            "extra_context": ["smoke-test", "dry-run-only"],
        },
    )
    variants = generated["variants"]
    print(f"Generated variants: {len(variants)}")
    if not variants:
        raise RuntimeError("No variants generated")

    approved_variant_ids: list[str] = []
    for variant in variants[: len(platforms)]:
        result = post(
            session,
            args.base_url,
            f"/api/marketing/variants/{variant['id']}/approve",
            {"approved": True, "notes": "smoke approval"},
        )
        if result["safe_to_schedule"]:
            approved_variant_ids.append(result["variant"]["id"])
    print(f"Approved variants: {len(approved_variant_ids)}")
    if not approved_variant_ids:
        raise RuntimeError("No variants were approved for scheduling")

    schedule = post(
        session,
        args.base_url,
        f"/api/marketing/campaigns/{campaign['id']}/schedule",
        {
            "variant_ids": approved_variant_ids,
            "run_at": run_at,
            "timezone": "UTC",
        },
    )
    jobs = schedule["jobs"]
    print(f"Scheduled jobs: {len(jobs)}")
    if not jobs:
        raise RuntimeError("No jobs were scheduled")

    dry_run_log = post(
        session,
        args.base_url,
        f"/api/marketing/jobs/{jobs[0]['id']}/dispatch-now",
        {"execution_mode": "dry_run"},
    )
    print(f"Dry-run dispatch: platform={dry_run_log['platform']} status={dry_run_log['status']}")

    analytics = get(session, args.base_url, f"/api/marketing/analytics/campaigns/{campaign['id']}")
    print(f"Analytics events: {analytics['total_events']}")

    optimization = post(session, args.base_url, f"/api/marketing/optimize/campaigns/{campaign['id']}", None)
    print(
        "Optimization:",
        json.dumps(
            {
                "top_platform": optimization["top_platform"],
                "recommended_cta_style": optimization["recommended_cta_style"],
                "recommended_posting_window": optimization["recommended_posting_window"],
            }
        ),
    )

    print("Smoke test completed successfully.")
    return 0


def get(session: requests.Session, base_url: str, path: str):
    response = session.get(f"{base_url}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def post(session: requests.Session, base_url: str, path: str, payload):
    response = session.post(f"{base_url}{path}", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else str(exc)
        print(f"HTTP error: {body}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # pragma: no cover
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

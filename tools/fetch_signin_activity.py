#!/usr/bin/env python3
"""Fetch sign-in/security activity for a personal Microsoft Account (MSA).

This tool automates browser navigation to Microsoft Account security activity pages,
then scrapes currently visible activity entries after you complete login/MFA.

It is intended for defensive/self-audit use on accounts you own.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ACTIVITY_URL = "https://account.live.com/Activity?mkt=en-US"
SECURITY_URL = "https://account.microsoft.com/security?lang=en-US"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape visible sign-in/security activity for a personal Outlook.com "
            "(Microsoft Account / MSA) account via browser automation."
        )
    )
    parser.add_argument(
        "--output",
        default="msa_activity.json",
        help="Output path for extracted JSON records (default: msa_activity.json).",
    )
    parser.add_argument(
        "--html-output",
        default="msa_activity_page.html",
        help="Output path for captured page HTML (default: msa_activity_page.html).",
    )
    parser.add_argument(
        "--screenshot",
        default="msa_activity.png",
        help="Screenshot path for the loaded activity page (default: msa_activity.png).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of extracted entries to return (default: 50).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (not recommended for interactive login).",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=180000,
        help="Navigation timeout in milliseconds (default: 180000).",
    )
    return parser.parse_args()


def _extract_visible_activity(page: Any, limit: int) -> list[dict[str, str]]:
    # Heuristic extraction because MSA pages are dynamic and can change markup.
    raw = page.evaluate(
        """
        ({ limit }) => {
          const seen = new Set();
          const out = [];
          const keywords = [
            'sign in', 'sign-in', 'signed in', 'login', 'password',
            'security', 'mfa', 'two-step', 'verification', 'unusual'
          ];

          const candidates = Array.from(document.querySelectorAll('li, div[role="listitem"], tr, article, section'));

          for (const el of candidates) {
            const text = (el.innerText || '').replace(/\s+/g, ' ').trim();
            if (!text || text.length < 20 || text.length > 1200) continue;

            const lower = text.toLowerCase();
            if (!keywords.some(k => lower.includes(k))) continue;

            if (seen.has(text)) continue;
            seen.add(text);

            const lines = text.split(/\s*\n\s*|\s{2,}/).filter(Boolean);
            const title = lines[0] || text.slice(0, 120);

            out.push({
              title,
              text,
            });

            if (out.length >= limit) break;
          }

          return out;
        }
        """,
        {"limit": limit},
    )

    entries: list[dict[str, str]] = []
    date_regex = re.compile(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?",
        flags=re.IGNORECASE,
    )

    for item in raw:
        text = item.get("text", "").strip()
        title = item.get("title", "").strip()
        date_match = date_regex.search(text)
        entries.append(
            {
                "title": title,
                "observed_date": date_match.group(0) if date_match else "",
                "text": text,
            }
        )

    return entries


def collect_activity(args: argparse.Namespace) -> list[dict[str, str]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "Missing dependency: playwright. Install with `pip install -r requirements.txt` "
            "and run `python -m playwright install chromium`."
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(args.timeout_ms)

        print("Opening Microsoft security portal...")
        page.goto(SECURITY_URL, wait_until="domcontentloaded")

        print("\nPlease sign in to your personal Microsoft Account in the opened browser window.")
        print("Complete MFA/challenges if prompted, then navigate to your recent activity page.")
        print(f"If needed, open: {ACTIVITY_URL}")
        input("Press ENTER here after the activity list is visible in the browser... ")

        page.goto(ACTIVITY_URL, wait_until="networkidle")

        html = page.content()
        Path(args.html_output).write_text(html, encoding="utf-8")
        page.screenshot(path=args.screenshot, full_page=True)

        entries = _extract_visible_activity(page=page, limit=args.limit)

        context.close()
        browser.close()

    return entries


def summarize(entries: list[dict[str, str]]) -> None:
    if not entries:
        print("No activity entries were extracted from the page.")
        print("Tip: try re-running and ensure activity items are visible before pressing ENTER.")
        return

    print(f"Extracted {len(entries)} entries.")
    for item in entries[:10]:
        date = item.get("observed_date") or "unknown-date"
        title = item.get("title") or "untitled"
        print(f"- {date} | {title}")


def main() -> None:
    args = parse_args()

    try:
        entries = collect_activity(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(entries, file, indent=2)

    print(f"Saved extracted entries to: {args.output}")
    print(f"Saved raw page HTML to: {args.html_output}")
    print(f"Saved screenshot to: {args.screenshot}")
    summarize(entries)


if __name__ == "__main__":
    main()

# identity-threat-research
Research projects, tooling, and experiments focused on identity security, authentication telemetry, suspicious sign-in analysis, and defensive visibility gaps.

## Tool: Outlook.com (MSA) sign-in activity collector

`tools/fetch_signin_activity.py` targets **personal Microsoft Accounts (MSA)** such as `@outlook.com`, `@hotmail.com`, and `@live.com`.

It opens Microsoft Account security pages in a browser, lets you log in interactively, then extracts visible activity entries from your recent activity page.

### Important scope note

- This script is for **accounts you own/administer**.
- This is browser automation/scraping, not a documented public API for MSA activity logs.
- Page structure may change over time, so extraction is best-effort.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### Usage

```bash
python tools/fetch_signin_activity.py \
  --output msa_activity.json \
  --html-output msa_activity_page.html \
  --screenshot msa_activity.png \
  --limit 50
```

During execution:

1. A browser opens Microsoft security pages.
2. You log in manually and complete MFA.
3. Once the recent activity list is visible, press ENTER in the terminal.
4. The tool saves:
   - extracted entries (`msa_activity.json`)
   - raw HTML snapshot (`msa_activity_page.html`)
   - screenshot (`msa_activity.png`)

### Identity system name

Outlook.com personal accounts use **Microsoft Account (MSA)** identity.

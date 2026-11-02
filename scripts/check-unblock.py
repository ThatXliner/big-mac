#!/usr/bin/env python3
"""Verify anonymous denial, authenticated form and a real proxy request; no secret output."""
import argparse
import base64
from pathlib import Path
import urllib.error
import urllib.request

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--url", default="http://127.0.0.1:8093")
p.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[1] / "services/unblock/.env")
a = p.parse_args()
credentials = dict(line.split("=", 1) for line in a.env.read_text().splitlines() if line and not line.startswith("#"))["UNBLOCK_USERPASS"]
base = a.url.rstrip("/")
headers = {"User-Agent": "Mozilla/5.0 (compatible; BigMacHealthcheck/1.0)"}
try:
    urllib.request.urlopen(urllib.request.Request(base + "/", headers=headers), timeout=30)
except urllib.error.HTTPError as e:
    if e.code != 401:
        raise SystemExit(f"Expected anonymous 401, got {e.code}")
else:
    raise SystemExit("Anonymous request unexpectedly allowed")
auth = "Basic " + base64.b64encode(credentials.encode()).decode()
for path, expected in [("/", b"<form"), ("/https://example.com", b"Example Domain")]:
    request = urllib.request.Request(base + path, headers={**headers, "Authorization": auth})
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.status != 200 or expected not in response.read():
            raise SystemExit(f"Unexpected content from {path}")
print("PASS: anonymous 401, authenticated form 200, proxied example.com content 200")

#!/usr/bin/env python3
"""Login to Babbel API and page through /stories into stories.json."""

import json
import os
import sys
import urllib.request
from http.cookiejar import CookieJar

BASE = "https://babbel-api.zuidwest.cloud/api/v1"
PAGE = 100
UA = "Mozilla/5.0 babbel-analyse"

username = os.environ.get("BABBEL_USERNAME")
password = os.environ.get("BABBEL_PASSWORD")
if not username or not password:
    sys.exit("BABBEL_USERNAME and BABBEL_PASSWORD must be set in the environment")

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def login():
    body = json.dumps({"username": username, "password": password}).encode()
    req = urllib.request.Request(
        f"{BASE}/sessions",
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    with opener.open(req) as r:
        if r.status not in (200, 201):
            sys.exit(f"login failed: HTTP {r.status}")


def get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers={"User-Agent": UA})
    with opener.open(req) as r:
        return json.load(r)


login()

all_stories = []
offset = 0
while True:
    page = get(f"/stories?limit={PAGE}&offset={offset}&sort=created_at&trashed=with")
    data = page["data"]
    all_stories.extend(data)
    total = page["total"]
    sys.stderr.write(f"  fetched {len(all_stories)}/{total}\n")
    if len(all_stories) >= total or not data:
        break
    offset += len(data)

with open("stories.json", "w") as f:
    json.dump(all_stories, f, ensure_ascii=False)
print(f"saved {len(all_stories)} stories")

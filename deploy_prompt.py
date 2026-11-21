#!/usr/bin/env python3
"""Put speech-prompt.txt live in the Knabbel WordPress plugin.

Replaces the live prompt only when it is a version that was once committed here, so a
change made by hand in the plugin settings is never overwritten.
"""

import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

URL = "https://www.zuidwestupdate.nl/wp-json/knabbel/v1/speech-prompt"


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None  # a redirect fails the deploy, so the password never goes elsewhere


def call(method, body=None):
    auth = base64.b64encode(
        f"{os.environ['WP_PROMPT_USER']}:{os.environ['WP_PROMPT_PASSWORD']}".encode()
    )
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={"Authorization": f"Basic {auth.decode()}", "Content-Type": "application/json"},
    )
    # An HTTP error such as a 409 conflict raises and stops the deploy.
    with urllib.request.build_opener(NoRedirect).open(req, timeout=30) as r:
        return json.load(r)


def git(*args):  # bytes, decoded without newline changes: the hash must match the live bytes
    return subprocess.run(["git", *args], capture_output=True, check=True).stdout.decode()


commits = git("log", "--full-history", "--format=%H", "--", "speech-prompt.txt").split()
committed = {sha(git("show", f"{c}:speech-prompt.txt")) for c in commits}
new, live = Path("speech-prompt.txt").read_bytes().decode(), call("GET")
if live["sha256"] == sha(new):
    sys.exit(print("WordPress already has this prompt"))  # exit code 0
if live["sha256"] not in committed:
    sys.exit("The live prompt was changed by hand. See README: Monthly prompt check.")
print("live:", call("PUT", {"prompt": new, "expected_sha256": live["sha256"]})["sha256"])

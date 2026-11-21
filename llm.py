"""OpenAI Responses calls with a hard token budget, and the edit classifier.

The budget counts the tokens OpenAI reports back, so a run stops once it has used what it
may use. Calls that are already running finish, so a run can go over by at most WORKERS
calls.
"""

import concurrent.futures as cf
import json
import os
import threading
import time
import urllib.error
import urllib.request

OPENAI_URL = "https://api.openai.com/v1/responses"
UA = "babbel-analyse"
WORKERS = 6


class BudgetExceededError(RuntimeError):
    pass


class Budget:
    def __init__(self, max_input: int, max_output: int):
        self.max_input, self.max_output = max_input, max_output
        self.input = self.output = 0
        self.lock = threading.Lock()

    def check(self):
        with self.lock:
            if self.input >= self.max_input or self.output >= self.max_output:
                raise BudgetExceededError(
                    f"token budget used: {self.input} input, {self.output} output "
                    f"(limits {self.max_input} and {self.max_output})"
                )

    def add(self, usage):
        with self.lock:
            self.input += usage.get("input_tokens", 0)
            self.output += usage.get("output_tokens", 0)


budget = Budget(
    int(os.environ.get("MAX_INPUT_TOKENS", "2500000")),
    int(os.environ.get("MAX_OUTPUT_TOKENS", "1000000")),
)


def http_json(url, body=None, headers=None, timeout=180, tries=4):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, **(headers or {})}
    if data is not None:
        h["Content-Type"] = "application/json"
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, data=data, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            detail = e.read()[:300]
            # An empty balance is not worth retrying.
            if e.code in (429, 500, 502, 503, 504) and attempt < tries and b"credit" not in detail:
                time.sleep(2**attempt * 5)
                continue
            raise RuntimeError(f"{url}: HTTP {e.code} {detail!r}") from e
        except (urllib.error.URLError, TimeoutError):
            if attempt == tries:
                raise
            time.sleep(2**attempt * 5)
    raise RuntimeError("unreachable")


def openai(model, instructions, messages, max_tokens=1000, schema=None):
    """One Responses API call shaped like the WordPress OpenAI provider's request.

    Returns the text, the parsed JSON when a schema is given, or None when the model
    gave no complete answer.
    """
    budget.check()
    body = {
        "model": model,
        "input": [
            {
                "role": role,
                "content": [
                    {"type": "output_text" if role == "assistant" else "input_text", "text": text}
                ],
            }
            for role, text in messages
        ],
        "max_output_tokens": max_tokens,
    }
    if instructions:
        body["instructions"] = instructions
    if schema:
        body["text"] = {
            "format": {"type": "json_schema", "name": "result", "schema": schema, "strict": True}
        }
    key = os.environ["OPENAI_API_KEY"]
    r = http_json(OPENAI_URL, body, {"Authorization": f"Bearer {key}"})
    budget.add(r.get("usage") or {})
    if r.get("status") != "completed":
        return None
    text = "".join(
        c.get("text", "")
        for item in r.get("output", [])
        if item.get("type") == "message"
        for c in item.get("content", [])
        if c.get("type") == "output_text"
    ).strip()
    if not text:
        return None
    return json.loads(text) if schema else text


def pmap(fn, items):
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        return list(ex.map(fn, items))


# --- edit classifier ------------------------------------------------------------

# Bump when the instructions or kinds change, so old labels are redone on purpose.
CLASSIFIER_VERSION = 1

KINDS = {
    "fact": "the AI text said something the article does not support, and the editors fixed it",
    "missing": "the AI text left out something from the article that the editors added",
    "extra": "the editors added information that is not in the article",
    "timing": "the edit is about when the text airs (tense, 'vandaag' vs a weekday, ...)",
    "style": "a general writing rule the AI could follow next time",
    "taste": "a change without a clear general rule",
}

CLASSIFY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "kinds", "rules"],
                "properties": {
                    "id": {"type": "string"},
                    "kinds": {"type": "array", "items": {"type": "string", "enum": list(KINDS)}},
                    "rules": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}

CLASSIFY_INSTRUCTIONS = (
    "You help improve the system prompt that turns news articles into Dutch radio news "
    "texts. For each item you get the article the AI worked from, the AI text, the text the "
    "editors published and a word diff. Say what kinds of change the editors made. Use "
    "every kind that applies, and only those:\n"
    + "\n".join(f"- {k}: {v};" for k, v in KINDS.items())
    + "\nFor each style change, write the general rule as one short imperative sentence in "
    "Dutch that applies to any article (no names or details of this article). Leave rules "
    "empty when there is no style change."
)


def classify(model, cases, word_diff, batch_size=12):
    """Label the editors' changes per case; cases need id, article, ai and final.

    Returns (items, stopped). When the budget runs out, the batches that finished are
    still returned, so their cost is not lost, and stopped is True.
    """
    batches = [cases[i : i + batch_size] for i in range(0, len(cases), batch_size)]

    def run(batch):
        text = "\n\n".join(
            f"ITEM {c['id']}\nARTICLE: {c['article'][:20000]}\nAI: {c['ai']}\n"
            f"PUBLISHED: {c['final']}\nWORD DIFF: {word_diff(c['ai'], c['final'])}"
            for c in batch
        )
        try:
            r = openai(model, CLASSIFY_INSTRUCTIONS, [("user", text)], 16000, CLASSIFY_SCHEMA)
        except BudgetExceededError:
            return None
        wanted = {str(c["id"]) for c in batch}
        # Keep only items for stories that were sent in.
        return [i for i in (r["items"] if r else []) if i["id"] in wanted]

    results = pmap(run, batches)
    return [item for items in results if items for item in items], None in results

"""Run a small real demo lab job using an offline-provisioned organizer credential."""

import argparse
import json
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from uuid import uuid4

parser = argparse.ArgumentParser()
parser.add_argument("--target", default="http://localhost:8080")
parser.add_argument(
    "--credential-file", required=True, help="Private JSON file containing access_code"
)
parser.add_argument("--origin", help="Browser origin when it differs from the target API")
parser.add_argument("--output", help="Optional measured report JSON destination")
args = parser.parse_args()
jar = CookieJar()
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def request(path, method="GET", body=None, csrf=None):
    headers = {"Origin": args.origin or args.target}
    if method != "GET":
        headers["Content-Type"] = "application/json"
        headers["Idempotency-Key"] = str(uuid4())
    if csrf:
        headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(
        args.target + path,
        method=method,
        headers=headers,
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with client.open(req, timeout=5) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} during smoke verification") from None


health = request("/api/health/ready")
if not health["capabilities"]["lab"] or not health["capabilities"]["protected_writes"]:
    parser.error("Smoke workloads require an enabled isolated demo with healthy protection")
code = json.loads(Path(args.credential_file).read_text())["access_code"]
session = request("/api/v1/auth/session", "POST", {"access_code": code})
del code
if session["principal"]["role"] not in {"organizer", "admin"}:
    parser.error("Use an offline-provisioned organizer credential")
accepted = request(
    "/api/v1/admin/lab/runs",
    "POST",
    {
        "scenario": "normal",
        "human_actors": 2,
        "bot_actors": 2,
        "duration_seconds": 1,
        "target_rps": 12,
        "retries_per_actor": 0,
        "trials": 1,
        "drop_capacity": 2,
    },
    session["csrf_token"],
)
run_id = accepted["run_id"]
for _ in range(160):
    result = request(f"/api/v1/admin/lab/runs/{run_id}")
    if result["status"] in {"FAILED", "STOPPED", "COMPLETED"}:
        break
    time.sleep(0.25)
if result["status"] != "COMPLETED":
    raise SystemExit(f"Smoke run ended in {result['status']}; inspect retained private artifacts")
report = result["report"]
if (
    not report["integrity"]["audit_pass"]
    or report["performance"]["unexpected_5xx"]
    or report["performance"]["network_errors"]
):
    raise SystemExit("Smoke report did not pass integrity/transport checks")
if args.output:
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(f"Measured smoke passed: run {run_id}; no oversells or duplicate active owners.")

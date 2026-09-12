"""Read-only local web demo for the completed assignment artefacts.

The server deliberately has no model client and no write endpoint.  It turns
the frozen five-case result into a presentation a non-technical reviewer can
explore in a browser without spending API credit or changing review data.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import webbrowser
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.reference_pack import load_claims, load_sources
from src.service_catalogue import load_entries


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results" / "assignment_demo_v1.json"
ENQUIRIES = ROOT / "data" / "assignment_demo_v1.jsonl"
ASSETS = ROOT / "web_demo"

PURPOSES = {
    "ENQ-009": "Address change: compare a specific but partly unsupported answer with an evidence-grounded operational path.",
    "ENQ-021": "Medical claim: show how evidence constraints reduce invention but can make a reply too cautious.",
    "ENQ-030": "Formal complaint: test whether the model presents future actions as already completed.",
    "ENQ-024": "Refusal boundary: the reply must not guarantee claim approval when the customer asks for certainty.",
    "ENQ-012": "Prompt injection: malicious instructions inside an email must not alter the customer-service Agent's behaviour.",
}


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _evidence_index() -> dict[str, dict]:
    sources = load_sources()
    public = {}
    for claim in load_claims():
        source = sources[claim.source_id]
        public[claim.id] = {
            "kind": "public",
            "title": source.title,
            "publisher": source.publisher,
            "url": source.url,
            "locator": claim.locator,
            "guidance": claim.claim,
            "verified_on": source.verified_on,
        }
    service = {
        entry.id: {
            "kind": "synthetic",
            "title": entry.owner,
            "publisher": "Harbourview Life (fictional case study)",
            "guidance": entry.guidance,
        }
        for entry in load_entries()
    }
    return public | service


def build_demo_payload(result_path: Path = RESULT,
                       enquiries_path: Path = ENQUIRIES) -> dict:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    enquiries = {row["id"]: row for row in _jsonl(enquiries_path)}
    evidence = _evidence_index()

    cases = []
    for case in result["cases"]:
        record_id = case["record_id"]
        cases.append({
            **case,
            "purpose": PURPOSES.get(record_id, "Representative customer enquiry."),
            "enquiry": enquiries[record_id],
            "evidence": [
                {"id": evidence_id, **evidence[evidence_id]}
                for evidence_id in case["evidence_ids"]
            ],
        })

    return {
        "version": result["version"],
        "status": result["status"],
        "claim_scope": result["claim_scope"],
        "contract_failures": result["contract_failures"],
        "judge_usage": result["judge_usage"],
        "models": result["models"],
        "cases": cases,
        "notice": "Live input calls the configured models; frozen cases are read-only. Neither mode sends a customer reply.",
    }


def run_live_enquiry(subject: str, body: str) -> dict:
    """Run one evidence-backed enquiry and return a display-safe result.

    There is intentionally no trace store or queue writer here. The live demo
    displays the draft in memory and retains the production rule that nothing
    is sent to a customer.
    """
    from openai import OpenAI

    from src.contract import FailureCounters
    from src.generate import load_env
    from src.pipeline import PipelineConfig, StageConfig, run

    load_env(str(ROOT / ".env"))
    required = ("DASHSCOPE_API_KEY", "DASHSCOPE_BASE_URL",
                "TRIAGE_MODEL_A", "TRIAGE_MODEL_B")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing .env configuration: {', '.join(missing)}")

    client = OpenAI(api_key=os.environ["DASHSCOPE_API_KEY"],
                    base_url=os.environ["DASHSCOPE_BASE_URL"])
    config = PipelineConfig(
        triage=StageConfig(os.environ["TRIAGE_MODEL_A"]),
        draft=StageConfig(os.environ["TRIAGE_MODEL_B"]),
        evidence_backed=True,
    )
    counters = FailureCounters()
    item = run(client, config, "LIVE-DEMO", subject, body, counters)
    evidence = _evidence_index()
    return {
        "output": asdict(item),
        "evidence": [{"id": evidence_id, **evidence[evidence_id]}
                     for evidence_id in item.evidence_ids],
        "contract_failures": counters.as_dict(),
        "notice": "Draft for human review only. It was not queued or sent to a customer.",
    }


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


def make_handler(payload: dict, live_runner=run_live_enquiry):
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    class DemoHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = urlparse(self.path).path
            if path == "/api/demo":
                self._respond(encoded, "application/json; charset=utf-8")
                return
            asset = "index.html" if path in ("", "/") else path.removeprefix("/")
            target = (ASSETS / asset).resolve()
            if ASSETS.resolve() not in target.parents or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._respond(target.read_bytes(), CONTENT_TYPES.get(target.suffix,
                                                                  "application/octet-stream"))

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if urlparse(self.path).path != "/api/run":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 50_000:
                    raise ValueError("Request body is empty or too large")
                if "application/json" not in self.headers.get("Content-Type", ""):
                    raise ValueError("Request must use JSON")
                incoming = json.loads(self.rfile.read(length))
                subject = incoming.get("subject", "").strip()
                body = incoming.get("body", "").strip()
                if not subject or not body:
                    raise ValueError("Enter both an email subject and body")
                if len(subject) > 300 or len(body) > 20_000:
                    raise ValueError("Subject is limited to 300 characters and body to 20,000")
                result = live_runner(subject, body)
                self._json(result, HTTPStatus.OK)
            except (ValueError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # noqa: BLE001 - show a usable provider error
                self._json({"error": f"Agent run failed: {type(exc).__name__}: {exc}"},
                           HTTPStatus.BAD_GATEWAY)

        def _json(self, value: dict, status: HTTPStatus) -> None:
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _respond(self, body: bytes, content_type: str) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    return DemoHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open the read-only assignment web demo.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    payload = build_demo_payload()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(payload))
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"PACE assignment demo: {url}")
    print("Live input calls the models; no customer reply is sent. Press Ctrl+C to stop.")
    if not args.no_browser:
        threading.Timer(0.35, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import json
from urllib.error import HTTPError
from urllib.request import Request
from urllib.request import urlopen
from http.server import ThreadingHTTPServer
import threading

from web_demo import ASSETS, build_demo_payload, make_handler


def test_demo_payload_joins_frozen_cases_enquiries_and_evidence():
    payload = build_demo_payload()

    assert payload["status"] == "complete"
    assert len(payload["cases"]) == 5
    assert [case["record_id"] for case in payload["cases"]] == [
        "ENQ-009", "ENQ-021", "ENQ-030", "ENQ-024", "ENQ-012",
    ]
    assert all(case["enquiry"]["body"] for case in payload["cases"])
    assert all(case["evidence"] for case in payload["cases"])
    assert all(case["purpose"] for case in payload["cases"])
    assert {evidence["kind"] for case in payload["cases"]
            for evidence in case["evidence"]} == {"public", "synthetic"}


def test_demo_assets_exist():
    assert {path.name for path in ASSETS.iterdir()} >= {
        "index.html", "styles.css", "app.js",
    }


def test_demo_server_serves_page_and_json():
    server = ThreadingHTTPServer(("127.0.0.1", 0),
                                 make_handler(build_demo_payload()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base, timeout=2) as response:
            page = response.read().decode("utf-8")
            assert "PACE · Customer Operations AI" in page
            assert 'data-page="playground"' in page
        with urlopen(f"{base}/api/demo", timeout=2) as response:
            assert len(json.load(response)["cases"]) == 5
    finally:
        server.shutdown()
        server.server_close()


def test_live_endpoint_validates_input_and_returns_runner_output():
    calls = []

    def fake_runner(subject, body):
        calls.append((subject, body))
        return {"output": {"case_type": "CLAIM"}, "evidence": []}

    server = ThreadingHTTPServer(("127.0.0.1", 0),
                                 make_handler(build_demo_payload(), fake_runner))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/run"
        request = Request(url, method="POST",
                          headers={"Content-Type": "application/json"},
                          data=json.dumps({"subject": "Claim", "body": "Help"}).encode())
        with urlopen(request, timeout=2) as response:
            assert json.load(response)["output"]["case_type"] == "CLAIM"
        assert calls == [("Claim", "Help")]

        invalid = Request(url, method="POST",
                          headers={"Content-Type": "application/json"},
                          data=b'{"subject":"", "body":""}')
        try:
            urlopen(invalid, timeout=2)
            raise AssertionError("invalid request should fail")
        except HTTPError as error:
            assert error.code == 400
            assert "Enter both" in json.load(error)["error"]
    finally:
        server.shutdown()
        server.server_close()

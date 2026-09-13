import assert from "node:assert/strict";
import test from "node:test";
import handler, { parseContract, selectEvidence, confidenceFromVotes } from "./index.mjs";

test("validates the same strict output shapes as the Python pipeline", () => {
  assert.deepEqual(parseContract('{"case_type":"CLAIM","priority":"LOW"}', "triage"), { case_type: "CLAIM", priority: "LOW" });
  assert.throws(() => parseContract('{"case_type":"CLAIM","priority":"LOW","confidence":1}', "triage"), /exactly/);
  assert.throws(() => parseContract('{"case_type":"UNKNOWN","priority":"LOW"}', "triage"), /invalid/);
  assert.deepEqual(parseContract('```json\n{"summary":"A","draft_reply":"B"}\n```', "draft"), { summary: "A", draft_reply: "B" });
});

test("selects public and service evidence deterministically", async () => {
  const result = await selectEvidence("I need guidance for a hospital claim after surgery and want to make a complaint.");
  assert.deepEqual(result.selected.map(item => item.id), ["CLAIMS_01", "CLAIMS_02", "COMPLAINT_01", "COMPLAINT_02", "SVC_CLAIM_01", "SVC_COMPLAINT_01"]);
  assert.ok(result.context.some(line => line.includes("SYNTHETIC INTERNAL SERVICE CONTRACT")));
});

test("recognises natural duplicate-charge wording", async () => {
  const result = await selectEvidence("My bank account shows two charges for the renewal.");
  assert.deepEqual(result.selected.map(item => item.id), ["LEVY_01", "SVC_BILLING_01"]);
});

test("public live endpoint fails closed without an access code", async () => {
  const previous = process.env.DEMO_ACCESS_CODE; delete process.env.DEMO_ACCESS_CODE;
  try {
    const response = await handler.fetch(new Request("https://demo.example/api/index?route=run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ subject: "x", body: "y" }) }));
    assert.equal(response.status, 503);
  } finally { if (previous !== undefined) process.env.DEMO_ACCESS_CODE = previous; }
});

test("fallback confidence supports the label returned to the reviewer", () => {
  assert.equal(confidenceFromVotes(["OTHER", "OTHER", "OTHER"], "CLAIM").value, 0);
  assert.equal(confidenceFromVotes(["CLAIM", "OTHER", "CLAIM"], "CLAIM").value, 2 / 3);
  assert.throws(() => confidenceFromVotes([], "CLAIM"), /no valid votes/);
});

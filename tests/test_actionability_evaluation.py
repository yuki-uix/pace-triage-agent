import json

from evals.actionability_evaluation import prepare, score, status


def drafts(path):
    path.write_text("\n".join([
        json.dumps({
            "record_id": "ENQ-001",
            "enquiry": "Subject: Address\n\nHow do I update it?",
            "summary": "Customer asks how to update an address.",
            "draft_reply": "We need to verify your policy before advising.",
        }),
        json.dumps({
            "record_id": "ENQ-002",
            "enquiry": "Subject: Claim\n\nWhat should I provide?",
            "summary": "Customer asks what a claim requires.",
            "draft_reply": "We will look into it.",
        }),
    ]) + "\n", encoding="utf-8")


def test_prepare_is_free_and_creates_only_blind_human_material(tmp_path):
    source = tmp_path / "drafts.jsonl"
    drafts(source)
    out = tmp_path / "out"

    assert prepare(source, out) == 0
    labels = [json.loads(line) for line in
              (out / "actionability_labels.jsonl").read_text().splitlines()]
    assert [row["human"] for row in labels] == [None, None]
    assert not (out / "actionability_result.json").exists()
    worksheet = (out / "actionability_worksheet.md").read_text()
    assert "judge output" in worksheet
    assert "How do I update it?" in worksheet


def test_status_and_score_keep_judge_disabled_until_labels_complete(
        tmp_path, capsys):
    source = tmp_path / "drafts.jsonl"
    drafts(source)
    out = tmp_path / "out"
    prepare(source, out)

    assert status(out) == 1
    assert score(source, out) == 1
    output = capsys.readouterr().out
    assert "judge remains disabled" in output
    assert "judge calls remain disabled" in output


def test_prepare_refuses_to_overwrite_started_human_labels(tmp_path):
    source = tmp_path / "drafts.jsonl"
    drafts(source)
    out = tmp_path / "out"
    prepare(source, out)
    labels = out / "actionability_labels.jsonl"
    rows = [json.loads(line) for line in labels.read_text().splitlines()]
    rows[0]["human"] = 7
    labels.write_text("".join(json.dumps(row) + "\n" for row in rows))

    assert prepare(source, out) == 2
    assert json.loads(labels.read_text().splitlines()[0])["human"] == 7

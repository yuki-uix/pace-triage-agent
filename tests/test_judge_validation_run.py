import hashlib

from evals.judge_validation import input_sha256, matrix


def test_confusion_matrix_rows_are_expected_and_columns_are_judge_bands():
    result = matrix([0, 0, 1, 2, 3], [0, 1, 1, 3, 3])
    assert result == [
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
    ]


def test_input_hashes_make_paid_runs_traceable(tmp_path):
    source = tmp_path / "input.jsonl"
    source.write_bytes(b"frozen input\n")

    assert input_sha256((source,)) == {
        source.as_posix(): hashlib.sha256(b"frozen input\n").hexdigest()
    }

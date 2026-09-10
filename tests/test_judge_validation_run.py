from evals.judge_validation import matrix


def test_confusion_matrix_rows_are_expected_and_columns_are_judge_bands():
    result = matrix([0, 0, 1, 2, 3], [0, 1, 1, 3, 3])
    assert result == [
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
    ]

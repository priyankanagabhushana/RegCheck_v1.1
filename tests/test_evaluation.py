from evaluation.evaluator import EvalReport


def test_summary_text_discloses_evaluation_limitations():
    report = EvalReport(
        dataset_name="demo",
        evaluation_mode="synthetic_contracts",
        limitations=["This is not an end-to-end extraction benchmark."],
    )

    assert "Mode: synthetic_contracts" in report.summary_text
    assert "Limitations:" in report.summary_text
    assert "not an end-to-end extraction benchmark" in report.summary_text

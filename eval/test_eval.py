import pytest
from eval.eval_cases import EVAL_CASES
from eval.eval_suite import run_single_eval

@pytest.mark.parametrize("case", EVAL_CASES, ids=[c["id"] for c in EVAL_CASES])
def test_evaluation_case(case):
    passed, logs, result = run_single_eval(case)
    log_str = "\n".join(logs)
    assert passed, f"Evaluation case {case['id']} failed:\n{log_str}"

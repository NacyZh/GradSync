import pytest

from apps.projects.decision_risk_services import derive_risk_severity


@pytest.mark.parametrize(
    ("likelihood", "impact", "expected"),
    [
        ("low", "low", "low"),
        ("low", "medium", "low"),
        ("low", "high", "medium"),
        ("medium", "low", "low"),
        ("medium", "medium", "medium"),
        ("medium", "high", "high"),
        ("high", "low", "medium"),
        ("high", "medium", "high"),
        ("high", "high", "high"),
    ],
)
def test_fixed_risk_matrix(likelihood, impact, expected):
    assert derive_risk_severity(likelihood, impact) == expected

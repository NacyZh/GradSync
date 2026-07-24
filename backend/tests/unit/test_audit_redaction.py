from apps.audit.services import redact_snapshot


def test_redaction_removes_nested_credentials_and_bounds_values():
    value = redact_snapshot(
        {
            "status": "ok",
            "password": "never-store",
            "nested": {
                "authorization": "Bearer secret",
                "code": "123456",
                "reason": "x" * 2000,
            },
        },
        allowed_keys={"status", "nested"},
    )

    assert value["status"] == "ok"
    assert "password" not in value
    assert "authorization" not in value["nested"]
    assert "code" not in value["nested"]
    assert len(value["nested"]["reason"]) <= 1000

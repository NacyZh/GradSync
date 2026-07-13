from pathlib import Path


def test_resource_inventory_migrations_are_additive_and_non_destructive():
    root = Path(__file__).parents[2] / "apps"
    resource_migration = (
        root / "resources/migrations/0003_shared_resource_inventory.py"
    ).read_text()
    audit_migration = (root / "audit/migrations/0004_target_snapshot.py").read_text()

    for field in ("total_quantity", "confirmation_policy", "version"):
        assert field in resource_migration
    assert "target_snapshot" in audit_migration
    assert "DeleteModel" not in resource_migration + audit_migration
    assert "RemoveField" not in resource_migration + audit_migration


def test_resource_use_refinement_migration_adds_origin_completion_and_review_index():
    root = Path(__file__).parents[2] / "apps"
    migration = (
        root / "resources/migrations/0005_booking_origin_completion_indexes.py"
    ).read_text()

    for field in ("origin", "completed_at", "booking_review_queue_idx"):
        assert field in migration
    assert "legacy_booking" in migration
    assert "DeleteModel" not in migration
    assert "RemoveField" not in migration

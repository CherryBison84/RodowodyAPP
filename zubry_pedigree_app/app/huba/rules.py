"""Mapowanie reguł z JSON / UI na obiekty domenowe."""

from __future__ import annotations

from typing import Any

from app.data.auto_fix import AutoFixOptions
from app.huba.models import ProcessingRules


def auto_fix_from_mapping(raw: dict[str, Any] | None) -> AutoFixOptions:
    """Buduje ``AutoFixOptions`` z sekcji ``rules.auto_fix`` w JSON projektu."""
    if not raw:
        return AutoFixOptions()
    return AutoFixOptions(
        dedupe_ids=bool(raw.get("dedupe_ids", True)),
        drop_rows_without_id=bool(raw.get("drop_rows_without_id", False)),
        clear_birth_year_out_of_range=bool(raw.get("clear_birth_year_out_of_range", True)),
        clear_death_date_on_conflict=bool(raw.get("clear_death_date_on_conflict", True)),
        remove_self_parent=bool(raw.get("remove_self_parent", True)),
        cut_missing_parent_record=bool(raw.get("cut_missing_parent_record", True)),
        cut_parent_sex_collision=bool(raw.get("cut_parent_sex_collision", True)),
        cut_parent_too_young=bool(raw.get("cut_parent_too_young", True)),
        cut_parent_too_old=bool(raw.get("cut_parent_too_old", False)),
    )


def processing_rules_from_mapping(raw: dict[str, Any] | None) -> ProcessingRules:
    """Buduje ``ProcessingRules`` z sekcji ``rules`` w JSON projektu."""
    if not raw:
        return ProcessingRules()
    auto_raw = raw.get("auto_fix")
    auto = auto_fix_from_mapping(auto_raw if isinstance(auto_raw, dict) else None)
    return ProcessingRules(
        apply_auto_fix=bool(raw.get("apply_auto_fix", True)),
        auto_fix=auto,
        exclude_test_records=bool(raw.get("exclude_test_records", True)),
        test_record_id=str(raw.get("test_record_id", "99999")).strip() or "99999",
    )

"""Regresje integralności potoku: rekord techniczny, izolacja wyników i raport artefaktów."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

import pandas as pd

from app.huba.engine import run_project
from app.huba.models import HubProjectConfig, InputSource, ProcessingRules


def _frame(*ids: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": list(ids),
            "name": [f"Osobnik {value}" for value in ids],
            "sex": ["M"] * len(ids),
            "father_id": [None] * len(ids),
            "mother_id": [None] * len(ids),
        }
    )


class HubaIntegrityTests(unittest.TestCase):
    def test_test_record_option_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = InputSource(name="baza")
            keep = HubProjectConfig(
                project_name="keep",
                output_dir=root,
                inputs=(source,),
                rules=ProcessingRules(apply_auto_fix=False, exclude_test_records=False),
            )
            drop = HubProjectConfig(
                project_name="drop",
                output_dir=root,
                inputs=(source,),
                rules=ProcessingRules(apply_auto_fix=False, exclude_test_records=True),
            )

            kept = run_project(keep, upload_dataframes={"baza": _frame("1", "99999")})
            dropped = run_project(drop, upload_dataframes={"baza": _frame("1", "99999")})

            self.assertEqual(kept.datasets[0].rows_out, 2)
            self.assertEqual(dropped.datasets[0].rows_out, 1)
            cleaned = pd.read_excel(dropped.datasets[0].run_dir / "cleaned.xlsx")
            self.assertNotIn("99999", set(cleaned["id"].astype(str)))

    def test_reused_project_name_does_not_keep_stale_datasets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_project = HubProjectConfig(
                project_name="same_name",
                output_dir=root,
                inputs=(InputSource(name="stara_baza"),),
                rules=ProcessingRules(apply_auto_fix=False, exclude_test_records=False),
            )
            new_project = HubProjectConfig(
                project_name="same_name",
                output_dir=root,
                inputs=(InputSource(name="nowa_baza"),),
                rules=ProcessingRules(apply_auto_fix=False, exclude_test_records=False),
            )

            first = run_project(old_project, upload_dataframes={"stara_baza": _frame("1")})
            stale_dir = first.project_dir / "datasets" / "stara_baza"
            self.assertTrue(stale_dir.is_dir())
            second = run_project(new_project, upload_dataframes={"nowa_baza": _frame("2")})

            self.assertFalse(stale_dir.exists())
            self.assertTrue((second.project_dir / "datasets" / "nowa_baza").is_dir())

    def test_html_and_manifest_list_only_existing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = HubProjectConfig(
                project_name="artifacts",
                output_dir=Path(tmp),
                inputs=(InputSource(name="baza"),),
                rules=ProcessingRules(apply_auto_fix=False, exclude_test_records=False),
            )
            result = run_project(project, upload_dataframes={"baza": _frame("1")})

            html = result.final_report_html_path.read_text(encoding="utf-8")
            manifest_text = result.manifest_path.read_text(encoding="utf-8")
            manifest = json.loads(manifest_text)
            self.assertNotIn("auto_fix_log.txt", html)
            self.assertNotIn("auto_fix_log.txt", manifest_text)
            self.assertIn("cleaned.xlsx", html)
            self.assertTrue((result.datasets[0].run_dir / "cleaned.xlsx").is_file())
            self.assertEqual(manifest["schema_version"], 2)
            self.assertIn("generated_at", manifest)
            self.assertIn("application_version", manifest)
            self.assertIn("configuration", manifest)
            self.assertEqual(len(manifest["datasets"][0]["input"]["sha256"]), 64)

    def test_comparison_contains_validation_before_and_after(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = HubProjectConfig(
                project_name="comparison",
                output_dir=Path(tmp),
                inputs=(InputSource(name="baza"),),
                rules=ProcessingRules(apply_auto_fix=True, exclude_test_records=False),
            )
            duplicated = pd.concat([_frame("1"), _frame("1")], ignore_index=True)
            result = run_project(project, upload_dataframes={"baza": duplicated})
            comparison = pd.read_csv(result.comparison_path)

            self.assertIn("validation_errors_before", comparison.columns)
            self.assertIn("validation_errors_after", comparison.columns)
            self.assertGreater(comparison.loc[0, "validation_errors_before"], comparison.loc[0, "validation_errors_after"])


if __name__ == "__main__":
    unittest.main()

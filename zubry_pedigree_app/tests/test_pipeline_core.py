"""Testy kluczowej logiki DataCleaner poza warstwą interfejsu."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.cli import main as cli_main
from app.data.auto_fix import AutoFixOptions, apply_auto_fixes
from app.data.manual_edit import apply_record_patches
from app.data.validator import validate_loaded_dataset
from app.huba.config_io import load_project_config
from app.huba.modules.merge import merge_standardized_frames
from app.pedigree.ancestor_pedigree import build_people_map


def _problem_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": ["1", "1", None, "2"],
            "name": ["A", "A duplikat", "Bez ID", "B"],
            "sex": ["U", "M", "F", "F"],
            "birth_year": [2000, 2000, 2001, 2020],
            "father_id": ["1", None, None, "404"],
            "mother_id": [None, None, None, None],
        }
    )


class PipelineCoreTests(unittest.TestCase):
    def test_validator_reports_core_data_problems(self) -> None:
        df = _problem_frame()
        report = validate_loaded_dataset(df, build_people_map(df), current_year=2026)
        titles = {issue.title for issue in report.issues}
        types = {row.problem_type for row in report.export_rows}

        self.assertIn("Duplikaty ID", titles)
        self.assertIn("Self-parent (osobnik ma samego siebie jako rodzica)", titles)
        self.assertIn("Niepoprawna płeć (sex)", types)
        self.assertIn("Pusty lub niepoprawny identyfikator", types)
        self.assertIn("Brak rekordu ojca w bazie", types)

    def test_auto_fix_and_manual_edit_are_deterministic(self) -> None:
        df = _problem_frame()
        fixed, log = apply_auto_fixes(
            df,
            AutoFixOptions(
                dedupe_ids=True,
                drop_rows_without_id=True,
                remove_self_parent=True,
                cut_missing_parent_record=True,
            ),
            year_max=2028,
        )
        self.assertEqual(len(fixed), 2)
        self.assertEqual(fixed["id"].duplicated().sum(), 0)
        self.assertTrue(pd.isna(fixed.loc[fixed["id"] == "1", "father_id"]).all())
        self.assertTrue(any("duplikat" in line.lower() for line in log))

        edited, messages = apply_record_patches(fixed, "2", {"sex": "M", "birth_year": "2021"})
        row = edited.loc[edited["id"] == "2"].iloc[0]
        self.assertEqual(row["sex"], "M")
        self.assertEqual(row["birth_year"], 2021)
        self.assertEqual(len(messages), 2)

    def test_merge_duplicate_policies(self) -> None:
        left = pd.DataFrame({"id": ["1", "2"], "name": ["A", "B"]})
        right = pd.DataFrame({"id": ["2", "3"], "name": ["B2", "C"]})

        first = merge_standardized_frames([("left", left), ("right", right)], on_duplicate_id="keep_first")
        last = merge_standardized_frames([("left", left), ("right", right)], on_duplicate_id="keep_last")
        all_rows = merge_standardized_frames([("left", left), ("right", right)], on_duplicate_id="keep_all")

        self.assertEqual(len(first.df_std), 3)
        self.assertEqual(first.df_std.loc[first.df_std["id"] == "2", "name"].iloc[0], "B")
        self.assertEqual(last.df_std.loc[last.df_std["id"] == "2", "name"].iloc[0], "B2")
        self.assertEqual(len(all_rows.df_std), 4)

    def test_json_config_and_cli_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.csv"
            output = root / "out"
            config = root / "project.json"
            pd.DataFrame(
                {
                    "id": ["1"],
                    "name": ["A"],
                    "sex": ["M"],
                    "father_id": [None],
                    "mother_id": [None],
                }
            ).to_csv(source, index=False)
            config.write_text(
                json.dumps(
                    {
                        "project_name": "json_run",
                        "output_dir": str(output),
                        "inputs": [{"name": "input", "path": str(source)}],
                        "rules": {"apply_auto_fix": False, "exclude_test_records": False},
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_project_config(config)
            self.assertEqual(loaded.project_name, "json_run")
            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = cli_main(["run", "--config", str(config)])
            self.assertEqual(exit_code, 0)
            self.assertTrue((output / "json_run" / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()

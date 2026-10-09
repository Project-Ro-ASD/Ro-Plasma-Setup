"""Policy/negative checks; these do not certify QML loading or rendering."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("harness", Path(__file__).parents[1] / "tools/harness.py")
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.pages = [{"id": p["id"], "weight": p["weight"]} for p in harness.LOCK["installed_modules"]]

    def test_lock_matches_immutable_pr01_baseline(self):
        harness.verify_baseline()

    def test_both_future_slots_preserve_first_and_last(self):
        ordered = harness.contracts()
        self.assertEqual(ordered[0]["id"], harness.LANGUAGE)
        self.assertEqual(ordered[1]["weight"], 1)
        self.assertEqual(ordered[-2]["weight"], 190)
        self.assertEqual(ordered[-1]["id"], harness.FINISHED)

    def test_invalid_weight_types_and_range(self):
        for value in (None, True, False, "1", 1.0, 1.5, -1, 201):
            with self.subTest(value=value), self.assertRaisesRegex(harness.ContractError, "integer"):
                harness.validate_order(self.pages + [{"id": harness.SAMPLE_ID, "weight": value}])

    def test_duplicate_weight(self):
        with self.assertRaisesRegex(harness.ContractError, "duplicate weight"):
            harness.validate_order(self.pages + [{"id": harness.SAMPLE_ID, "weight": 5}])

    def test_duplicate_id(self):
        with self.assertRaisesRegex(harness.ContractError, "duplicate plugin ID"):
            harness.validate_order(self.pages + [self.pages[0]])

    def test_reserved_ro_slots(self):
        with self.assertRaisesRegex(harness.ContractError, "reserved Ro"):
            harness.validate_order(self.pages + [{"id": harness.SAMPLE_ID, "weight": 2}])

    def test_missing_language_or_final(self):
        for ident in (harness.LANGUAGE, harness.FINISHED):
            with self.subTest(ident=ident), self.assertRaises(harness.ContractError):
                harness.validate_order([p for p in self.pages if p["id"] != ident])

    def test_no_page_before_language_or_after_finished(self):
        for index, value in ((0, 2), (-1, 189)):
            pages = copy.deepcopy(self.pages)
            pages[index]["weight"] = value
            with self.assertRaises(harness.ContractError):
                harness.validate_order(pages)

    def test_metadata_contract_and_required_mainscript(self):
        original = json.loads((harness.SAMPLE / "metadata.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / harness.SAMPLE_ID
            (package / "contents/ui").mkdir(parents=True)
            (package / "metadata.json").write_text(json.dumps(original))
            with self.assertRaisesRegex(harness.ContractError, "missing required mainscript"):
                harness.metadata(package)
            (package / "contents/ui/main.qml").touch()
            for field in ("KPackageStructure", "X-KDE-ParentApp"):
                data = copy.deepcopy(original)
                data[field] = "wrong"
                (package / "metadata.json").write_text(json.dumps(data))
                with self.subTest(field=field), self.assertRaises(harness.ContractError):
                    harness.metadata(package)

    def test_staging_refuses_unmarked_directory_and_existing_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            with self.assertRaisesRegex(harness.ContractError, "outside harness sandbox"):
                harness.stage(sandbox, 1)
            (sandbox / ".ro-harness-sandbox").touch()
            destination = harness.stage(sandbox, 1)
            digest = harness.snapshot(destination)
            with self.assertRaisesRegex(harness.ContractError, "refusing replacement"):
                harness.stage(sandbox, 190)
            self.assertEqual(harness.snapshot(destination), digest)

    def test_snapshot_detects_persistent_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            before = harness.snapshot(path)
            (path / "unexpected-state").write_text("changed")
            self.assertNotEqual(before, harness.snapshot(path))

    def test_source_drift_fails_before_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            entry = next(iter(harness.LOCK["source_files"]))
            (path / entry).parent.mkdir(parents=True)
            (path / entry).write_text("modified")
            with self.assertRaisesRegex(harness.ContractError, "source drift"):
                harness.verify_source(path)

    def test_root_runtime_is_rejected_before_any_command(self):
        with patch.object(harness.os, "geteuid", return_value=0), patch.object(harness, "command") as call:
            with self.assertRaisesRegex(harness.ContractError, "unprivileged"):
                harness.run(Path("/usr/libexec/plasma-setup"), Path("/tmp"))
            call.assert_not_called()

    def test_upstream_wizard_cannot_be_selected_as_runner(self):
        with patch.object(harness.os, "geteuid", return_value=1000), \
                patch.dict(harness.os.environ, {"RO_HARNESS_DISPOSABLE_VM": "1"}), \
                patch.object(harness, "command") as call:
            with self.assertRaisesRegex(harness.ContractError, "separately built ro-plasma-probe"):
                harness.run(Path("/usr/libexec/plasma-setup"), Path("/tmp"))
            call.assert_not_called()


if __name__ == "__main__":
    unittest.main()

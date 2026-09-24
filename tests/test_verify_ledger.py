"""Tests for the reference verifier (spec/LEDGER.md, Verdict and coverage)."""
import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "tools" / "verify_ledger.py"
spec = importlib.util.spec_from_file_location("verify_ledger", VERIFIER)
verify_ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_ledger)

GENESIS = "0" * 64


def chain(n=3):
    """A synthetic, correctly hashed chain of n capture signals."""
    rows, prev = [], GENESIS
    for i in range(n):
        row = {"id": f"mem_row{i}", "op": "capture", "ts": f"2026-09-24T00:00:0{i}Z",
               "actor": "human:test", "workspace": "test", "hash": "", "prevHash": prev,
               "payload": {"body": f"row {i}", "kind": "event"}}
        row["hash"] = verify_ledger.content_hash(row)
        prev = row["hash"]
        rows.append(row)
    return rows


class VerdictTests(unittest.TestCase):
    def verify(self, rows, profile="v2.2"):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "ledger.jsonl"
            path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
            return verify_ledger.verify(str(path), profile)

    def test_intact_chain_is_verified(self):
        result = self.verify(chain())
        self.assertEqual(result["verdict"], "verified")
        self.assertEqual(result["coverage"]["canonical_rows"], 3)

    def test_parents_rewired_to_genesis_are_incomplete_not_verified(self):
        rows = chain()
        for row in rows:
            row["prevHash"] = GENESIS
        result = self.verify(rows)
        self.assertEqual(result["verdict"], "incomplete")
        self.assertFalse(result["ok"])
        self.assertEqual(result["coverage"]["detached_rows"], 2)
        self.assertEqual(self.verify(rows, "strict")["verdict"], "failed")

    def test_branch_is_permitted_under_v22_and_fails_under_strict(self):
        rows = chain()
        rows[2]["prevHash"] = rows[0]["hash"]
        self.assertEqual(self.verify(rows)["verdict"], "verified")
        self.assertEqual(self.verify(rows)["coverage"]["fork_rows"], 1)
        self.assertEqual(self.verify(rows, "strict")["verdict"], "failed")

    def test_changed_content_fails(self):
        rows = chain()
        rows[1] = copy.deepcopy(rows[1])
        rows[1]["payload"]["body"] = "row X"
        self.assertEqual(self.verify(rows)["verdict"], "failed")

    def test_sample_ledger_is_verified(self):
        result = verify_ledger.verify(str(ROOT / "examples" / "sample-ledger.jsonl"))
        self.assertEqual(result["verdict"], "verified")


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(VERIFIER), *args], capture_output=True, text=True)

    def test_a_path_is_required(self):
        self.assertEqual(self.run_cli().returncode, 64)

    def test_exit_codes_follow_the_verdict(self):
        rows = chain()
        for row in rows:
            row["prevHash"] = GENESIS
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "ledger.jsonl"
            path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
            self.assertEqual(self.run_cli("--json", str(path)).returncode, 2)
            self.assertEqual(self.run_cli("--json", "--profile", "strict", str(path)).returncode, 1)
        self.assertEqual(self.run_cli(str(ROOT / "examples" / "sample-ledger.jsonl")).returncode, 0)


if __name__ == "__main__":
    unittest.main()

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cortensor_ops_agent import (
    NodeAuditSummary,
    inspect_cortensor_node,
    run_cortensor_audit_workflow,
    verify_poi_receipt,
)


class CortensorOpsTests(unittest.TestCase):
    def test_inspect_cortensor_node_payload(self) -> None:
        raw = inspect_cortensor_node("miner-test-01")
        data = json.loads(raw)
        self.assertEqual(data["node_id"], "miner-test-01")
        self.assertEqual(data["status"], "ONLINE_VERIFIED")
        self.assertIn("poi_commit_hash", data)

    def test_verify_poi_receipt(self) -> None:
        raw = verify_poi_receipt(session_id=7)
        data = json.loads(raw)
        self.assertEqual(data["session_id"], 7)
        self.assertTrue(data["verified"])

    def test_node_audit_summary_schema(self) -> None:
        model = NodeAuditSummary(
            node_id="miner-sol-gpu-042",
            health_status="HEALTHY",
            poi_verified=True,
            vram_utilization_pct=68.4,
            summary="Passed all checks",
        )
        self.assertEqual(model.health_status, "HEALTHY")

    def test_end_to_end_openminion_workflow(self) -> None:
        code = run_cortensor_audit_workflow(use_local_server=True)
        self.assertEqual(code, 0)
        receipt = Path(__file__).resolve().parent.parent / "audit_logs" / "miner-sol-gpu-042_receipt.json"
        self.assertTrue(receipt.exists())


if __name__ == "__main__":
    unittest.main()

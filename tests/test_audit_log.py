import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_log import append_event, append_pdf_processed_event, read_events, verify_log_chain


class TestAuditLog(unittest.TestCase):
    def test_first_event_has_null_prev_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "audit.jsonl"

            event = append_event(
                log_path,
                {
                    "event": "pdf_processed",
                    "source_sha256": "source-a",
                    "output_sha256": "output-a",
                    "timestamp": "2026-06-29T00:00:00+00:00",
                },
            )

        self.assertIsNone(event["prev_hash"])
        self.assertTrue(event["event_hash"])

    def test_second_event_links_to_previous_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "audit.jsonl"

            first = append_event(
                log_path,
                {
                    "event": "pdf_processed",
                    "source_sha256": "source-a",
                    "output_sha256": "output-a",
                    "timestamp": "2026-06-29T00:00:00+00:00",
                },
            )
            second = append_event(
                log_path,
                {
                    "event": "pdf_processed",
                    "source_sha256": "source-b",
                    "output_sha256": "output-b",
                    "timestamp": "2026-06-29T00:00:01+00:00",
                },
            )

        self.assertEqual(second["prev_hash"], first["event_hash"])

    def test_tampering_breaks_chain_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "audit.jsonl"
            append_event(
                log_path,
                {
                    "event": "pdf_processed",
                    "source_sha256": "source-a",
                    "output_sha256": "output-a",
                    "timestamp": "2026-06-29T00:00:00+00:00",
                },
            )
            append_event(
                log_path,
                {
                    "event": "pdf_processed",
                    "source_sha256": "source-b",
                    "output_sha256": "output-b",
                    "timestamp": "2026-06-29T00:00:01+00:00",
                },
            )
            events = read_events(log_path)
            events[0]["source_sha256"] = "tampered"
            log_path.write_text(
                "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
                encoding="utf-8",
            )

            errors = verify_log_chain(log_path)

        self.assertTrue(any("event_hash mismatch at line 1" in error for error in errors))

    def test_append_pdf_processed_event_records_output_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "audit.jsonl"
            output_path = Path(tmp) / "oficio.json"
            output_path.write_text('{"ok": true}', encoding="utf-8")

            event = append_pdf_processed_event(
                log_path,
                source_sha256="source-a",
                output_path=output_path,
                timestamp="2026-06-29T00:00:00+00:00",
            )

        self.assertEqual(event["event"], "pdf_processed")
        self.assertEqual(event["source_sha256"], "source-a")
        self.assertEqual(
            event["output_sha256"],
            hashlib.sha256(b'{"ok": true}').hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()

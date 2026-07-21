import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "plugins/codex-share-plugin/scripts/share_session.py"
SPEC = importlib.util.spec_from_file_location("share_session", SCRIPT)
assert SPEC and SPEC.loader
share_session = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(share_session)


class ShareSessionTest(unittest.TestCase):
    def test_defaults_to_codex_namespace(self) -> None:
        original_argv = share_session.sys.argv
        share_session.sys.argv = ["share_session.py"]
        try:
            args = share_session.parse_args()
        finally:
            share_session.sys.argv = original_argv

        self.assertEqual(args.base_path, "sessions/codex")

    def test_converts_messages_and_tool_calls_without_internal_instructions(self) -> None:
        entries = [
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "developer",
                    "content": [{"type": "input_text", "text": "secret instructions"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Fix the bug"}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "I found it."}],
                },
            },
            {
                "type": "response_item",
                "payload": {"type": "function_call", "name": "shell", "arguments": "{\"cmd\": \"pytest\"}"},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session.jsonl"
            session.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")

            markdown = share_session.convert_session(session, "Bug fix")

        self.assertIn("# Bug fix", markdown)
        self.assertIn("## User\n\nFix the bug", markdown)
        self.assertIn("## Codex\n\nI found it.", markdown)
        self.assertIn("<summary><code>shell</code></summary>", markdown)
        self.assertNotIn("secret instructions", markdown)

    def test_prefers_session_for_current_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sessions = root / "sessions/2026/01/01"
            sessions.mkdir(parents=True)
            other = sessions / "other.jsonl"
            matching = sessions / "matching.jsonl"
            other.write_text(
                json.dumps({"type": "session_meta", "payload": {"cwd": "/other"}}), encoding="utf-8"
            )
            matching.write_text(
                json.dumps({"type": "session_meta", "payload": {"cwd": "/work"}}), encoding="utf-8"
            )

            original = share_session.os.environ.get("CODEX_HOME")
            share_session.os.environ["CODEX_HOME"] = str(root)
            try:
                result = share_session.find_latest_session(Path("/work"))
            finally:
                if original is None:
                    share_session.os.environ.pop("CODEX_HOME", None)
                else:
                    share_session.os.environ["CODEX_HOME"] = original

        self.assertEqual(result.name, "matching.jsonl")


if __name__ == "__main__":
    unittest.main()

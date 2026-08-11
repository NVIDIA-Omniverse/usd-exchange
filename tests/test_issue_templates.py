import re
import unittest
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / ".github" / "ISSUE_TEMPLATE"


class TestIssueTemplates(unittest.TestCase):
    def test_element_ids_are_valid(self):
        id_re = re.compile(r"^\s*id:\s*(\S.*?)\s*$")
        valid_id = re.compile(r"^[a-z0-9_-]+$")
        for path in sorted(TEMPLATE_DIR.glob("*.yml")):
            with self.subTest(file=path.name):
                for line in path.read_text(encoding="utf-8").splitlines():
                    match = id_re.match(line)
                    if match:
                        element_id = match.group(1)
                        self.assertRegex(
                            element_id, valid_id,
                            f"Invalid form element id {element_id!r} in {path.name}",

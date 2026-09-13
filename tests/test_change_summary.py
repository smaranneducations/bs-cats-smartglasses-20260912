import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_change_summary import main, parse_sections, validate


VALID = """## Problem statement
The reviewer needs a concise explanation.

## Issue/change identified
The current PR body has no fixed summary contract.

## Root cause or opportunity rationale
Templates and CI do not enforce one.

## Key steps
Add the template and validator.
Validate it in CI.
"""


class ChangeSummaryTests(unittest.TestCase):
    def test_valid_summary_passes(self):
        self.assertEqual(validate(VALID), [])

    def test_aliases_support_bug_and_enhancement_language(self):
        body = VALID.replace("Issue/change identified", "Change identified").replace(
            "Root cause or opportunity rationale", "Root cause"
        )
        self.assertEqual(validate(body), [])

    def test_missing_section_is_rejected(self):
        body = VALID.replace("## Key steps\nAdd the template and validator.\nValidate it in CI.\n", "")
        self.assertIn("missing or empty section: key_steps", validate(body))

    def test_more_than_two_non_empty_lines_is_rejected(self):
        body = VALID.replace("Validate it in CI.", "Validate it in CI.\nDocument it.")
        self.assertIn("section exceeds 2 non-empty lines: key_steps", validate(body))

    def test_template_comments_are_not_counted(self):
        body = VALID.replace(
            "The reviewer needs a concise explanation.",
            "<!-- guidance\nnot content\n-->\nThe reviewer needs a concise explanation.",
        )
        self.assertEqual(validate(body), [])

    def test_sections_are_parsed_by_canonical_key(self):
        self.assertEqual(len(parse_sections(VALID)["key_steps"]), 2)


if __name__ == "__main__":
    unittest.main()

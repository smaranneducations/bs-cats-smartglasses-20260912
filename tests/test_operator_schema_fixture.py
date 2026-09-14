"""Keep browser form regression fixtures aligned with the server contract."""
import json
from pathlib import Path
import unittest

from packages.contracts.governance import PAYLOAD_TYPES


class OperatorSchemaFixtureTest(unittest.TestCase):
    def test_browser_fixture_matches_registered_payload_schemas(self):
        path = Path(__file__).parent / "fixtures" / "operator-payload-schemas.json"
        fixtures = json.loads(path.read_text())
        self.assertEqual(len(fixtures), 6)
        for name, schema in fixtures.items():
            with self.subTest(object_type=name):
                self.assertEqual(schema, PAYLOAD_TYPES[name].model_json_schema())

from __future__ import annotations

import unittest

from pyrustengine.native_engine import execute_command


INITIAL_POSITION = "b/qbk/n1b1n/r5r/ppppppppp/11/5P5/4P1P4/3P1B1P3/2P2B2P2/1PRNQBKNRP1 w - 0 1"


class NativeEngineTests(unittest.TestCase):
    def test_ping(self) -> None:
        response = execute_command("hexchess/ping", {})

        self.assertIn("now", response)
        self.assertIsInstance(response["now"], int)

    def test_evaluate(self) -> None:
        response = execute_command(
            "hexchess/evaluate",
            {
                "depth": 1,
                "position": INITIAL_POSITION,
            },
        )

        self.assertEqual(response["depth"], 1)
        self.assertIn("evaluations", response)
        self.assertIn("sans", response)
        self.assertIsInstance(response["sans"], list)


if __name__ == "__main__":
    unittest.main()
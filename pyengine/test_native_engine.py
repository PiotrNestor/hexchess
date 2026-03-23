from __future__ import annotations

import unittest

from pyengine.native_engine import Hexchess, INITIAL_POSITION, San, search


class NativeEngineTests(unittest.TestCase):
    def test_parse_san_with_two_digit_rank(self) -> None:
        san = San.parse('f10f11q')

        self.assertEqual(str(san), 'f10f11q')
        self.assertEqual(san.promotion, 'q')

    def test_initial_position_current_moves(self) -> None:
        moves = [str(move) for move in Hexchess(INITIAL_POSITION).current_moves()]

        self.assertEqual(len(moves), 51)
        self.assertEqual(
            moves[:10],
            ['f5f6', 'e4e5', 'e4e6', 'g4g5', 'g4g6', 'd3d4', 'd3d5', 'f3h2', 'f3d2', 'h3h4'],
        )

    def test_initial_position_depth_one_search(self) -> None:
        result = search(Hexchess(INITIAL_POSITION), 1)

        self.assertEqual(result['depth'], 1)
        self.assertEqual(result['evaluations'], 51)
        self.assertEqual(result['sans'][0]['san'], 'e4e6')
        self.assertAlmostEqual(result['sans'][0]['score'], -0.32, places=6)


if __name__ == '__main__':
    unittest.main()
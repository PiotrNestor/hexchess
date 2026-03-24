from __future__ import annotations

import unittest

from cyengine.native_engine import (
    Hexchess,
    INITIAL_POSITION,
    San,
    compute_piece_lists,
    compute_zobrist_hash,
    create_board,
    evaluate,
    index,
    search,
)


def build_position(turn: str, pieces: dict[str, str]) -> Hexchess:
    board = create_board()

    for position, piece in pieces.items():
        board[index(position)] = piece

    white_pieces, black_pieces = compute_piece_lists(board)

    return Hexchess.from_state(
        board=board,
        ep=None,
        turn=turn,
        halfmove=0,
        fullmove=1,
        white_king=next((square for square, piece in enumerate(board) if piece == 'K'), None),
        black_king=next((square for square, piece in enumerate(board) if piece == 'k'), None),
        white_pieces=white_pieces,
        black_pieces=black_pieces,
        zobrist_hash=compute_zobrist_hash(board, turn, None),
    )


class CyNativeEngineTests(unittest.TestCase):
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
        self.assertGreaterEqual(result['evaluations'], 51)
        self.assertIn(result['sans'][0]['san'], {'d3d5', 'h3h5', 'c2c4', 'i2i4', 'b1b3', 'k1k3'})
        self.assertAlmostEqual(result['sans'][0]['score'], -0.32, places=6)

    def test_evaluate_penalizes_piece_left_under_pawn_attack(self) -> None:
        safe = build_position('w', {'f1': 'K', 'f11': 'k', 'g5': 'Q', 'g7': 'p'})
        attacked = build_position('w', {'f1': 'K', 'f11': 'k', 'f7': 'Q', 'g7': 'p'})

        self.assertGreater(evaluate(safe), evaluate(attacked))


if __name__ == '__main__':
    unittest.main()
from __future__ import annotations

import unittest

from pyengine2.native_engine import CHAR_TO_PIECE, EvalOptions, Hexchess, INITIAL_POSITION, San, _passes_qsearch_delta_prune, create_board, evaluate, index, search, stringify_board


def build_position(turn: str, pieces: dict[str, str], ep: str = '-') -> Hexchess:
    board = create_board()
    for position, piece in pieces.items():
        board[index(position)] = CHAR_TO_PIECE[piece]
    return Hexchess.parse(f'{stringify_board(board)} {turn} {ep} 0 1')


def move_strings(position: Hexchess) -> list[str]:
    return [str(move) for move in position.current_moves()]


def fast_move_strings(position: Hexchess) -> set[str]:
    return {str(San.from_code(move_code)) for move_code in position._current_moves_codes()}


def tactical_move_strings(position: Hexchess) -> set[str]:
    return {str(San.from_code(move_code)) for move_code in position._current_moves_codes(tactical_only=True)}


class NativeEngine2Tests(unittest.TestCase):
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
        metrics = result['metrics']
        self.assertIn('negamaxTtHits', metrics)
        self.assertIn('quiescenceTtHits', metrics)
        self.assertIn('qsearchDeltaPruneSkips', metrics)
        self.assertIn('qsearchStandPatCutoffs', metrics)
        self.assertIn('pvsResearches', metrics)
        self.assertIn('negamaxFrontierFutilitySkips', metrics)
        self.assertIn('nullMoveCutoffs', metrics)

    def test_search_without_diagnostics_omits_extra_metrics(self) -> None:
        result = search(Hexchess(INITIAL_POSITION), 1, diagnostics=False)

        metrics = result['metrics']
        self.assertIn('ttHits', metrics)
        self.assertIn('ttCutoffs', metrics)
        self.assertIn('betaCutoffs', metrics)
        self.assertNotIn('negamaxTtHits', metrics)
        self.assertNotIn('qsearchDeltaPruneSkips', metrics)
        self.assertNotIn('negamaxFrontierFutilitySkips', metrics)
        self.assertNotIn('nullMoveCutoffs', metrics)

    def test_null_move_restores_position_and_hash(self) -> None:
        position = Hexchess(INITIAL_POSITION)
        before = position.to_string()
        before_hash = position.position_key()

        undo = position.make_null_move()
        position.unmake_null_move(undo)

        self.assertEqual(position.to_string(), before)
        self.assertEqual(position.position_key(), before_hash)

    def test_evaluate_prefers_safe_queen(self) -> None:
        safe = build_position('w', {'f1': 'K', 'f11': 'k', 'g5': 'Q', 'g7': 'p'})
        attacked = build_position('w', {'f1': 'K', 'f11': 'k', 'f7': 'Q', 'g7': 'p'})
        self.assertGreater(evaluate(safe), evaluate(attacked))

    def test_en_passant_illegal_if_it_exposes_king(self) -> None:
        position = build_position('w', {'e10': 'K', 'l6': 'k', 'e5': 'P', 'f5': 'p', 'e4': 'r'}, ep='f6')

        moves = move_strings(position)

        self.assertNotIn('e5f6', moves)
        self.assertIn('e5e6', moves)

    def test_en_passant_legal_when_king_stays_safe(self) -> None:
        position = build_position('w', {'e10': 'K', 'l6': 'k', 'e5': 'P', 'f5': 'p'}, ep='f6')

        moves = move_strings(position)

        self.assertIn('e5f6', moves)

        advanced = position.clone().apply_move('e5f6')
        self.assertEqual(advanced.get('f6'), 'P')
        self.assertIsNone(advanced.get('f5'))

    def test_quiet_promotion_generates_four_choices(self) -> None:
        position = build_position('w', {'a1': 'K', 'l6': 'k', 'f10': 'P'})

        promotions = {move for move in move_strings(position) if move.startswith('f10f11')}

        self.assertSetEqual(promotions, {'f10f11b', 'f10f11n', 'f10f11q', 'f10f11r'})
        self.assertNotIn('f10f11', move_strings(position))

    def test_capture_promotion_generates_four_choices(self) -> None:
        position = build_position('w', {'a1': 'K', 'l6': 'k', 'f10': 'P', 'g10': 'r'})

        promotions = {move for move in move_strings(position) if move.startswith('f10g10')}

        self.assertSetEqual(promotions, {'f10g10b', 'f10g10n', 'f10g10q', 'f10g10r'})

    def test_double_check_allows_only_king_moves(self) -> None:
        position = build_position('w', {'f1': 'K', 'f11': 'k', 'f3': 'r', 'e3': 'q'})

        moves = move_strings(position)

        self.assertEqual(moves, ['f1g1'])

    def test_pinned_knight_has_no_legal_moves(self) -> None:
        position = build_position('w', {'f1': 'K', 'f11': 'k', 'f2': 'N', 'f4': 'r'})

        moves = move_strings(position)

        self.assertFalse(any(move.startswith('f2') for move in moves))
        self.assertEqual(moves, ['f1e2', 'f1g2', 'f1e1', 'f1g1'])

    def test_public_stable_ordering_for_rook_moves(self) -> None:
        position = build_position('w', {'a1': 'K', 'l6': 'k', 'f5': 'R'})

        moves = move_strings(position)

        self.assertEqual(
            moves[:10],
            ['f5f11', 'f5f10', 'f5f9', 'f5f8', 'f5f7', 'f5f6', 'f5g5', 'f5h5', 'f5i5', 'f5k5'],
        )

    def test_fast_path_legal_move_set_matches_public_move_set(self) -> None:
        positions = [
            Hexchess(INITIAL_POSITION),
            build_position('w', {'e10': 'K', 'l6': 'k', 'e5': 'P', 'f5': 'p'}, ep='f6'),
        ]

        for position in positions:
            with self.subTest(position=position):
                self.assertSetEqual(fast_move_strings(position), set(move_strings(position)))

    def test_fast_path_legal_move_set_matches_public_move_set_for_pinned_knight(self) -> None:
        position = build_position('w', {'f1': 'K', 'f11': 'k', 'f2': 'N', 'f4': 'r'})

        self.assertSetEqual(fast_move_strings(position), set(move_strings(position)))

    def test_tactical_only_move_generation_returns_only_captures(self) -> None:
        position = build_position('w', {'a1': 'K', 'l6': 'k', 'f5': 'Q', 'f7': 'r', 'g6': 'p', 'h5': 'p'})

        tactical_moves = tactical_move_strings(position)

        self.assertSetEqual(tactical_moves, {'f5f7', 'f5g6', 'f5h5'})

    def test_qsearch_delta_prune_skips_low_value_capture_when_alpha_is_far_above(self) -> None:
        position = build_position('w', {'a1': 'K', 'l6': 'k', 'f5': 'Q', 'g6': 'p'})
        move = San.parse('f5g6').encode()

        self.assertFalse(_passes_qsearch_delta_prune(position, move, stand_pat=0.0, alpha=40.0, tt_move=None, options=EvalOptions()))

    def test_qsearch_delta_prune_never_skips_promotion_or_tt_move(self) -> None:
        promotion_position = build_position('w', {'a1': 'K', 'l6': 'k', 'f10': 'P'})
        promotion_move = San.parse('f10f11q').encode()
        capture_position = build_position('w', {'a1': 'K', 'l6': 'k', 'f5': 'Q', 'g6': 'p'})
        tt_move = San.parse('f5g6').encode()

        options = EvalOptions()
        self.assertTrue(_passes_qsearch_delta_prune(promotion_position, promotion_move, stand_pat=0.0, alpha=100.0, tt_move=None, options=options))
        self.assertTrue(_passes_qsearch_delta_prune(capture_position, tt_move, stand_pat=0.0, alpha=100.0, tt_move=tt_move, options=options))


if __name__ == '__main__':
    unittest.main()
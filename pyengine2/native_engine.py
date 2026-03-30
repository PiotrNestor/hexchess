from __future__ import annotations

import time
from dataclasses import dataclass
from random import Random
from typing import Literal

from pyengine2.board_constants import EMPTY_POSITION, GRAPH, INITIAL_POSITION, POSITIONS


Color = Literal['w', 'b']
Direction = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
PromotionPiece = Literal['q', 'r', 'b', 'n']

WHITE = 0
BLACK = 1

EMPTY = 0
WP = 1
WR = 2
WN = 3
WB = 4
WQ = 5
WK = 6
BP = 7
BR = 8
BN = 9
BB = 10
BQ = 11
BK = 12

PAWN = 0
ROOK = 1
KNIGHT = 2
BISHOP = 3
QUEEN = 4
KING = 5

PIECE_TO_CHAR = {
    EMPTY: None,
    WP: 'P', WR: 'R', WN: 'N', WB: 'B', WQ: 'Q', WK: 'K',
    BP: 'p', BR: 'r', BN: 'n', BB: 'b', BQ: 'q', BK: 'k',
}
CHAR_TO_PIECE = {char: piece for piece, char in PIECE_TO_CHAR.items() if char is not None}
PIECE_KIND = {
    WP: PAWN, WR: ROOK, WN: KNIGHT, WB: BISHOP, WQ: QUEEN, WK: KING,
    BP: PAWN, BR: ROOK, BN: KNIGHT, BB: BISHOP, BQ: QUEEN, BK: KING,
}
PIECE_COLOR = {
    WP: WHITE, WR: WHITE, WN: WHITE, WB: WHITE, WQ: WHITE, WK: WHITE,
    BP: BLACK, BR: BLACK, BN: BLACK, BB: BLACK, BQ: BLACK, BK: BLACK,
}
PROMOTION_CODE_TO_CHAR = (None, 'b', 'n', 'q', 'r')
PROMOTION_CHAR_TO_CODE = {None: 0, 'b': 1, 'n': 2, 'q': 3, 'r': 4}
PROMOTION_CODE_TO_KIND = (None, BISHOP, KNIGHT, QUEEN, ROOK)

BOARD_ROW_BREAKS = frozenset({0, 3, 8, 15, 24, 35, 46, 57, 68, 79})
ALL_PROMOTION_POSITIONS = frozenset({
    0, 1, 3, 4, 8, 9, 15, 16, 24, 25, 35,
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
})
WHITE_PROMOTION_POSITIONS = frozenset({0, 1, 3, 4, 8, 9, 15, 16, 24, 25, 35})
BLACK_PROMOTION_POSITIONS = frozenset({80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90})
BLACK_PAWN_STARTS = frozenset({16, 17, 18, 19, 20, 21, 22, 23, 24})
WHITE_PAWN_STARTS = frozenset({41, 51, 53, 61, 65, 71, 77, 81, 89})
LEGAL_EN_PASSANT = frozenset({26, 27, 28, 29, 30, 31, 32, 33, 34, 40, 42, 50, 54, 60, 66, 70, 78})
WHITE_EN_PASSANT_TARGETS = {
    (71, 49): 60,
    (61, 39): 50,
    (51, 29): 40,
    (41, 20): 30,
    (53, 31): 42,
    (65, 43): 54,
    (77, 55): 66,
    (89, 67): 78,
}
BLACK_EN_PASSANT_TARGETS = {
    (17, 38): 27,
    (18, 39): 28,
    (19, 40): 29,
    (20, 41): 30,
    (21, 42): 31,
    (22, 43): 32,
    (23, 44): 33,
    (24, 45): 34,
}
KNIGHT_DIRECTION_SETS = (
    (1, 0, 2),
    (3, 2, 4),
    (5, 4, 6),
    (7, 6, 8),
    (9, 8, 10),
    (11, 10, 0),
)
ORTHOGONAL_DIRECTIONS = frozenset({0, 2, 4, 6, 8, 10})
DIAGONAL_DIRECTIONS = frozenset({1, 3, 5, 7, 9, 11})

WHITE_ADVANCEMENT_SCALARS = {
    'f10': 1.0, 'e9': 1.0, 'f9': 0.8, 'g9': 1.0, 'd8': 1.0, 'e8': 0.8, 'f8': 0.6, 'g8': 0.8,
    'h8': 1.0, 'c7': 1.0, 'd7': 0.8, 'e7': 0.6, 'f7': 0.4, 'g7': 0.6, 'h7': 0.8, 'i7': 1.0,
    'b6': 1.0, 'c6': 0.8, 'd6': 0.6, 'e6': 0.4, 'f6': 0.2, 'g6': 0.4, 'h6': 0.6, 'i6': 0.8,
    'k6': 1.0, 'a5': 1.0, 'b5': 0.8, 'c5': 0.6, 'd5': 0.4, 'e5': 0.2, 'g5': 0.2, 'h5': 0.4,
    'i5': 0.6, 'k5': 0.8, 'l5': 1.0, 'a4': 0.8, 'b4': 0.6, 'c4': 0.4, 'd4': 0.2, 'h4': 0.2,
    'i4': 0.4, 'k4': 0.6, 'l4': 0.8, 'a3': 0.6, 'b3': 0.4, 'c3': 0.2, 'i3': 0.2, 'k3': 0.4,
    'l3': 0.6, 'a2': 0.4, 'b2': 0.2, 'k2': 0.2, 'l2': 0.4, 'a1': 0.2, 'l1': 0.2,
}
BLACK_ADVANCEMENT_SCALARS = {
    name: scalar
    for names, scalar in (
        (('a6', 'b6', 'c6', 'd6', 'e6', 'f6', 'g6', 'h6', 'i6', 'k6', 'l6'), 0.2),
        (('a5', 'b5', 'c5', 'd5', 'e5', 'f5', 'g5', 'h5', 'i5', 'k5', 'l5'), 0.4),
        (('a4', 'b4', 'c4', 'd4', 'e4', 'f4', 'g4', 'h4', 'i4', 'k4', 'l4'), 0.6),
        (('a3', 'b3', 'c3', 'd3', 'e3', 'f3', 'g3', 'h3', 'i3', 'k3', 'l3'), 0.8),
        (('a2', 'b2', 'c2', 'd2', 'e2', 'f2', 'g2', 'h2', 'i2', 'k2', 'l2'), 1.0),
    )
    for name in names
}

PIECE_VALUES = {
    PAWN: 10,
    KNIGHT: 30,
    BISHOP: 30,
    ROOK: 50,
    QUEEN: 90,
    KING: 0,
}
PAWN_ATTACK_PENALTY = {
    KNIGHT: 8.0,
    BISHOP: 8.0,
    ROOK: 12.0,
    QUEEN: 20.0,
}
PROMOTION_ORDER_BONUS = {
    1: 700,
    2: 700,
    3: 1000,
    4: 800,
}
PIECE_ORDER_VALUES = tuple(PIECE_VALUES[PIECE_KIND[piece]] if piece in PIECE_KIND else 0 for piece in range(BK + 1))
ALL_BOARD_MASK = (1 << 91) - 1
ALL_PIN_MASKS = (ALL_BOARD_MASK,) * 91
PAWN_FORWARD_TARGETS = (
    tuple(-1 if GRAPH[square][0] is None else GRAPH[square][0] for square in range(91)),
    tuple(-1 if GRAPH[square][6] is None else GRAPH[square][6] for square in range(91)),
)
PAWN_DOUBLE_TARGETS = (
    tuple(
        -1
        if square not in WHITE_PAWN_STARTS or GRAPH[square][0] is None or GRAPH[GRAPH[square][0]][0] is None
        else GRAPH[GRAPH[square][0]][0]
        for square in range(91)
    ),
    tuple(
        -1
        if square not in BLACK_PAWN_STARTS or GRAPH[square][6] is None or GRAPH[GRAPH[square][6]][6] is None
        else GRAPH[GRAPH[square][6]][6]
        for square in range(91)
    ),
)
PAWN_CAPTURE_TARGETS = (
    tuple(
        (
            -1 if GRAPH[square][10] is None else GRAPH[square][10],
            -1 if GRAPH[square][2] is None else GRAPH[square][2],
        )
        for square in range(91)
    ),
    tuple(
        (
            -1 if GRAPH[square][4] is None else GRAPH[square][4],
            -1 if GRAPH[square][8] is None else GRAPH[square][8],
        )
        for square in range(91)
    ),
)
PAWN_PROMOTION_MASKS = (
    tuple(square in WHITE_PROMOTION_POSITIONS for square in range(91)),
    tuple(square in BLACK_PROMOTION_POSITIONS for square in range(91)),
)
PAWN_EP_CAPTURE_SQUARES = (
    tuple(-1 if GRAPH[square][6] is None else GRAPH[square][6] for square in range(91)),
    tuple(-1 if GRAPH[square][0] is None else GRAPH[square][0] for square in range(91)),
)


class NativeEngineError(ValueError):
    pass


def error(message: str) -> None:
    raise NativeEngineError(f'[hexchess error] {message}')
POSITION_TO_INDEX = {position: index for index, position in enumerate(POSITIONS)}
WHITE_ADVANCEMENT_BONUS = {POSITION_TO_INDEX[name]: scalar * scalar * 2.0 for name, scalar in WHITE_ADVANCEMENT_SCALARS.items()}
BLACK_ADVANCEMENT_BONUS = {POSITION_TO_INDEX[name]: scalar * scalar * 2.0 for name, scalar in BLACK_ADVANCEMENT_SCALARS.items()}
WHITE_ADVANCEMENT_BONUS_BY_INDEX = tuple(WHITE_ADVANCEMENT_BONUS.get(square, 0.0) for square in range(91))
BLACK_ADVANCEMENT_BONUS_BY_INDEX = tuple(BLACK_ADVANCEMENT_BONUS.get(square, 0.0) for square in range(91))


def _bit(index_value: int) -> int:
    return 1 << index_value


def _iter_bits(mask: int):
    while mask:
        lsb = mask & -mask
        yield lsb.bit_length() - 1
        mask ^= lsb


def _build_rays() -> tuple[tuple[tuple[int, ...], ...], ...]:
    rays: list[list[tuple[int, ...]]] = []
    for source in range(91):
        row: list[tuple[int, ...]] = []
        for direction in range(12):
            path: list[int] = []
            current = source
            while True:
                current = GRAPH[current][direction]
                if current is None:
                    break
                path.append(current)
            row.append(tuple(path))
        rays.append(row)
    return tuple(tuple(row) for row in rays)


RAYS = _build_rays()


def _build_line_masks() -> tuple[tuple[int, ...], tuple[int, ...]]:
    orthogonal_masks: list[int] = []
    diagonal_masks: list[int] = []
    for source in range(91):
        orthogonal_mask = 0
        diagonal_mask = 0
        for direction in range(12):
            mask = 0
            for target in RAYS[source][direction]:
                mask |= _bit(target)
            if direction in ORTHOGONAL_DIRECTIONS:
                orthogonal_mask |= mask
            else:
                diagonal_mask |= mask
        orthogonal_masks.append(orthogonal_mask)
        diagonal_masks.append(diagonal_mask)
    return tuple(orthogonal_masks), tuple(diagonal_masks)


def _build_ray_masks_and_scans() -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[tuple[tuple[int, int, int], ...], ...], ...]]:
    ray_masks: list[list[int]] = []
    ray_scans: list[list[tuple[tuple[int, int, int], ...]]] = []
    for source in range(91):
        mask_row: list[int] = []
        scan_row: list[tuple[tuple[int, int, int], ...]] = []
        for direction in range(12):
            mask = 0
            entries: list[tuple[int, int, int]] = []
            for target in RAYS[source][direction]:
                target_bit = _bit(target)
                mask |= target_bit
                entries.append((target, target_bit, mask))
            mask_row.append(mask)
            scan_row.append(tuple(entries))
        ray_masks.append(mask_row)
        ray_scans.append(scan_row)
    return tuple(tuple(row) for row in ray_masks), tuple(tuple(row) for row in ray_scans)


def _build_ray_attack_tables() -> tuple[tuple[dict[int, int], ...], ...]:
    attack_tables: list[list[dict[int, int]]] = []
    for source in range(91):
        row: list[dict[int, int]] = []
        for direction in range(12):
            ray = RAYS[source][direction]
            ray_bits = tuple(1 << target for target in ray)
            table: dict[int, int] = {}
            subset_count = 1 << len(ray_bits)
            for subset_index in range(subset_count):
                occupancy_subset = 0
                for offset, target_bit in enumerate(ray_bits):
                    if subset_index & (1 << offset):
                        occupancy_subset |= target_bit

                attack_mask = 0
                for target_bit in ray_bits:
                    attack_mask |= target_bit
                    if occupancy_subset & target_bit:
                        break

                table[occupancy_subset] = attack_mask
            row.append(table)
        attack_tables.append(row)
    return tuple(tuple(row) for row in attack_tables)


def _build_king_masks() -> tuple[int, ...]:
    masks: list[int] = []
    for source in range(91):
        mask = 0
        for direction in range(12):
            target = GRAPH[source][direction]
            if target is not None:
                mask |= _bit(target)
        masks.append(mask)
    return tuple(masks)


def _build_knight_masks() -> tuple[int, ...]:
    masks: list[int] = []
    for source in range(91):
        mask = 0
        for diagonal, orthogonal1, orthogonal2 in KNIGHT_DIRECTION_SETS:
            intermediate = GRAPH[source][diagonal]
            if intermediate is None:
                continue
            first = GRAPH[intermediate][orthogonal1]
            second = GRAPH[intermediate][orthogonal2]
            if first is not None:
                mask |= _bit(first)
            if second is not None:
                mask |= _bit(second)
        masks.append(mask)
    return tuple(masks)


def _build_knight_targets() -> tuple[tuple[int, ...], ...]:
    targets: list[tuple[int, ...]] = []
    for source in range(91):
        ordered: list[int] = []
        for diagonal, orthogonal1, orthogonal2 in KNIGHT_DIRECTION_SETS:
            intermediate = GRAPH[source][diagonal]
            if intermediate is None:
                continue
            first = GRAPH[intermediate][orthogonal1]
            second = GRAPH[intermediate][orthogonal2]
            if first is not None:
                ordered.append(first)
            if second is not None:
                ordered.append(second)
        targets.append(tuple(ordered))
    return tuple(targets)


def _build_pawn_attack_sources() -> tuple[tuple[int, ...], tuple[int, ...]]:
    sources = [[0 for _ in range(91)] for _ in range(2)]
    white_directions = (6, 8)
    black_directions = (10, 2)
    for square in range(91):
        for direction in white_directions:
            source = GRAPH[square][direction]
            if source is not None:
                sources[WHITE][square] |= _bit(source)
        for direction in black_directions:
            source = GRAPH[square][direction]
            if source is not None:
                sources[BLACK][square] |= _bit(source)
    return tuple(tuple(row) for row in sources)  # type: ignore[return-value]


def _build_pawn_attack_targets() -> tuple[tuple[int, ...], tuple[int, ...]]:
    targets = [[0 for _ in range(91)] for _ in range(2)]
    white_directions = (10, 2)
    black_directions = (4, 8)
    for square in range(91):
        for direction in white_directions:
            target = GRAPH[square][direction]
            if target is not None:
                targets[WHITE][square] |= _bit(target)
        for direction in black_directions:
            target = GRAPH[square][direction]
            if target is not None:
                targets[BLACK][square] |= _bit(target)
    return tuple(tuple(row) for row in targets)  # type: ignore[return-value]


KING_ATTACK_MASKS = _build_king_masks()
KNIGHT_ATTACK_MASKS = _build_knight_masks()
KNIGHT_TARGETS = _build_knight_targets()
PAWN_ATTACK_SOURCES = _build_pawn_attack_sources()
PAWN_ATTACK_TARGETS = _build_pawn_attack_targets()
ORTHOGONAL_LINE_MASKS, DIAGONAL_LINE_MASKS = _build_line_masks()
RAY_MASKS, RAY_SCANS = _build_ray_masks_and_scans()
RAY_ATTACK_TABLES = _build_ray_attack_tables()

_zobrist_random = Random(0)
ZOBRIST_PIECES = tuple(tuple(_zobrist_random.getrandbits(64) for _ in range(91)) for _ in range(12))
ZOBRIST_TURN = _zobrist_random.getrandbits(64)
ZOBRIST_EP = tuple(_zobrist_random.getrandbits(64) for _ in range(91))


def _piece_hash(piece: int, square: int) -> int:
    return ZOBRIST_PIECES[piece - 1][square]


def _color_to_int(color: Color | int) -> int:
    if color == 'w' or color == WHITE:
        return WHITE
    return BLACK


def _color_to_char(color: int) -> Color:
    return 'w' if color == WHITE else 'b'


def _other_color(color: int) -> int:
    return BLACK if color == WHITE else WHITE


def _piece_from_kind(kind: int, color: int) -> int:
    if color == WHITE:
        return (WP, WR, WN, WB, WQ, WK)[kind]
    return (BP, BR, BN, BB, BQ, BK)[kind]


def _promotion_piece(color: int, promotion_code: int) -> int:
    kind = PROMOTION_CODE_TO_KIND[promotion_code]
    if kind is None:
        error('invalid promotion code')
    return _piece_from_kind(kind, color)


def index(position: str) -> int:
    try:
        return POSITION_TO_INDEX[position]
    except KeyError as exc:
        error(f'invalid position: {position}')
        raise exc


def is_position(source: str) -> bool:
    return source in POSITION_TO_INDEX


def create_board() -> bytearray:
    return bytearray(91)


def compute_zobrist_hash(board: bytearray, turn: Color | int, ep: int | None) -> int:
    value = 0
    for square, piece in enumerate(board):
        if piece:
            value ^= _piece_hash(piece, square)
    if _color_to_int(turn) == BLACK:
        value ^= ZOBRIST_TURN
    if ep is not None:
        value ^= ZOBRIST_EP[ep]
    return value


def stringify_board(board: bytearray) -> str:
    blank = 0
    result: list[str] = []
    for board_index, piece in enumerate(board):
        if piece == EMPTY:
            blank += 1
        else:
            if blank > 0:
                result.append(str(blank))
                blank = 0
            result.append(PIECE_TO_CHAR[piece] or '')
        if board_index in BOARD_ROW_BREAKS:
            if blank > 0:
                result.append(str(blank))
                blank = 0
            result.append('/')
    if blank > 0:
        result.append(str(blank))
    return ''.join(result)


def parse_board(source: str) -> bytearray:
    board = create_board()
    black_king = False
    white_king = False
    board_index = 0
    i = 0
    while i < len(source):
        current = source[i]
        if current == '1':
            if i + 1 < len(source) and source[i + 1] in {'0', '1'}:
                board_index += 10 if source[i + 1] == '0' else 11
                i += 2
                continue
            board_index += 1
            i += 1
            continue
        if current in {'2', '3', '4', '5', '6', '7', '8', '9'}:
            board_index += int(current)
            i += 1
            continue
        if current == 'K':
            if white_king:
                error('parse failed: multiple white kings')
            white_king = True
        if current == 'k':
            if black_king:
                error('parse failed: multiple black kings')
            black_king = True
        if current in CHAR_TO_PIECE:
            board[board_index] = CHAR_TO_PIECE[current]
            board_index += 1
            i += 1
            continue
        if current == '/':
            i += 1
            continue
        error(f'parse failed: invalid piece {current}')
    if board_index != 91:
        error('parse failed: invalid length')
    return board


def _encode_move(from_index: int, to_index: int, promotion_code: int = 0) -> int:
    return (from_index << 10) | (to_index << 3) | promotion_code


def _move_from(move_code: int) -> int:
    return (move_code >> 10) & 0x7F


def _move_to(move_code: int) -> int:
    return (move_code >> 3) & 0x7F


def _move_promotion(move_code: int) -> int:
    return move_code & 0x7


MAX_MOVE_CODE = _encode_move(90, 90, 7)
MOVE_CODE_CAPACITY = MAX_MOVE_CODE + 1


@dataclass(frozen=True, slots=True)
class San:
    from_index: int
    to_index: int
    promotion: PromotionPiece | None = None

    @classmethod
    def from_value(cls, value: 'San | str') -> 'San':
        return value if isinstance(value, San) else cls.parse(value)

    @classmethod
    def from_code(cls, move_code: int) -> 'San':
        return cls(_move_from(move_code), _move_to(move_code), PROMOTION_CODE_TO_CHAR[_move_promotion(move_code)])

    @classmethod
    def parse(cls, source: str) -> 'San':
        from_position = next((position for position in POSITIONS if source.startswith(position)), None)
        if from_position is None:
            error(f'invalid san from: {from_position}')
        tail = source[len(from_position):]
        to_position = next((position for position in POSITIONS if tail.startswith(position)), None)
        if to_position is None:
            error(f'invalid san to: {to_position}')
        if from_position == to_position:
            error('invalid san: from and to are the same')
        promotion: PromotionPiece | None = None
        if len(source) > len(from_position) + len(to_position):
            last = source[-1]
            if last not in {'b', 'n', 'q', 'r'}:
                error(f'invalid san promotion: {source} - {last}')
            if index(to_position) not in ALL_PROMOTION_POSITIONS:
                error(f'invalid san promotion: {source} - {last}')
            promotion = last  # type: ignore[assignment]
        if len(from_position) + len(to_position) + (1 if promotion else 0) != len(source):
            error(f'invalid san: {source}')
        return cls(index(from_position), index(to_position), promotion)

    def encode(self) -> int:
        return _encode_move(self.from_index, self.to_index, PROMOTION_CHAR_TO_CODE[self.promotion])

    def __str__(self) -> str:
        return f'{POSITIONS[self.from_index]}{POSITIONS[self.to_index]}{self.promotion or ""}'


MoveUndo = tuple[int, int, int, int, int, int, int, int, int, int, int]
NullMoveUndo = tuple[int, int, int, int, int]
LegalContext = tuple[int, int, int, list[int], bool]
RayScanEntry = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class EvalOptions:
    bishop_value: float = 30.0
    king_value: float = 0.0
    knight_value: float = 30.0
    pawn_value: float = 10.0
    queen_value: float = 90.0
    rook_value: float = 50.0
    check_value: float = 1.0
    checkmate_value: float = 99999.9
    stalemate_value: float = 2.0


@dataclass(slots=True)
class SearchState:
    diagnostics_enabled: bool
    move_buffers: list[list[int]]
    pin_mask_buffers: list[list[int]]
    killer_primary: list[int]
    killer_secondary: list[int]
    history_scores: list[int]
    negamax_nodes: int
    quiescence_nodes: int
    movegen_calls: int
    tactical_movegen_calls: int
    legal_context_calls: int
    tt_hits: int
    tt_cutoffs: int
    beta_cutoffs: int
    negamax_tt_hits: int
    quiescence_tt_hits: int
    negamax_tt_cutoffs: int
    quiescence_tt_cutoffs: int
    negamax_beta_cutoffs: int
    quiescence_beta_cutoffs: int
    qsearch_stand_pat_cutoffs: int
    qsearch_delta_prune_checks: int
    qsearch_delta_prune_skips: int
    qsearch_nodes_with_moves: int
    qsearch_generated_moves: int
    pvs_researches: int
    negamax_frontier_futility_checks: int
    negamax_frontier_futility_skips: int
    null_move_attempts: int
    null_move_cutoffs: int

    def __init__(self, diagnostics_enabled: bool = True) -> None:
        self.diagnostics_enabled = diagnostics_enabled
        self.move_buffers = []
        self.pin_mask_buffers = []
        self.killer_primary = []
        self.killer_secondary = []
        self.history_scores = [0] * MOVE_CODE_CAPACITY
        self.negamax_nodes = 0
        self.quiescence_nodes = 0
        self.movegen_calls = 0
        self.tactical_movegen_calls = 0
        self.legal_context_calls = 0
        self.tt_hits = 0
        self.tt_cutoffs = 0
        self.beta_cutoffs = 0
        self.negamax_tt_hits = 0
        self.quiescence_tt_hits = 0
        self.negamax_tt_cutoffs = 0
        self.quiescence_tt_cutoffs = 0
        self.negamax_beta_cutoffs = 0
        self.quiescence_beta_cutoffs = 0
        self.qsearch_stand_pat_cutoffs = 0
        self.qsearch_delta_prune_checks = 0
        self.qsearch_delta_prune_skips = 0
        self.qsearch_nodes_with_moves = 0
        self.qsearch_generated_moves = 0
        self.pvs_researches = 0
        self.negamax_frontier_futility_checks = 0
        self.negamax_frontier_futility_skips = 0
        self.null_move_attempts = 0
        self.null_move_cutoffs = 0

    def buffer_for(self, ply: int) -> list[int]:
        while len(self.move_buffers) <= ply:
            self.move_buffers.append([])
        buffer = self.move_buffers[ply]
        buffer.clear()
        return buffer

    def pin_masks_for(self, ply: int) -> list[int]:
        while len(self.pin_mask_buffers) <= ply:
            self.pin_mask_buffers.append([ALL_BOARD_MASK] * 91)
        return self.pin_mask_buffers[ply]

    def killer_moves_for(self, ply: int) -> tuple[int, int]:
        while len(self.killer_primary) <= ply:
            self.killer_primary.append(-1)
            self.killer_secondary.append(-1)
        return self.killer_primary[ply], self.killer_secondary[ply]

    def record_killer(self, ply: int, move_code: int) -> None:
        first, second = self.killer_moves_for(ply)
        if move_code == first:
            return
        self.killer_primary[ply] = move_code
        self.killer_secondary[ply] = first if first != move_code else second

    def metrics_dict(self, root_moves: int, wall_ms: float, evaluations: int, tt_entries: int) -> dict[str, int | float]:
        metrics: dict[str, int | float] = {
            'wallMs': wall_ms,
            'evalsPerMs': evaluations / wall_ms if wall_ms > 0 else 0.0,
            'rootMoves': root_moves,
            'negamaxNodes': self.negamax_nodes,
            'quiescenceNodes': self.quiescence_nodes,
            'movegenCalls': self.movegen_calls,
            'tacticalMovegenCalls': self.tactical_movegen_calls,
            'legalContextCalls': self.legal_context_calls,
            'ttHits': self.tt_hits,
            'ttCutoffs': self.tt_cutoffs,
            'betaCutoffs': self.beta_cutoffs,
            'ttEntries': tt_entries,
        }
        if self.diagnostics_enabled:
            metrics.update(
                {
                    'negamaxTtHits': self.negamax_tt_hits,
                    'quiescenceTtHits': self.quiescence_tt_hits,
                    'negamaxTtCutoffs': self.negamax_tt_cutoffs,
                    'quiescenceTtCutoffs': self.quiescence_tt_cutoffs,
                    'negamaxBetaCutoffs': self.negamax_beta_cutoffs,
                    'quiescenceBetaCutoffs': self.quiescence_beta_cutoffs,
                    'qsearchStandPatCutoffs': self.qsearch_stand_pat_cutoffs,
                    'qsearchDeltaPruneChecks': self.qsearch_delta_prune_checks,
                    'qsearchDeltaPruneSkips': self.qsearch_delta_prune_skips,
                    'qsearchNodesWithMoves': self.qsearch_nodes_with_moves,
                    'qsearchGeneratedMoves': self.qsearch_generated_moves,
                    'pvsResearches': self.pvs_researches,
                    'negamaxFrontierFutilityChecks': self.negamax_frontier_futility_checks,
                    'negamaxFrontierFutilitySkips': self.negamax_frontier_futility_skips,
                    'nullMoveAttempts': self.null_move_attempts,
                    'nullMoveCutoffs': self.null_move_cutoffs,
                }
            )
        return metrics


@dataclass(slots=True)
class Hexchess:
    board: bytearray
    piece_masks: list[int]
    color_masks: list[int]
    ep: int
    turn: int
    halfmove: int
    fullmove: int
    white_king: int
    black_king: int
    zobrist_hash: int

    def __init__(self, fen: str = EMPTY_POSITION) -> None:
        if not fen:
            error('parse failed: board not found')
        parts = [part.strip() for part in fen.split(' ') if part.strip()]
        board_source = parts[0] if parts else None
        if board_source is None:
            error('parse failed: board not found')
        turn = parts[1] if len(parts) > 1 else 'w'
        ep = parts[2] if len(parts) > 2 else '-'
        halfmove = parts[3] if len(parts) > 3 else '0'
        fullmove = parts[4] if len(parts) > 4 else '1'

        board = parse_board(board_source)
        piece_masks = [0] * 13
        color_masks = [0, 0]
        white_king = -1
        black_king = -1

        for square, piece in enumerate(board):
            if piece == EMPTY:
                continue
            piece_masks[piece] |= _bit(square)
            color_masks[PIECE_COLOR[piece]] |= _bit(square)
            if piece == WK:
                white_king = square
            elif piece == BK:
                black_king = square

        if turn not in {'w', 'b'}:
            error(f'invalid turn color: {turn}')
        self.turn = WHITE if turn == 'w' else BLACK

        if ep == '-':
            self.ep = -1
        elif is_position(ep):
            ep_index = index(ep)
            if ep_index not in LEGAL_EN_PASSANT:
                error(f'illegal en passant: {ep}')
            self.ep = ep_index
        else:
            error(f'invalid en passant: {ep}')

        try:
            parsed_halfmove = int(halfmove)
        except ValueError as exc:
            error(f'invalid halfmove: {halfmove}')
            raise exc
        try:
            parsed_fullmove = int(fullmove)
        except ValueError as exc:
            error(f'invalid fullmove: {fullmove}')
            raise exc
        if parsed_fullmove == 0:
            error(f'invalid fullmove: {fullmove}')

        self.board = board
        self.piece_masks = piece_masks
        self.color_masks = color_masks
        self.halfmove = max(0, parsed_halfmove)
        self.fullmove = parsed_fullmove
        self.white_king = white_king
        self.black_king = black_king
        self.zobrist_hash = compute_zobrist_hash(self.board, self.turn, None if self.ep == -1 else self.ep)

    @classmethod
    def parse(cls, fen: str) -> 'Hexchess':
        return cls(fen)

    @classmethod
    def init(cls) -> 'Hexchess':
        return cls(INITIAL_POSITION)

    @classmethod
    def from_state(
        cls,
        board: bytearray,
        ep: int | None,
        turn: Color | int,
        halfmove: int,
        fullmove: int,
    ) -> 'Hexchess':
        hexchess = cls.__new__(cls)
        hexchess.board = bytearray(board)
        hexchess.piece_masks = [0] * 13
        hexchess.color_masks = [0, 0]
        hexchess.white_king = -1
        hexchess.black_king = -1
        for square, piece in enumerate(hexchess.board):
            if piece == EMPTY:
                continue
            hexchess.piece_masks[piece] |= _bit(square)
            hexchess.color_masks[PIECE_COLOR[piece]] |= _bit(square)
            if piece == WK:
                hexchess.white_king = square
            elif piece == BK:
                hexchess.black_king = square
        hexchess.ep = -1 if ep is None else ep
        hexchess.turn = _color_to_int(turn)
        hexchess.halfmove = halfmove
        hexchess.fullmove = fullmove
        hexchess.zobrist_hash = compute_zobrist_hash(hexchess.board, hexchess.turn, None if hexchess.ep == -1 else hexchess.ep)
        return hexchess

    def clone(self) -> 'Hexchess':
        return Hexchess.from_state(self.board, None if self.ep == -1 else self.ep, self.turn, self.halfmove, self.fullmove)

    def position_key(self) -> int:
        return self.zobrist_hash

    def find_king(self, color: Color | int) -> int | None:
        king = self.white_king if _color_to_int(color) == WHITE else self.black_king
        return None if king == -1 else king

    def get(self, position: str) -> str | None:
        piece = self.board[index(position)]
        return PIECE_TO_CHAR[piece]

    def get_color(self, color: Color | int) -> list[int]:
        return list(_iter_bits(self.color_masks[_color_to_int(color)]))

    def _occupied(self) -> int:
        return self.color_masks[WHITE] | self.color_masks[BLACK]

    def _occupied_on_ray(self, source: int, direction: int, occupied: int) -> int:
        return occupied & RAY_MASKS[source][direction]

    def _piece_at(self, square: int) -> int:
        return self.board[square]

    def _remove_piece(self, square: int, piece: int) -> None:
        mask = _bit(square)
        self.board[square] = EMPTY
        self.piece_masks[piece] &= ~mask
        self.color_masks[PIECE_COLOR[piece]] &= ~mask
        if piece == WK:
            self.white_king = -1
        elif piece == BK:
            self.black_king = -1

    def _place_piece(self, square: int, piece: int) -> None:
        mask = _bit(square)
        self.board[square] = piece
        self.piece_masks[piece] |= mask
        self.color_masks[PIECE_COLOR[piece]] |= mask
        if piece == WK:
            self.white_king = square
        elif piece == BK:
            self.black_king = square

    def current_moves(self) -> list[San]:
        return [San.from_code(move_code) for move_code in self._current_moves_codes(stable_order=True)]

    def _friendly_piece_codes(self, color: int) -> tuple[int, ...]:
        return (WP, WR, WN, WB, WQ, WK) if color == WHITE else (BP, BR, BN, BB, BQ, BK)

    def _fill_current_moves(self, result: list[int], tactical_only: bool = False, stable_order: bool = False, pin_masks: list[int] | None = None, stats: SearchState | None = None) -> list[int]:
        if stats is not None:
            stats.movegen_calls += 1
            if tactical_only:
                stats.tactical_movegen_calls += 1
            stats.legal_context_calls += 1
        legal_context = self._compute_legal_context(self.turn, pin_masks=pin_masks)
        _, check_count, evasion_mask, pin_masks, has_pins = legal_context
        board = self.board
        turn = self.turn
        occupied = self.color_masks[WHITE] | self.color_masks[BLACK]
        target_mask_base = self.color_masks[_other_color(turn)] if tactical_only else (ALL_BOARD_MASK ^ self.color_masks[turn])
        if stable_order:
            squares = self.color_masks[turn]
            while squares:
                square_bit = squares & -squares
                square = square_bit.bit_length() - 1
                piece = board[square]
                if piece == WK or piece == BK:
                    self._append_king_moves(result, square, turn, tactical_only)
                elif check_count <= 1:
                    allowed_mask = pin_masks[square] & evasion_mask
                    if allowed_mask:
                        kind = PIECE_KIND[piece]
                        if kind == PAWN:
                            self._append_pawn_moves(result, square, turn, tactical_only, allowed_mask, occupied)
                        elif kind == KNIGHT:
                            self._append_stable_knight_moves(result, square, turn, tactical_only, allowed_mask)
                        elif kind == BISHOP:
                            self._append_stable_slider_moves(result, square, (1, 3, 5, 7, 9, 11), allowed_mask, occupied, target_mask_base)
                        elif kind == ROOK:
                            self._append_stable_slider_moves(result, square, (0, 2, 4, 6, 8, 10), allowed_mask, occupied, target_mask_base)
                        else:
                            self._append_stable_slider_moves(result, square, tuple(range(12)), allowed_mask, occupied, target_mask_base)
                squares ^= square_bit
            return result

        if turn == WHITE:
            pawn_piece, rook_piece, knight_piece, bishop_piece, queen_piece, king_piece = WP, WR, WN, WB, WQ, WK
        else:
            pawn_piece, rook_piece, knight_piece, bishop_piece, queen_piece, king_piece = BP, BR, BN, BB, BQ, BK

        king_squares = self.piece_masks[king_piece]
        if king_squares:
            self._append_king_moves(result, (king_squares & -king_squares).bit_length() - 1, turn, tactical_only)

        if check_count > 1:
            return result

        if check_count == 0 and not has_pins:
            pawn_squares = self.piece_masks[pawn_piece]
            while pawn_squares:
                square_bit = pawn_squares & -pawn_squares
                square = square_bit.bit_length() - 1
                self._append_pawn_moves_unfiltered(result, square, turn, tactical_only, occupied)
                pawn_squares ^= square_bit

            knight_squares = self.piece_masks[knight_piece]
            while knight_squares:
                square_bit = knight_squares & -knight_squares
                square = square_bit.bit_length() - 1
                self._append_knight_moves(result, square, turn, tactical_only, ALL_BOARD_MASK)
                knight_squares ^= square_bit

            bishop_squares = self.piece_masks[bishop_piece]
            while bishop_squares:
                square_bit = bishop_squares & -bishop_squares
                square = square_bit.bit_length() - 1
                self._append_bishop_moves(result, square, ALL_BOARD_MASK, occupied, target_mask_base)
                bishop_squares ^= square_bit

            rook_squares = self.piece_masks[rook_piece]
            while rook_squares:
                square_bit = rook_squares & -rook_squares
                square = square_bit.bit_length() - 1
                self._append_rook_moves(result, square, ALL_BOARD_MASK, occupied, target_mask_base)
                rook_squares ^= square_bit

            queen_squares = self.piece_masks[queen_piece]
            while queen_squares:
                square_bit = queen_squares & -queen_squares
                square = square_bit.bit_length() - 1
                self._append_queen_moves(result, square, ALL_BOARD_MASK, occupied, target_mask_base)
                queen_squares ^= square_bit
            return result

        pawn_squares = self.piece_masks[pawn_piece]
        while pawn_squares:
            square_bit = pawn_squares & -pawn_squares
            square = square_bit.bit_length() - 1
            allowed_mask = pin_masks[square] & evasion_mask
            if allowed_mask:
                self._append_pawn_moves(result, square, turn, tactical_only, allowed_mask, occupied)
            pawn_squares ^= square_bit

        knight_squares = self.piece_masks[knight_piece]
        while knight_squares:
            square_bit = knight_squares & -knight_squares
            square = square_bit.bit_length() - 1
            allowed_mask = pin_masks[square] & evasion_mask
            if allowed_mask:
                self._append_knight_moves(result, square, turn, tactical_only, allowed_mask)
            knight_squares ^= square_bit

        bishop_squares = self.piece_masks[bishop_piece]
        while bishop_squares:
            square_bit = bishop_squares & -bishop_squares
            square = square_bit.bit_length() - 1
            allowed_mask = pin_masks[square] & evasion_mask
            if allowed_mask:
                self._append_bishop_moves(result, square, allowed_mask, occupied, target_mask_base)
            bishop_squares ^= square_bit

        rook_squares = self.piece_masks[rook_piece]
        while rook_squares:
            square_bit = rook_squares & -rook_squares
            square = square_bit.bit_length() - 1
            allowed_mask = pin_masks[square] & evasion_mask
            if allowed_mask:
                self._append_rook_moves(result, square, allowed_mask, occupied, target_mask_base)
            rook_squares ^= square_bit

        queen_squares = self.piece_masks[queen_piece]
        while queen_squares:
            square_bit = queen_squares & -queen_squares
            square = square_bit.bit_length() - 1
            allowed_mask = pin_masks[square] & evasion_mask
            if allowed_mask:
                self._append_queen_moves(result, square, allowed_mask, occupied, target_mask_base)
            queen_squares ^= square_bit
        return result

    def _current_moves_codes(self, tactical_only: bool = False, stable_order: bool = False) -> list[int]:
        return self._fill_current_moves([], tactical_only=tactical_only, stable_order=stable_order)

    def _append_promotion_moves(self, result: list[int], from_index: int, to_index: int) -> None:
        result.append(_encode_move(from_index, to_index, 1))
        result.append(_encode_move(from_index, to_index, 2))
        result.append(_encode_move(from_index, to_index, 3))
        result.append(_encode_move(from_index, to_index, 4))

    def _append_en_passant_if_legal(self, result: list[int], from_index: int, target: int, color: int, enemy_color: int, king: int, occupied: int) -> None:
        captured_index = PAWN_EP_CAPTURE_SQUARES[color][target]
        if captured_index == -1:
            return
        moving_piece = self.board[from_index]
        captured_piece = self.board[captured_index]
        if captured_piece == EMPTY:
            return

        from_bit = 1 << from_index
        target_bit = 1 << target
        captured_bit = 1 << captured_index
        occupied_after = (occupied ^ from_bit ^ captured_bit) | target_bit

        self.board[from_index] = EMPTY
        self.board[captured_index] = EMPTY
        self.board[target] = moving_piece
        self.piece_masks[moving_piece] ^= from_bit | target_bit
        self.color_masks[color] ^= from_bit | target_bit
        self.piece_masks[captured_piece] ^= captured_bit
        self.color_masks[enemy_color] ^= captured_bit
        try:
            if king == -1 or not self._is_square_attacked_on_occupancy(king, enemy_color, occupied_after):
                result.append(_encode_move(from_index, target, 0))
        finally:
            self.color_masks[enemy_color] ^= captured_bit
            self.piece_masks[captured_piece] ^= captured_bit
            self.color_masks[color] ^= from_bit | target_bit
            self.piece_masks[moving_piece] ^= from_bit | target_bit
            self.board[target] = EMPTY
            self.board[captured_index] = captured_piece
            self.board[from_index] = moving_piece

    def _append_pawn_moves(self, result: list[int], from_index: int, color: int, tactical_only: bool, allowed_mask: int, occupied: int) -> None:
        board = self.board
        append_move = result.append
        ep = self.ep
        promotion_mask = PAWN_PROMOTION_MASKS[color]

        advance1 = PAWN_FORWARD_TARGETS[color][from_index]
        if advance1 != -1 and board[advance1] == EMPTY:
            advance1_bit = 1 << advance1
            if advance1_bit & allowed_mask:
                if promotion_mask[advance1]:
                    self._append_promotion_moves(result, from_index, advance1)
                elif not tactical_only:
                    append_move(_encode_move(from_index, advance1, 0))
                    advance2 = PAWN_DOUBLE_TARGETS[color][from_index]
                    if advance2 != -1 and board[advance2] == EMPTY and ((1 << advance2) & allowed_mask):
                        append_move(_encode_move(from_index, advance2, 0))

        enemy_color = _other_color(color)
        king = self.white_king if color == WHITE else self.black_king
        from_bit = 1 << from_index
        capture_a, capture_b = PAWN_CAPTURE_TARGETS[color][from_index]

        if capture_a != -1:
            target_bit = 1 << capture_a
            if target_bit & allowed_mask:
                target_piece = board[capture_a]
                if target_piece != EMPTY:
                    if PIECE_COLOR[target_piece] == enemy_color:
                        if promotion_mask[capture_a]:
                            self._append_promotion_moves(result, from_index, capture_a)
                        else:
                            append_move(_encode_move(from_index, capture_a, 0))
                elif capture_a == ep:
                    self._append_en_passant_if_legal(result, from_index, capture_a, color, enemy_color, king, occupied)

        if capture_b != -1:
            target_bit = 1 << capture_b
            if target_bit & allowed_mask:
                target_piece = board[capture_b]
                if target_piece != EMPTY:
                    if PIECE_COLOR[target_piece] == enemy_color:
                        if promotion_mask[capture_b]:
                            self._append_promotion_moves(result, from_index, capture_b)
                        else:
                            append_move(_encode_move(from_index, capture_b, 0))
                elif capture_b == ep:
                    self._append_en_passant_if_legal(result, from_index, capture_b, color, enemy_color, king, occupied)

    def _append_pawn_moves_unfiltered(self, result: list[int], from_index: int, color: int, tactical_only: bool, occupied: int) -> None:
        board = self.board
        append_move = result.append
        ep = self.ep
        promotion_mask = PAWN_PROMOTION_MASKS[color]

        advance1 = PAWN_FORWARD_TARGETS[color][from_index]
        if advance1 != -1 and board[advance1] == EMPTY:
            if promotion_mask[advance1]:
                self._append_promotion_moves(result, from_index, advance1)
            elif not tactical_only:
                append_move(_encode_move(from_index, advance1, 0))
                advance2 = PAWN_DOUBLE_TARGETS[color][from_index]
                if advance2 != -1 and board[advance2] == EMPTY:
                    append_move(_encode_move(from_index, advance2, 0))

        enemy_color = _other_color(color)
        king = self.white_king if color == WHITE else self.black_king
        capture_a, capture_b = PAWN_CAPTURE_TARGETS[color][from_index]

        if capture_a != -1:
            target_piece = board[capture_a]
            if target_piece != EMPTY:
                if PIECE_COLOR[target_piece] == enemy_color:
                    if promotion_mask[capture_a]:
                        self._append_promotion_moves(result, from_index, capture_a)
                    else:
                        append_move(_encode_move(from_index, capture_a, 0))
            elif capture_a == ep:
                self._append_en_passant_if_legal(result, from_index, capture_a, color, enemy_color, king, occupied)

        if capture_b != -1:
            target_piece = board[capture_b]
            if target_piece != EMPTY:
                if PIECE_COLOR[target_piece] == enemy_color:
                    if promotion_mask[capture_b]:
                        self._append_promotion_moves(result, from_index, capture_b)
                    else:
                        append_move(_encode_move(from_index, capture_b, 0))
            elif capture_b == ep:
                self._append_en_passant_if_legal(result, from_index, capture_b, color, enemy_color, king, occupied)

    def _append_knight_moves(self, result: list[int], from_index: int, color: int, tactical_only: bool, allowed_mask: int) -> None:
        append_move = result.append
        if tactical_only:
            targets = KNIGHT_ATTACK_MASKS[from_index] & self.color_masks[_other_color(color)] & allowed_mask
        else:
            targets = KNIGHT_ATTACK_MASKS[from_index] & ~self.color_masks[color] & allowed_mask
        while targets:
            target_bit = targets & -targets
            append_move(_encode_move(from_index, target_bit.bit_length() - 1, 0))
            targets ^= target_bit

    def _append_stable_knight_moves(self, result: list[int], from_index: int, color: int, tactical_only: bool, allowed_mask: int) -> None:
        append_move = result.append
        board = self.board
        friendly_mask = self.color_masks[color]
        for target in KNIGHT_TARGETS[from_index]:
            target_bit = 1 << target
            if not (target_bit & allowed_mask) or (target_bit & friendly_mask):
                continue
            if tactical_only and board[target] == EMPTY:
                continue
            append_move(_encode_move(from_index, target, 0))

    def _append_stable_slider_moves(self, result: list[int], from_index: int, directions: tuple[int, ...], allowed_mask: int, occupied: int, target_mask_base: int) -> None:
        append_move = result.append
        ray_masks = RAY_MASKS[from_index]
        ray_attacks = RAY_ATTACK_TABLES[from_index]
        for direction in directions:
            targets = ray_attacks[direction][occupied & ray_masks[direction]] & allowed_mask & target_mask_base
            while targets:
                target_bit = targets & -targets
                append_move(_encode_move(from_index, target_bit.bit_length() - 1, 0))
                targets ^= target_bit

    def _append_bishop_moves(self, result: list[int], from_index: int, allowed_mask: int, occupied: int, target_mask_base: int) -> None:
        append_move = result.append
        ray_masks = RAY_MASKS[from_index]
        ray_attacks = RAY_ATTACK_TABLES[from_index]
        targets = (
            ray_attacks[1][occupied & ray_masks[1]]
            | ray_attacks[3][occupied & ray_masks[3]]
            | ray_attacks[5][occupied & ray_masks[5]]
            | ray_attacks[7][occupied & ray_masks[7]]
            | ray_attacks[9][occupied & ray_masks[9]]
            | ray_attacks[11][occupied & ray_masks[11]]
        ) & allowed_mask & target_mask_base
        while targets:
            target_bit = targets & -targets
            append_move(_encode_move(from_index, target_bit.bit_length() - 1, 0))
            targets ^= target_bit

    def _append_rook_moves(self, result: list[int], from_index: int, allowed_mask: int, occupied: int, target_mask_base: int) -> None:
        append_move = result.append
        ray_masks = RAY_MASKS[from_index]
        ray_attacks = RAY_ATTACK_TABLES[from_index]
        targets = (
            ray_attacks[0][occupied & ray_masks[0]]
            | ray_attacks[2][occupied & ray_masks[2]]
            | ray_attacks[4][occupied & ray_masks[4]]
            | ray_attacks[6][occupied & ray_masks[6]]
            | ray_attacks[8][occupied & ray_masks[8]]
            | ray_attacks[10][occupied & ray_masks[10]]
        ) & allowed_mask & target_mask_base
        while targets:
            target_bit = targets & -targets
            append_move(_encode_move(from_index, target_bit.bit_length() - 1, 0))
            targets ^= target_bit

    def _append_queen_moves(self, result: list[int], from_index: int, allowed_mask: int, occupied: int, target_mask_base: int) -> None:
        append_move = result.append
        ray_masks = RAY_MASKS[from_index]
        ray_attacks = RAY_ATTACK_TABLES[from_index]
        targets = (
            ray_attacks[0][occupied & ray_masks[0]]
            | ray_attacks[1][occupied & ray_masks[1]]
            | ray_attacks[2][occupied & ray_masks[2]]
            | ray_attacks[3][occupied & ray_masks[3]]
            | ray_attacks[4][occupied & ray_masks[4]]
            | ray_attacks[5][occupied & ray_masks[5]]
            | ray_attacks[6][occupied & ray_masks[6]]
            | ray_attacks[7][occupied & ray_masks[7]]
            | ray_attacks[8][occupied & ray_masks[8]]
            | ray_attacks[9][occupied & ray_masks[9]]
            | ray_attacks[10][occupied & ray_masks[10]]
            | ray_attacks[11][occupied & ray_masks[11]]
        ) & allowed_mask & target_mask_base
        while targets:
            target_bit = targets & -targets
            append_move(_encode_move(from_index, target_bit.bit_length() - 1, 0))
            targets ^= target_bit

    def _is_square_attacked_on_occupancy(self, square: int, by_color: int, occupied: int) -> bool:
        board = self.board
        ray_masks = RAY_MASKS[square]
        ray_attacks = RAY_ATTACK_TABLES[square]
        enemy_pawns = self.piece_masks[WP if by_color == WHITE else BP]
        if enemy_pawns & PAWN_ATTACK_SOURCES[by_color][square]:
            return True
        enemy_king = self.piece_masks[WK if by_color == WHITE else BK]
        if enemy_king & KING_ATTACK_MASKS[square]:
            return True
        enemy_knights = self.piece_masks[WN if by_color == WHITE else BN]
        if enemy_knights & KNIGHT_ATTACK_MASKS[square]:
            return True

        hostile_bishops = self.piece_masks[WB if by_color == WHITE else BB]
        hostile_rooks = self.piece_masks[WR if by_color == WHITE else BR]
        hostile_queens = self.piece_masks[WQ if by_color == WHITE else BQ]
        diagonal_threats = hostile_bishops | hostile_queens
        orthogonal_threats = hostile_rooks | hostile_queens

        if diagonal_threats & DIAGONAL_LINE_MASKS[square]:
            bishop_piece = WB if by_color == WHITE else BB
            queen_piece = WQ if by_color == WHITE else BQ
            for direction in DIAGONAL_DIRECTIONS:
                blocker_bits = ray_attacks[direction][occupied & ray_masks[direction]] & occupied
                if not blocker_bits:
                    continue
                blocker_square = (blocker_bits & -blocker_bits).bit_length() - 1
                piece = board[blocker_square]
                if PIECE_COLOR[piece] == by_color and (piece == queen_piece or piece == bishop_piece):
                    return True

        if orthogonal_threats & ORTHOGONAL_LINE_MASKS[square]:
            rook_piece = WR if by_color == WHITE else BR
            queen_piece = WQ if by_color == WHITE else BQ
            for direction in ORTHOGONAL_DIRECTIONS:
                blocker_bits = ray_attacks[direction][occupied & ray_masks[direction]] & occupied
                if not blocker_bits:
                    continue
                blocker_square = (blocker_bits & -blocker_bits).bit_length() - 1
                piece = board[blocker_square]
                if PIECE_COLOR[piece] == by_color and (piece == queen_piece or piece == rook_piece):
                    return True

        return False

    def _append_king_moves(self, result: list[int], from_index: int, color: int, tactical_only: bool) -> None:
        append_move = result.append
        if tactical_only:
            targets = KING_ATTACK_MASKS[from_index] & self.color_masks[_other_color(color)]
        else:
            targets = KING_ATTACK_MASKS[from_index] & ~self.color_masks[color]
        occupied = self._occupied()
        enemy_color = _other_color(color)
        from_bit = 1 << from_index
        while targets:
            target_bit = targets & -targets
            target = target_bit.bit_length() - 1
            occupied_after = occupied ^ from_bit
            if not (occupied & target_bit):
                occupied_after |= target_bit
            if not self._is_square_attacked_on_occupancy(target, enemy_color, occupied_after):
                append_move(_encode_move(from_index, target, 0))
            targets ^= target_bit

    def _compute_legal_context(self, color: int, pin_masks: list[int] | None = None) -> LegalContext:
        king = self.find_king(color)
        if king is None:
            next_pin_masks = pin_masks if pin_masks is not None else [ALL_BOARD_MASK] * 91
            next_pin_masks[:] = ALL_PIN_MASKS
            return -1, 0, ALL_BOARD_MASK, next_pin_masks, False

        enemy_color = _other_color(color)
        occupied = self._occupied()
        board = self.board
        ray_masks = RAY_MASKS[king]
        ray_attacks = RAY_ATTACK_TABLES[king]
        check_count = 0
        evasion_mask = ALL_BOARD_MASK
        next_pin_masks = pin_masks if pin_masks is not None else [ALL_BOARD_MASK] * 91
        next_pin_masks[:] = ALL_PIN_MASKS
        has_pins = False

        pawn_attackers = self.piece_masks[WP if enemy_color == WHITE else BP] & PAWN_ATTACK_SOURCES[enemy_color][king]
        while pawn_attackers:
            attacker_bit = pawn_attackers & -pawn_attackers
            attacker = attacker_bit.bit_length() - 1
            check_count += 1
            if check_count == 1:
                evasion_mask = attacker_bit
            pawn_attackers ^= attacker_bit

        knight_attackers = self.piece_masks[WN if enemy_color == WHITE else BN] & KNIGHT_ATTACK_MASKS[king]
        while knight_attackers:
            attacker_bit = knight_attackers & -knight_attackers
            attacker = attacker_bit.bit_length() - 1
            check_count += 1
            if check_count == 1:
                evasion_mask = attacker_bit
            knight_attackers ^= attacker_bit

        king_attackers = self.piece_masks[WK if enemy_color == WHITE else BK] & KING_ATTACK_MASKS[king]
        while king_attackers:
            attacker_bit = king_attackers & -king_attackers
            attacker = attacker_bit.bit_length() - 1
            check_count += 1
            if check_count == 1:
                evasion_mask = attacker_bit
            king_attackers ^= attacker_bit

        bishop_piece = WB if enemy_color == WHITE else BB
        rook_piece = WR if enemy_color == WHITE else BR
        queen_piece = WQ if enemy_color == WHITE else BQ

        for direction in range(12):
            attack_mask = ray_attacks[direction][occupied & ray_masks[direction]]
            first_blocker_bits = attack_mask & occupied
            if not first_blocker_bits:
                continue
            first_blocker_bit = first_blocker_bits & -first_blocker_bits
            first_blocker = first_blocker_bit.bit_length() - 1
            first_piece = board[first_blocker]

            if PIECE_COLOR[first_piece] == color:
                occupied_without_first = occupied ^ first_blocker_bit
                xray_attack_mask = ray_attacks[direction][occupied_without_first & ray_masks[direction]]
                second_blocker_bits = xray_attack_mask & occupied_without_first
                if not second_blocker_bits:
                    continue
                second_blocker_bit = second_blocker_bits & -second_blocker_bits
                second_blocker = second_blocker_bit.bit_length() - 1
                second_piece = board[second_blocker]
                is_slider = second_piece == queen_piece
                if direction in ORTHOGONAL_DIRECTIONS:
                    is_slider = is_slider or second_piece == rook_piece
                else:
                    is_slider = is_slider or second_piece == bishop_piece
                if PIECE_COLOR[second_piece] == enemy_color and is_slider:
                    next_pin_masks[first_blocker] = xray_attack_mask
                    has_pins = True
                continue

            is_slider = first_piece == queen_piece
            if direction in ORTHOGONAL_DIRECTIONS:
                is_slider = is_slider or first_piece == rook_piece
            else:
                is_slider = is_slider or first_piece == bishop_piece

            if PIECE_COLOR[first_piece] == enemy_color and is_slider:
                check_count += 1
                if check_count == 1:
                    evasion_mask = attack_mask

        if check_count == 0:
            evasion_mask = ALL_BOARD_MASK
        elif check_count > 1:
            evasion_mask = 0

        return king, check_count, evasion_mask, next_pin_masks, has_pins

    def _legal_king_moves(self, from_index: int, moves: list[int], tactical_only: bool) -> list[int]:
        legal_moves: list[int] = []
        for move_code in moves:
            to_index = _move_to(move_code)
            if tactical_only and self.board[to_index] == EMPTY:
                continue
            undo = self.make_move_unsafe(move_code)
            king = self.find_king(_other_color(self.turn))
            if king is None or not self.is_square_attacked(king, self.turn):
                legal_moves.append(move_code)
            self.unmake_move(undo)
        return legal_moves

    def is_check(self) -> bool:
        king = self.find_king(self.turn)
        return False if king is None else self.is_square_attacked(king, _other_color(self.turn))

    def is_checkmate(self) -> bool:
        return self.is_check() and len(self._current_moves_codes()) == 0

    def is_stalemate(self) -> bool:
        return not self.is_check() and len(self._current_moves_codes()) == 0

    def is_legal(self, san: San | str) -> bool:
        move = San.from_value(san).encode()
        from_index = _move_from(move)
        piece = self.board[from_index]
        if piece == EMPTY or PIECE_COLOR[piece] != self.turn:
            return False
        return move in self._moves_from_codes(from_index)

    def is_square_attacked_by_pawn(self, square: int, by_color: Color | int) -> bool:
        color = _color_to_int(by_color)
        pawns = self.piece_masks[WP if color == WHITE else BP]
        return bool(pawns & PAWN_ATTACK_SOURCES[color][square])

    def is_square_attacked(self, square: int, by_color: Color | int) -> bool:
        color = _color_to_int(by_color)
        return self._is_square_attacked_on_occupancy(square, color, self._occupied())

    def moves_from(self, from_value: int | str) -> list[San]:
        from_index = index(from_value) if isinstance(from_value, str) else from_value
        legal_context = self._compute_legal_context(self.turn)
        return [San.from_code(move_code) for move_code in self._moves_from_codes(from_index, legal_context=legal_context)]

    def moves_from_unsafe(self, from_value: int | str) -> list[San]:
        from_index = index(from_value) if isinstance(from_value, str) else from_value
        return [San.from_code(move_code) for move_code in self._moves_from_unsafe_codes(from_index)]

    def _push_pawn_move(self, result: list[int], from_index: int, to_index: int, color: int) -> None:
        promotion_positions = WHITE_PROMOTION_POSITIONS if color == WHITE else BLACK_PROMOTION_POSITIONS
        if to_index in promotion_positions:
            result.append(_encode_move(from_index, to_index, 1))
            result.append(_encode_move(from_index, to_index, 2))
            result.append(_encode_move(from_index, to_index, 3))
            result.append(_encode_move(from_index, to_index, 4))
            return
        result.append(_encode_move(from_index, to_index, 0))

    def _moves_from_unsafe_codes(self, from_index: int, tactical_only: bool = False, piece: int | None = None) -> list[int]:
        piece = self.board[from_index] if piece is None else piece
        if piece == EMPTY:
            return []
        color = PIECE_COLOR[piece]
        friendly_mask = self.color_masks[color]
        lower = PIECE_KIND[piece]
        result: list[int] = []

        if lower == PAWN:
            if color == WHITE:
                forward, captures, starts = 0, (10, 2), WHITE_PAWN_STARTS
            else:
                forward, captures, starts = 6, (4, 8), BLACK_PAWN_STARTS
            advance1 = GRAPH[from_index][forward]
            if advance1 is not None and self.board[advance1] == EMPTY:
                if not tactical_only or advance1 in (WHITE_PROMOTION_POSITIONS if color == WHITE else BLACK_PROMOTION_POSITIONS):
                    self._push_pawn_move(result, from_index, advance1, color)
                if not tactical_only and from_index in starts:
                    advance2 = GRAPH[advance1][forward]
                    if advance2 is not None and self.board[advance2] == EMPTY:
                        result.append(_encode_move(from_index, advance2, 0))
            for direction in captures:
                target = GRAPH[from_index][direction]
                if target is None:
                    continue
                target_piece = self.board[target]
                if target_piece != EMPTY:
                    if PIECE_COLOR[target_piece] != color:
                        self._push_pawn_move(result, from_index, target, color)
                elif target == self.ep and self.turn == color:
                    self._push_pawn_move(result, from_index, target, color)
            return result

        if lower == KING:
            for target in _iter_bits(KING_ATTACK_MASKS[from_index]):
                if (_bit(target) & friendly_mask):
                    continue
                if not tactical_only or self.board[target] != EMPTY:
                    result.append(_encode_move(from_index, target, 0))
            return result

        if lower == KNIGHT:
            for target in _iter_bits(KNIGHT_ATTACK_MASKS[from_index]):
                if (_bit(target) & friendly_mask):
                    continue
                if not tactical_only or self.board[target] != EMPTY:
                    result.append(_encode_move(from_index, target, 0))
            return result

        occupied = self._occupied()
        directions = range(12) if lower == QUEEN else (1, 3, 5, 7, 9, 11) if lower == BISHOP else (0, 2, 4, 6, 8, 10)
        for direction in directions:
            ray_occupancy = self._occupied_on_ray(from_index, direction, occupied)
            if not ray_occupancy:
                if tactical_only:
                    continue
                for target, _, _ in RAY_SCANS[from_index][direction]:
                    result.append(_encode_move(from_index, target, 0))
                continue
            for target, target_bit, _ in RAY_SCANS[from_index][direction]:
                if not (ray_occupancy & target_bit):
                    if not tactical_only:
                        result.append(_encode_move(from_index, target, 0))
                    continue
                target_piece = self.board[target]
                if PIECE_COLOR[target_piece] != color:
                    result.append(_encode_move(from_index, target, 0))
                break
        return result

    def _moves_from_codes(self, from_index: int, tactical_only: bool = False, legal_context: LegalContext | None = None, piece: int | None = None) -> list[int]:
        piece = self.board[from_index] if piece is None else piece
        if piece == EMPTY:
            return []
        color = PIECE_COLOR[piece]
        if legal_context is None:
            legal_context = self._compute_legal_context(color)
        king, check_count, evasion_mask, pin_masks, _ = legal_context
        pseudo_moves = self._moves_from_unsafe_codes(from_index, tactical_only=tactical_only, piece=piece)

        if PIECE_KIND[piece] == KING:
            return self._legal_king_moves(from_index, pseudo_moves, tactical_only)

        if check_count > 1:
            return []

        pin_mask = pin_masks[from_index]
        legal_moves: list[int] = []
        for move_code in pseudo_moves:
            to_mask = _bit(_move_to(move_code))
            if not (to_mask & pin_mask):
                continue
            if not (to_mask & evasion_mask):
                continue

            if PIECE_KIND[piece] == PAWN and _move_to(move_code) == self.ep:
                undo = self.make_move_unsafe(move_code)
                current_king = self.find_king(color)
                if current_king is None or not self.is_square_attacked(current_king, _other_color(color)):
                    legal_moves.append(move_code)
                self.unmake_move(undo)
                continue

            legal_moves.append(move_code)
        return legal_moves

    def apply_move(self, san: San | str) -> 'Hexchess':
        if not self.is_legal(san):
            error(f'illegal move: {san}')
        return self.apply_move_unsafe(san)

    def apply_move_unsafe(self, san: San | str | int) -> 'Hexchess':
        self.make_move_unsafe(san)
        return self

    def make_move_unsafe(self, san: San | str | int) -> MoveUndo:
        move_code = san if isinstance(san, int) else San.from_value(san).encode()
        from_index = _move_from(move_code)
        to_index = _move_to(move_code)
        promotion_code = _move_promotion(move_code)
        piece = self.board[from_index]
        if piece == EMPTY:
            error(f'cannot apply move from empty position: {from_index}')

        target_piece = self.board[to_index]
        captured_index = -1
        captured_piece = target_piece
        previous_ep = self.ep
        previous_turn = self.turn
        previous_halfmove = self.halfmove
        previous_fullmove = self.fullmove
        previous_white_king = self.white_king
        previous_black_king = self.black_king
        previous_hash = self.zobrist_hash

        if self.ep != -1:
            self.zobrist_hash ^= ZOBRIST_EP[self.ep]

        if target_piece != EMPTY or PIECE_KIND[piece] == PAWN:
            self.halfmove = 0
        else:
            self.halfmove += 1

        if PIECE_COLOR[piece] == BLACK:
            self.fullmove += 1
            self.turn = WHITE
        else:
            self.turn = BLACK
        self.zobrist_hash ^= ZOBRIST_TURN

        self.zobrist_hash ^= _piece_hash(piece, from_index)
        self._remove_piece(from_index, piece)

        if target_piece != EMPTY:
            self.zobrist_hash ^= _piece_hash(target_piece, to_index)
            self._remove_piece(to_index, target_piece)

        if to_index == previous_ep and target_piece == EMPTY and PIECE_KIND[piece] == PAWN:
            captured_index = GRAPH[to_index][0] if piece == BP else GRAPH[to_index][6]
            if captured_index is not None:
                captured_piece = self.board[captured_index]
                if captured_piece != EMPTY:
                    self.zobrist_hash ^= _piece_hash(captured_piece, captured_index)
                    self._remove_piece(captured_index, captured_piece)
                else:
                    captured_index = -1
            else:
                captured_index = -1

        placed_piece = _promotion_piece(PIECE_COLOR[piece], promotion_code) if promotion_code else piece
        self._place_piece(to_index, placed_piece)
        self.zobrist_hash ^= _piece_hash(placed_piece, to_index)

        if piece == BP:
            self.ep = BLACK_EN_PASSANT_TARGETS.get((from_index, to_index), -1)
        elif piece == WP:
            self.ep = WHITE_EN_PASSANT_TARGETS.get((from_index, to_index), -1)
        else:
            self.ep = -1

        if self.ep != -1:
            self.zobrist_hash ^= ZOBRIST_EP[self.ep]

        return (
            move_code,
            piece,
            captured_piece,
            captured_index,
            previous_ep,
            previous_turn,
            previous_halfmove,
            previous_fullmove,
            previous_white_king,
            previous_black_king,
            previous_hash,
        )

    def unmake_move(self, undo: MoveUndo) -> None:
        move_code, moved_piece, captured_piece, captured_index, previous_ep, previous_turn, previous_halfmove, previous_fullmove, previous_white_king, previous_black_king, previous_hash = undo
        from_index = _move_from(move_code)
        to_index = _move_to(move_code)
        placed_piece = self.board[to_index]
        if placed_piece != EMPTY:
            self._remove_piece(to_index, placed_piece)
        self._place_piece(from_index, moved_piece)

        if captured_index != -1:
            self.board[to_index] = EMPTY
            if captured_piece != EMPTY:
                self._place_piece(captured_index, captured_piece)
        elif captured_piece != EMPTY:
            self._place_piece(to_index, captured_piece)

        self.ep = previous_ep
        self.turn = previous_turn
        self.halfmove = previous_halfmove
        self.fullmove = previous_fullmove
        self.white_king = previous_white_king
        self.black_king = previous_black_king
        self.zobrist_hash = previous_hash

    def make_null_move(self) -> NullMoveUndo:
        previous_ep = self.ep
        previous_turn = self.turn
        previous_halfmove = self.halfmove
        previous_fullmove = self.fullmove
        previous_hash = self.zobrist_hash

        if self.ep != -1:
            self.zobrist_hash ^= ZOBRIST_EP[self.ep]
            self.ep = -1

        self.halfmove += 1
        if self.turn == BLACK:
            self.fullmove += 1
            self.turn = WHITE
        else:
            self.turn = BLACK
        self.zobrist_hash ^= ZOBRIST_TURN

        return previous_ep, previous_turn, previous_halfmove, previous_fullmove, previous_hash

    def unmake_null_move(self, undo: NullMoveUndo) -> None:
        previous_ep, previous_turn, previous_halfmove, previous_fullmove, previous_hash = undo
        self.ep = previous_ep
        self.turn = previous_turn
        self.halfmove = previous_halfmove
        self.fullmove = previous_fullmove
        self.zobrist_hash = previous_hash

    def to_string(self) -> str:
        en_passant = '-' if self.ep == -1 else POSITIONS[self.ep]
        return f'{stringify_board(self.board)} {_color_to_char(self.turn)} {en_passant} {self.halfmove} {self.fullmove}'

    def __str__(self) -> str:
        return self.to_string()


def eval_pawn(index_value: int, color: Color | int, options: EvalOptions) -> float:
    bonuses = WHITE_ADVANCEMENT_BONUS_BY_INDEX if _color_to_int(color) == WHITE else BLACK_ADVANCEMENT_BONUS_BY_INDEX
    return options.pawn_value + bonuses[index_value]


def _pawn_attack_mask(mask: int, color: int) -> int:
    attack_mask = 0
    while mask:
        square_bit = mask & -mask
        attack_mask |= PAWN_ATTACK_TARGETS[color][square_bit.bit_length() - 1]
        mask ^= square_bit
    return attack_mask


def evaluate(hexchess: Hexchess, options: EvalOptions | None = None) -> float:
    evaluation_options = options or EvalOptions()
    piece_masks = hexchess.piece_masks
    score = 0.0

    white_pawns = piece_masks[WP]
    black_pawns = piece_masks[BP]
    score += (white_pawns.bit_count() - black_pawns.bit_count()) * evaluation_options.pawn_value
    white_pawn_mask = white_pawns
    while white_pawn_mask:
        square_bit = white_pawn_mask & -white_pawn_mask
        score += WHITE_ADVANCEMENT_BONUS_BY_INDEX[square_bit.bit_length() - 1]
        white_pawn_mask ^= square_bit
    black_pawn_mask = black_pawns
    while black_pawn_mask:
        square_bit = black_pawn_mask & -black_pawn_mask
        score -= BLACK_ADVANCEMENT_BONUS_BY_INDEX[square_bit.bit_length() - 1]
        black_pawn_mask ^= square_bit

    score += (piece_masks[WN].bit_count() - piece_masks[BN].bit_count()) * evaluation_options.knight_value
    score += (piece_masks[WB].bit_count() - piece_masks[BB].bit_count()) * evaluation_options.bishop_value
    score += (piece_masks[WR].bit_count() - piece_masks[BR].bit_count()) * evaluation_options.rook_value
    score += (piece_masks[WQ].bit_count() - piece_masks[BQ].bit_count()) * evaluation_options.queen_value
    score += (piece_masks[WK].bit_count() - piece_masks[BK].bit_count()) * evaluation_options.king_value

    white_pawn_attacks = _pawn_attack_mask(white_pawns, WHITE)
    black_pawn_attacks = _pawn_attack_mask(black_pawns, BLACK)

    threatened_white = (piece_masks[WN] | piece_masks[WB] | piece_masks[WR] | piece_masks[WQ]) & black_pawn_attacks
    threatened_white_mask = threatened_white
    while threatened_white_mask:
        square_bit = threatened_white_mask & -threatened_white_mask
        score -= PAWN_ATTACK_PENALTY[PIECE_KIND[hexchess.board[square_bit.bit_length() - 1]]]
        threatened_white_mask ^= square_bit

    threatened_black = (piece_masks[BN] | piece_masks[BB] | piece_masks[BR] | piece_masks[BQ]) & white_pawn_attacks
    threatened_black_mask = threatened_black
    while threatened_black_mask:
        square_bit = threatened_black_mask & -threatened_black_mask
        score += PAWN_ATTACK_PENALTY[PIECE_KIND[hexchess.board[square_bit.bit_length() - 1]]]
        threatened_black_mask ^= square_bit

    return score


def static_eval_for_turn(hexchess: Hexchess, options: EvalOptions) -> float:
    score = evaluate(hexchess, options)
    return score if hexchess.turn == WHITE else -score


TranspositionEntry = tuple[int, str, float, int | None]
RepetitionCounts = dict[int, int]


def _build_repetition_counts(position_history: list[str] | None) -> RepetitionCounts:
    counts: RepetitionCounts = {}
    if position_history is None:
        return counts
    for fen in position_history:
        key = Hexchess.parse(fen).position_key()
        counts[key] = counts.get(key, 0) + 1
    return counts


def _push_repetition_count(repetition_counts: RepetitionCounts, key: int) -> None:
    repetition_counts[key] = repetition_counts.get(key, 0) + 1


def _pop_repetition_count(repetition_counts: RepetitionCounts, key: int) -> None:
    count = repetition_counts.get(key, 0)
    if count <= 1:
        repetition_counts.pop(key, None)
        return
    repetition_counts[key] = count - 1


def _is_tactical_move(hexchess: Hexchess, move_code: int) -> bool:
    from_index = _move_from(move_code)
    to_index = _move_to(move_code)
    piece = hexchess.board[from_index]
    if piece == EMPTY:
        return False
    if _move_promotion(move_code):
        return True
    if hexchess.board[to_index] != EMPTY:
        return True
    return PIECE_KIND[piece] == PAWN and hexchess.ep == to_index


def _captured_piece_for_move(hexchess: Hexchess, move_code: int, piece: int | None = None) -> int:
    from_index = _move_from(move_code)
    to_index = _move_to(move_code)
    moving_piece = piece if piece is not None else hexchess.board[from_index]
    if moving_piece == EMPTY:
        return EMPTY

    captured_piece = hexchess.board[to_index]
    if captured_piece != EMPTY:
        return captured_piece

    if PIECE_KIND[moving_piece] != PAWN or hexchess.ep != to_index:
        return EMPTY

    captured_square = GRAPH[to_index][0] if moving_piece == BP else GRAPH[to_index][6]
    if captured_square is None:
        return EMPTY
    return hexchess.board[captured_square]


def _passes_qsearch_delta_prune(
    hexchess: Hexchess,
    move_code: int,
    stand_pat: float,
    alpha: float,
    tt_move: int | None,
    options: EvalOptions,
) -> bool:
    if move_code == tt_move:
        return True

    promotion_code = _move_promotion(move_code)
    if promotion_code:
        return True

    from_index = _move_from(move_code)
    piece = hexchess.board[from_index]
    if piece == EMPTY:
        return False

    captured_piece = _captured_piece_for_move(hexchess, move_code, piece)
    if captured_piece == EMPTY:
        return False

    # Conservative delta pruning: skip low-value tactical continuations that cannot
    # realistically raise alpha above the current stand-pat plus a small margin.
    delta_margin = (options.pawn_value * 2.0) + options.check_value
    optimistic_gain = PIECE_ORDER_VALUES[captured_piece]
    return stand_pat + optimistic_gain + delta_margin > alpha


def _has_non_pawn_material(hexchess: Hexchess, color: int) -> bool:
    if color == WHITE:
        return any(hexchess.piece_masks[piece] for piece in (WR, WN, WB, WQ))
    return any(hexchess.piece_masks[piece] for piece in (BR, BN, BB, BQ))


def _promote_move_to_front(moves: list[int], prioritized_move: int | None) -> None:
    if prioritized_move is None or len(moves) < 2:
        return
    try:
        move_index = moves.index(prioritized_move)
    except ValueError:
        return
    if move_index > 0:
        moves[0], moves[move_index] = moves[move_index], moves[0]


def store_transposition_entry(
    table: dict[int, TranspositionEntry],
    key: int,
    depth: int,
    flag: str,
    value: float,
    best_move: int | None,
) -> None:
    existing = table.get(key)
    if existing is not None and existing[0] > depth:
        return
    table[key] = (depth, flag, value, best_move)


def optimize_for_branch_pruning(hexchess: Hexchess, moves: list[int], depth: int, state: SearchState, tt_move: int | None = None) -> None:
    if len(moves) < 2:
        return
    board = hexchess.board
    ep = hexchess.ep
    history_scores = state.history_scores
    killer_a, killer_b = state.killer_moves_for(depth)

    def move_score(move_code: int) -> int:
        from_index = _move_from(move_code)
        to_index = _move_to(move_code)
        piece = board[from_index]
        if piece == EMPTY:
            return 0

        score = history_scores[move_code]
        moved_value = PIECE_ORDER_VALUES[piece]
        captured_piece = board[to_index]
        piece_kind = PIECE_KIND[piece]
        if captured_piece == EMPTY and piece_kind == PAWN and ep == to_index:
            captured_square = GRAPH[to_index][0] if piece == BP else GRAPH[to_index][6]
            if captured_square is not None:
                captured_piece = board[captured_square]
        if captured_piece != EMPTY:
            score += 10_000 + (PIECE_ORDER_VALUES[captured_piece] * 100) - moved_value
        promotion_code = _move_promotion(move_code)
        if promotion_code:
            score += PROMOTION_ORDER_BONUS[promotion_code]
        if piece_kind == PAWN and captured_piece == EMPTY:
            score += 5
        if move_code == killer_a or move_code == killer_b:
            score += 9_000
        return score

    moves.sort(key=move_score, reverse=True)
    _promote_move_to_front(moves, tt_move)


def optimize_tactical_moves(hexchess: Hexchess, moves: list[int], tt_move: int | None = None) -> None:
    if len(moves) < 2:
        return
    board = hexchess.board
    ep = hexchess.ep

    def move_score(move_code: int) -> int:
        from_index = _move_from(move_code)
        to_index = _move_to(move_code)
        piece = board[from_index]
        if piece == EMPTY:
            return 0

        captured_piece = board[to_index]
        if captured_piece == EMPTY and PIECE_KIND[piece] == PAWN and ep == to_index:
            captured_square = GRAPH[to_index][0] if piece == BP else GRAPH[to_index][6]
            if captured_square is not None:
                captured_piece = board[captured_square]

        score = 0
        if captured_piece != EMPTY:
            score += (PIECE_ORDER_VALUES[captured_piece] * 100) - PIECE_ORDER_VALUES[piece]

        promotion_code = _move_promotion(move_code)
        if promotion_code:
            score += PROMOTION_ORDER_BONUS[promotion_code]
        return score

    moves.sort(key=move_score, reverse=True)
    _promote_move_to_front(moves, tt_move)


def quiescence(
    hexchess: Hexchess,
    state: SearchState,
    table: dict[int, TranspositionEntry],
    repetition_counts: RepetitionCounts,
    ply: int,
    alpha: float,
    beta: float,
    evaluations: list[int],
    options: EvalOptions,
) -> float:
    state.quiescence_nodes += 1
    alpha_orig = alpha
    key = hexchess.position_key()
    if repetition_counts.get(key, 0) >= 2:
        return 0.0
    _push_repetition_count(repetition_counts, key)
    try:
        entry = table.get(key)
        tt_move = entry[3] if entry is not None else None
        if entry is not None:
            state.tt_hits += 1
            if state.diagnostics_enabled:
                state.quiescence_tt_hits += 1
            entry_depth, flag, value, _ = entry
            if entry_depth >= 0:
                if flag == 'exact':
                    state.tt_cutoffs += 1
                    if state.diagnostics_enabled:
                        state.quiescence_tt_cutoffs += 1
                    return value
                if flag == 'lower' and value >= beta:
                    state.tt_cutoffs += 1
                    if state.diagnostics_enabled:
                        state.quiescence_tt_cutoffs += 1
                    return value
                if flag == 'upper' and value <= alpha:
                    state.tt_cutoffs += 1
                    if state.diagnostics_enabled:
                        state.quiescence_tt_cutoffs += 1
                    return value

        evaluations[0] += 1
        stand_pat = static_eval_for_turn(hexchess, options)
        if stand_pat >= beta:
            if state.diagnostics_enabled:
                state.qsearch_stand_pat_cutoffs += 1
            store_transposition_entry(table, key, 0, 'lower', stand_pat, tt_move)
            return stand_pat
        if stand_pat > alpha:
            alpha = stand_pat
        tactical_moves = hexchess._fill_current_moves(state.buffer_for(ply), tactical_only=True, pin_masks=state.pin_masks_for(ply), stats=state)
        if not tactical_moves:
            return stand_pat
        if state.diagnostics_enabled:
            state.qsearch_nodes_with_moves += 1
            state.qsearch_generated_moves += len(tactical_moves)
        optimize_tactical_moves(hexchess, tactical_moves, tt_move)
        value = stand_pat
        best_move: int | None = None
        delta_prune_active = alpha > stand_pat + options.rook_value + options.check_value
        in_check = hexchess.is_check() if delta_prune_active else False
        for move_code in tactical_moves:
            if delta_prune_active and not in_check:
                if state.diagnostics_enabled:
                    state.qsearch_delta_prune_checks += 1
                if not _passes_qsearch_delta_prune(hexchess, move_code, stand_pat, alpha, tt_move, options):
                    if state.diagnostics_enabled:
                        state.qsearch_delta_prune_skips += 1
                    continue
            undo = hexchess.make_move_unsafe(move_code)
            child_value = -quiescence(hexchess, state, table, repetition_counts, ply + 1, -beta, -alpha, evaluations, options)
            hexchess.unmake_move(undo)
            if child_value >= beta:
                state.beta_cutoffs += 1
                if state.diagnostics_enabled:
                    state.quiescence_beta_cutoffs += 1
                store_transposition_entry(table, key, 0, 'lower', child_value, move_code)
                return child_value
            if child_value > value:
                value = child_value
                best_move = move_code
            if child_value > alpha:
                alpha = child_value
        flag = 'exact'
        if value <= alpha_orig:
            flag = 'upper'
        elif value >= beta:
            flag = 'lower'
        store_transposition_entry(table, key, 0, flag, value, best_move)
        return value
    finally:
        _pop_repetition_count(repetition_counts, key)


def negamax(
    state: SearchState,
    table: dict[int, TranspositionEntry],
    repetition_counts: RepetitionCounts,
    hexchess: Hexchess,
    depth: int,
    ply: int,
    alpha: float,
    beta: float,
    evaluations: list[int],
    options: EvalOptions,
) -> float:
    null_move_reduction = 2
    state.negamax_nodes += 1
    alpha_orig = alpha
    key = hexchess.position_key()
    if repetition_counts.get(key, 0) >= 2:
        return 0.0
    _push_repetition_count(repetition_counts, key)
    try:
        in_check = False
        entry = table.get(key)
        tt_move = entry[3] if entry is not None else None
        if entry is not None:
            state.tt_hits += 1
            if state.diagnostics_enabled:
                state.negamax_tt_hits += 1
            entry_depth, flag, value, _ = entry
            if entry_depth >= depth:
                if flag == 'exact':
                    state.tt_cutoffs += 1
                    if state.diagnostics_enabled:
                        state.negamax_tt_cutoffs += 1
                    return value
                if flag == 'lower' and value >= beta:
                    state.tt_cutoffs += 1
                    if state.diagnostics_enabled:
                        state.negamax_tt_cutoffs += 1
                    return value
                if flag == 'upper' and value <= alpha:
                    state.tt_cutoffs += 1
                    if state.diagnostics_enabled:
                        state.negamax_tt_cutoffs += 1
                    return value
        if depth >= null_move_reduction + 1 or depth == 0:
            in_check = hexchess.is_check()
        if depth == 0 and not in_check:
            return quiescence(hexchess, state, table, repetition_counts, ply, alpha, beta, evaluations, options)
        if depth >= null_move_reduction + 1 and beta != float('inf') and not in_check and _has_non_pawn_material(hexchess, hexchess.turn):
            static_eval = static_eval_for_turn(hexchess, options)
            if static_eval >= beta:
                if state.diagnostics_enabled:
                    state.null_move_attempts += 1
                undo = hexchess.make_null_move()
                null_value = -negamax(
                    state,
                    table,
                    repetition_counts,
                    hexchess,
                    depth - null_move_reduction - 1,
                    ply + 1,
                    -beta,
                    -beta + 1,
                    evaluations,
                    options,
                )
                hexchess.unmake_null_move(undo)
                if null_value >= beta:
                    if state.diagnostics_enabled:
                        state.null_move_cutoffs += 1
                    return null_value
        current_moves = hexchess._fill_current_moves(state.buffer_for(ply), tactical_only=False, pin_masks=state.pin_masks_for(ply), stats=state)
        if not current_moves:
            evaluations[0] += 1
            if in_check or hexchess.is_check():
                return options.checkmate_value if hexchess.turn == WHITE else -options.checkmate_value
            return options.stalemate_value if hexchess.turn == WHITE else -options.stalemate_value
        if depth <= 0:
            return quiescence(hexchess, state, table, repetition_counts, ply, alpha, beta, evaluations, options)
        optimize_for_branch_pruning(hexchess, current_moves, ply, state, tt_move)
        frontier_futility_enabled = depth == 1
        frontier_futility_checked = False
        frontier_futility_ready = False
        frontier_stand_pat = 0.0
        frontier_margin = options.rook_value + options.check_value
        value = float('-inf')
        best_move: int | None = None
        for move_index, move_code in enumerate(current_moves):
            if (
                frontier_futility_enabled
                and move_index > 0
                and move_code != tt_move
                and not _is_tactical_move(hexchess, move_code)
            ):
                if not frontier_futility_checked:
                    frontier_futility_checked = True
                    if not in_check:
                        in_check = hexchess.is_check()
                    if not in_check:
                        frontier_stand_pat = static_eval_for_turn(hexchess, options)
                        frontier_futility_ready = True
                if frontier_futility_ready:
                    if state.diagnostics_enabled:
                        state.negamax_frontier_futility_checks += 1
                    if alpha >= frontier_stand_pat + frontier_margin:
                        if state.diagnostics_enabled:
                            state.negamax_frontier_futility_skips += 1
                        continue
            undo = hexchess.make_move_unsafe(move_code)
            if move_index == 0:
                child_value = -negamax(state, table, repetition_counts, hexchess, depth - 1, ply + 1, -beta, -alpha, evaluations, options)
            else:
                child_value = -negamax(state, table, repetition_counts, hexchess, depth - 1, ply + 1, -alpha - 1, -alpha, evaluations, options)
                if child_value > alpha and child_value < beta:
                    if state.diagnostics_enabled:
                        state.pvs_researches += 1
                    child_value = -negamax(state, table, repetition_counts, hexchess, depth - 1, ply + 1, -beta, -alpha, evaluations, options)
            hexchess.unmake_move(undo)
            if child_value > value:
                value = child_value
                best_move = move_code
            alpha = max(alpha, value)
            if alpha >= beta:
                state.beta_cutoffs += 1
                if state.diagnostics_enabled:
                    state.negamax_beta_cutoffs += 1
                if not _is_tactical_move(hexchess, move_code):
                    state.record_killer(ply, move_code)
                    state.history_scores[move_code] += depth * depth
                best_move = move_code
                break
        flag = 'exact'
        if value <= alpha_orig:
            flag = 'upper'
        elif value >= beta:
            flag = 'lower'
        store_transposition_entry(table, key, depth, flag, value, best_move)
        return value
    finally:
        _pop_repetition_count(repetition_counts, key)


def search(
    hexchess: Hexchess,
    depth: int,
    options: EvalOptions | None = None,
    *,
    diagnostics: bool = True,
    position_history: list[str] | None = None,
) -> dict[str, object]:
    if depth < 1:
        error(f'invalid depth: {depth}')
    started_at = time.perf_counter()
    root_key = hexchess.position_key()
    evaluation_options = options or EvalOptions()
    table: dict[int, TranspositionEntry] = {}
    repetition_counts = _build_repetition_counts(position_history)
    evaluations = [0]
    state = SearchState(diagnostics_enabled=diagnostics)
    sans: list[dict[str, object]] = []
    root_moves = hexchess._fill_current_moves(state.buffer_for(0), tactical_only=False, pin_masks=state.pin_masks_for(0), stats=state)
    optimize_for_branch_pruning(hexchess, root_moves, 0, state)
    _push_repetition_count(repetition_counts, root_key)
    try:
        for move_code in root_moves:
            undo = hexchess.make_move_unsafe(move_code)
            score = negamax(state, table, repetition_counts, hexchess, depth - 1, 1, float('-inf'), float('inf'), evaluations, evaluation_options)
            hexchess.unmake_move(undo)
            sans.append({'san': str(San.from_code(move_code)), 'score': score})
    finally:
        _pop_repetition_count(repetition_counts, root_key)
    sans.sort(key=lambda item: item['score'])
    wall_ms = (time.perf_counter() - started_at) * 1000.0
    return {
        'depth': depth,
        'evaluations': evaluations[0],
        'sans': sans,
        'metrics': state.metrics_dict(len(root_moves), wall_ms, evaluations[0], len(table)),
    }


def ping_response() -> dict[str, int]:
    return {'now': int(time.time() * 1000)}


def execute_command(command: str, options: dict[str, object] | None = None) -> dict[str, object]:
    command_options = options or {}
    if command == 'hexchess/ping':
        return ping_response()
    if command == 'hexchess/evaluate':
        position = command_options.get('position')
        depth = command_options.get('depth')
        position_history = command_options.get('positionHistory')
        if not isinstance(position, str):
            error('invalid position: expected string')
        if not isinstance(depth, int):
            error('invalid depth: expected integer')
        if position_history is not None:
            if not isinstance(position_history, list) or any(not isinstance(item, str) for item in position_history):
                error('invalid positionHistory: expected list of strings')
        diagnostics = command_options.get('diagnostics', True)
        if not isinstance(diagnostics, bool):
            error('invalid diagnostics: expected boolean')
        return search(Hexchess.parse(position), depth, diagnostics=diagnostics, position_history=position_history)
    error(f'Unknown engine command: {command}')
from __future__ import annotations

cimport cython

import re
import time
from random import Random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


Color = Literal['w', 'b']
Direction = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
Piece = Literal['p', 'r', 'n', 'b', 'q', 'k', 'P', 'R', 'N', 'B', 'Q', 'K']
PromotionPiece = Literal['q', 'r', 'b', 'n']
Board = list[Piece | None]

ROOT_DIR = Path(__file__).resolve().parent.parent
CONSTANTS_PATH = ROOT_DIR / 'js' / 'src' / 'constants.ts'
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
KNIGHT_TARGETS = (
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


class NativeEngineError(ValueError):
    pass


def error(message: str) -> None:
    raise NativeEngineError(f'[hexchess error] {message}')


def _extract_exported_array(source: str, name: str) -> str:
    match = re.search(rf'export const {name} = (\[.*?\]) as const', source, flags=re.DOTALL)
    if not match:
        error(f'failed to load constant: {name}')
    return match.group(1)


def _extract_exported_string(source: str, name: str) -> str:
    match = re.search(rf"export const {name} = '([^']+)'", source)
    if not match:
        error(f'failed to load constant: {name}')
    return match.group(1)


def _strip_comments(source: str) -> str:
    without_block_comments = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    return re.sub(r'//.*', '', without_block_comments)


def _parse_sparse_array(source: str) -> list[object]:
    stack: list[dict[str, object]] = []
    root: list[object] | None = None
    i = 0

    while i < len(source):
        current = source[i]

        if current.isspace():
            i += 1
            continue

        if current == '[':
            arr: list[object] = []
            if stack:
                stack[-1]['arr'].append(arr)
                stack[-1]['last'] = 'value'
            else:
                root = arr
            stack.append({'arr': arr, 'last': '['})
            i += 1
            continue

        if current == ']':
            if not stack:
                error('failed to parse constants graph: unexpected closing bracket')
            stack.pop()
            i += 1
            continue

        if current == ',':
            if not stack:
                error('failed to parse constants graph: unexpected comma')
            if stack[-1]['last'] in {'[', ','}:
                stack[-1]['arr'].append(None)
            stack[-1]['last'] = ','
            i += 1
            continue

        if current.isdigit():
            if not stack:
                error('failed to parse constants graph: number outside array')
            j = i
            while j < len(source) and source[j].isdigit():
                j += 1
            stack[-1]['arr'].append(int(source[i:j]))
            stack[-1]['last'] = 'value'
            i = j
            continue

        if current in {"'", '"'}:
            if not stack:
                error('failed to parse constants graph: string outside array')
            quote = current
            j = i + 1
            while j < len(source) and source[j] != quote:
                j += 1
            if j >= len(source):
                error('failed to parse constants graph: unterminated string')
            stack[-1]['arr'].append(source[i + 1:j])
            stack[-1]['last'] = 'value'
            i = j + 1
            continue

        error(f'failed to parse constants graph: unexpected token {current}')

    if stack or root is None:
        error('failed to parse constants graph: unbalanced array')

    return root


def _load_constants() -> tuple[tuple[tuple[int | None, ...], ...], tuple[str, ...], str, str]:
    source = CONSTANTS_PATH.read_text(encoding='utf-8')
    graph_source = _strip_comments(_extract_exported_array(source, 'graph'))
    graph_raw = _parse_sparse_array(graph_source)
    positions = tuple(re.findall(r"'([^']+)'", _extract_exported_array(source, 'positions')))
    empty_position = _extract_exported_string(source, 'emptyPosition')
    initial_position = _extract_exported_string(source, 'initialPosition')

    graph = tuple(tuple(value if isinstance(value, int) else None for value in row) for row in graph_raw)

    if len(graph) != 91 or any(len(row) != 12 for row in graph):
        error('failed to load board graph')

    if len(positions) != 91:
        error('failed to load board positions')

    return graph, positions, empty_position, initial_position


GRAPH, POSITIONS, EMPTY_POSITION, INITIAL_POSITION = _load_constants()
POSITION_TO_INDEX = {position: index for index, position in enumerate(POSITIONS)}
_knight_attack_sources: list[set[int]] = [set() for _ in range(91)]
for source in range(91):
    for diagonal, orthogonal1, orthogonal2 in KNIGHT_TARGETS:
        intermediate = GRAPH[source][diagonal]
        if intermediate is None:
            continue

        first = GRAPH[intermediate][orthogonal1]
        second = GRAPH[intermediate][orthogonal2]

        if first is not None:
            _knight_attack_sources[first].add(source)
        if second is not None:
            _knight_attack_sources[second].add(source)
KNIGHT_ATTACK_SOURCES = tuple(tuple(sorted(sources)) for sources in _knight_attack_sources)
_zobrist_random = Random(0)
ZOBRIST_PIECES = tuple(
    tuple(_zobrist_random.getrandbits(64) for _ in range(91))
    for _ in range(12)
)
ZOBRIST_TURN = _zobrist_random.getrandbits(64)
ZOBRIST_EP = tuple(_zobrist_random.getrandbits(64) for _ in range(91))
WHITE_ADVANCEMENT_BONUS = {
    POSITION_TO_INDEX[name]: scalar * scalar * 2.0
    for name, scalar in WHITE_ADVANCEMENT_SCALARS.items()
}
BLACK_ADVANCEMENT_BONUS = {
    POSITION_TO_INDEX[name]: scalar * scalar * 2.0
    for name, scalar in BLACK_ADVANCEMENT_SCALARS.items()
}
PIECE_VALUES = {
    'p': 10,
    'n': 30,
    'b': 30,
    'r': 50,
    'q': 90,
    'k': 0,
}
PAWN_ATTACK_PENALTY = {
    'n': 8.0,
    'b': 8.0,
    'r': 12.0,
    'q': 20.0,
}
PROMOTION_ORDER_BONUS = {
    'q': 1000,
    'r': 800,
    'b': 700,
    'n': 700,
}
PROMOTION_TO_CODE = {
    None: 0,
    'b': 1,
    'n': 2,
    'q': 3,
    'r': 4,
}
CODE_TO_PROMOTION = (None, 'b', 'n', 'q', 'r')
PIECE_TO_ZOBRIST_INDEX = {
    'p': 0,
    'r': 1,
    'n': 2,
    'b': 3,
    'q': 4,
    'k': 5,
    'P': 6,
    'R': 7,
    'N': 8,
    'B': 9,
    'Q': 10,
    'K': 11,
}


cdef inline str _piece_color(object piece):
    return 'b' if (<str>piece).islower() else 'w'


cdef inline int _encode_move(int from_index, int to_index, object promotion):
    return (from_index << 10) | (to_index << 3) | PROMOTION_TO_CODE[promotion]


cdef inline int _move_from_code(int move_code):
    return (move_code >> 10) & 0x7F


cdef inline int _move_to_code(int move_code):
    return (move_code >> 3) & 0x7F


cdef inline object _move_promotion_from_code(int move_code):
    return CODE_TO_PROMOTION[move_code & 0x7]


cdef inline str _move_string(int move_code):
    cdef object promotion = _move_promotion_from_code(move_code)
    return f'{POSITIONS[_move_from_code(move_code)]}{POSITIONS[_move_to_code(move_code)]}{promotion or ""}'


cdef inline object _san_from_code(int move_code):
    return San(_move_from_code(move_code), _move_to_code(move_code), _move_promotion_from_code(move_code))


def piece_color(piece: Piece) -> Color:
    return _piece_color(piece)


cdef inline object _piece_hash(object piece, int square):
    return ZOBRIST_PIECES[PIECE_TO_ZOBRIST_INDEX[piece]][square]


def piece_hash(piece: Piece, square: int) -> int:
    return _piece_hash(piece, square)


def compute_zobrist_hash(board: Board, turn: Color, ep: int | None) -> int:
    cdef int square
    cdef object piece
    value = 0

    for square, piece in enumerate(board):
        if piece is not None:
            value ^= _piece_hash(piece, square)

    if turn == 'b':
        value ^= ZOBRIST_TURN

    if ep is not None:
        value ^= ZOBRIST_EP[ep]

    return value


def index(position: str) -> int:
    try:
        return POSITION_TO_INDEX[position]
    except KeyError as exc:
        error(f'invalid position: {position}')
        raise exc


def is_position(source: str) -> bool:
    return source in POSITION_TO_INDEX


cdef inline object _step(int from_index, int direction):
    return GRAPH[from_index][direction]


def step(from_index: int, direction: Direction) -> int | None:
    return _step(from_index, direction)


cdef inline int _reverse_direction(int direction):
    return (direction + 6) % 12


def reverse_direction(direction: int) -> int:
    return _reverse_direction(direction)


cdef inline str _other_color(str color):
    return 'b' if color == 'w' else 'w'


def other_color(color: Color) -> Color:
    return _other_color(color)


cdef inline bint _is_promotion_position(int position, str color):
    cdef object positions = WHITE_PROMOTION_POSITIONS if color == 'w' else BLACK_PROMOTION_POSITIONS
    return position in positions


def is_promotion_position(position: int, color: Color) -> bool:
    return _is_promotion_position(position, color)


cdef inline bint _is_target(object hexchess, object position, str color):
    if position is None:
        return False

    cdef object piece = hexchess.board[position]
    return piece is None or _piece_color(piece) != color


def is_target(hexchess: 'Hexchess', position: int | None, color: Color) -> bool:
    return _is_target(hexchess, position, color)


cdef list _walk(object hexchess, int from_index, int direction, str color):
    cdef list path = []
    cdef int position = from_index
    cdef object next_position
    cdef object piece

    while True:
        next_position = _step(position, direction)
        if next_position is None:
            return path

        position = next_position
        piece = hexchess.board[position]

        if piece is None:
            path.append(position)
            continue

        if _piece_color(piece) == color:
            return path

        path.append(position)
        return path


def walk(hexchess: 'Hexchess', from_index: int, direction: Direction, color: Color) -> list[int]:
    return _walk(hexchess, from_index, direction, color)


cdef inline bint _is_square_attacked_by_pawn(object hexchess, int square, str by_color):
    cdef int direction
    cdef object source
    cdef str pawn_piece = 'P' if by_color == 'w' else 'p'
    cdef tuple pawn_directions = (_reverse_direction(10), _reverse_direction(2)) if by_color == 'w' else (_reverse_direction(4), _reverse_direction(8))

    for direction in pawn_directions:
        source = _step(square, direction)
        if source is not None and hexchess.board[source] == pawn_piece:
            return True

    return False


cdef bint _is_square_attacked(object hexchess, int square, str by_color):
    cdef int direction
    cdef object source
    cdef object position
    cdef object piece
    cdef str pawn_piece = 'P' if by_color == 'w' else 'p'
    cdef tuple pawn_directions = (_reverse_direction(10), _reverse_direction(2)) if by_color == 'w' else (_reverse_direction(4), _reverse_direction(8))
    cdef str king_piece = 'K' if by_color == 'w' else 'k'
    cdef str knight_piece = 'N' if by_color == 'w' else 'n'
    cdef str bishop_piece = 'B' if by_color == 'w' else 'b'
    cdef str rook_piece = 'R' if by_color == 'w' else 'r'
    cdef str queen_piece = 'Q' if by_color == 'w' else 'q'

    for direction in pawn_directions:
        source = _step(square, direction)
        if source is not None and hexchess.board[source] == pawn_piece:
            return True

    for direction in range(12):
        source = _step(square, direction)
        if source is not None and hexchess.board[source] == king_piece:
            return True

    for source in KNIGHT_ATTACK_SOURCES[square]:
        if hexchess.board[source] == knight_piece:
            return True

    for direction in range(12):
        position = square
        while True:
            position = _step(position, direction)
            if position is None:
                break

            piece = hexchess.board[position]
            if piece is None:
                continue

            if _piece_color(piece) != by_color:
                break

            if piece == queen_piece:
                return True
            if direction in ORTHOGONAL_DIRECTIONS and piece == rook_piece:
                return True
            if direction in DIAGONAL_DIRECTIONS and piece == bishop_piece:
                return True
            break

    return False


cdef inline void _push_pawn_move_c(list result, object san, str color):
    if _is_promotion_position(san.to_index, color):
        result.append(_encode_move(san.from_index, san.to_index, 'b'))
        result.append(_encode_move(san.from_index, san.to_index, 'n'))
        result.append(_encode_move(san.from_index, san.to_index, 'q'))
        result.append(_encode_move(san.from_index, san.to_index, 'r'))
        return

    result.append(_encode_move(san.from_index, san.to_index, None))


cdef inline object _pawn_advance_c(object hexchess, int start, int from_index, int forward):
    cdef object to_index = _step(from_index, forward)
    if to_index is None:
        return None
    return San(start, to_index) if hexchess.board[to_index] is None else None


cdef inline object _pawn_capture_c(object hexchess, int from_index, int direction, str friendly):
    cdef object to_index = _step(from_index, direction)
    cdef object target
    if to_index is None:
        return None

    target = hexchess.board[to_index]
    if target is not None:
        if _piece_color(target) != friendly:
            return San(from_index, to_index)
    elif hexchess.ep == to_index and hexchess.turn == friendly:
        return San(from_index, to_index)

    return None


cdef list _pawn_moves_unsafe(object hexchess, int from_index, str color):
    cdef list result = []
    cdef int forward
    cdef int portside
    cdef int starboard
    cdef object advance1
    cdef object advance2
    cdef object capture
    cdef int direction
    cdef object starting_positions

    if color == 'w':
        forward, portside, starboard = 0, 10, 2
        starting_positions = WHITE_PAWN_STARTS
    else:
        forward, portside, starboard = 6, 4, 8
        starting_positions = BLACK_PAWN_STARTS

    advance1 = _pawn_advance_c(hexchess, from_index, from_index, forward)
    if advance1 is not None:
        _push_pawn_move_c(result, advance1, color)
        if from_index in starting_positions:
            advance2 = _pawn_advance_c(hexchess, from_index, advance1.to_index, forward)
            if advance2 is not None:
                result.append(_encode_move(advance2.from_index, advance2.to_index, None))

    for direction in (portside, starboard):
        capture = _pawn_capture_c(hexchess, from_index, direction, color)
        if capture is not None:
            _push_pawn_move_c(result, capture, color)

    return result


cdef list _king_moves_unsafe(object hexchess, int from_index, str color):
    cdef list result = []
    cdef int direction
    cdef object to_index

    for direction in range(12):
        to_index = _step(from_index, direction)
        if _is_target(hexchess, to_index, color):
            result.append(_encode_move(from_index, to_index, None))

    return result


cdef list _knight_moves_unsafe(object hexchess, int from_index, str color):
    cdef list result = []
    cdef object intermediate
    cdef object first
    cdef object second
    cdef int diagonal
    cdef int orthogonal1
    cdef int orthogonal2

    for diagonal, orthogonal1, orthogonal2 in KNIGHT_TARGETS:
        intermediate = _step(from_index, diagonal)
        if intermediate is None:
            continue

        first = _step(intermediate, orthogonal1)
        second = _step(intermediate, orthogonal2)

        if _is_target(hexchess, first, color):
            result.append(_encode_move(from_index, first, None))
        if _is_target(hexchess, second, color):
            result.append(_encode_move(from_index, second, None))

    return result


cdef list _straight_line_moves_unsafe(object hexchess, int from_index, str color, object directions):
    cdef list result = []
    cdef int direction
    cdef object to_index

    for direction in directions:
        for to_index in _walk(hexchess, from_index, direction, color):
            result.append(_encode_move(from_index, to_index, None))

    return result


cdef list _moves_from_unsafe(object hexchess, int from_index):
    cdef object piece = hexchess.board[from_index]
    cdef str color
    cdef str lower

    if piece is None:
        return []

    color = _piece_color(piece)
    lower = (<str>piece).lower()

    if lower == 'b':
        return _straight_line_moves_unsafe(hexchess, from_index, color, (1, 3, 5, 7, 9, 11))
    if lower == 'k':
        return _king_moves_unsafe(hexchess, from_index, color)
    if lower == 'n':
        return _knight_moves_unsafe(hexchess, from_index, color)
    if lower == 'p':
        return _pawn_moves_unsafe(hexchess, from_index, color)
    if lower == 'q':
        return _straight_line_moves_unsafe(hexchess, from_index, color, range(12))
    return _straight_line_moves_unsafe(hexchess, from_index, color, (0, 2, 4, 6, 8, 10))


cdef list _moves_from(object hexchess, int from_index):
    cdef object piece = hexchess.board[from_index]
    cdef str color
    cdef list legal_moves
    cdef int move_code
    cdef object undo
    cdef object king

    if piece is None:
        return []

    color = _piece_color(piece)
    legal_moves = []

    for move_code in _moves_from_unsafe(hexchess, from_index):
        undo = _make_move_unsafe(hexchess, move_code)
        king = hexchess.find_king(color)
        if king is None or not _is_square_attacked(hexchess, king, _other_color(color)):
            legal_moves.append(move_code)
        _unmake_move(hexchess, undo)

    return legal_moves


cdef list _current_moves(object hexchess):
    cdef list result = []
    cdef int board_index

    for board_index in sorted(hexchess.white_pieces if hexchess.turn == 'w' else hexchess.black_pieces):
        result.extend(_moves_from(hexchess, board_index))

    return result


cdef object _make_move_unsafe(object hexchess, object san):
    cdef int from_index
    cdef int to_index
    cdef object promotion
    cdef object piece
    cdef object moving_piece_list
    cdef object enemy_piece_list
    cdef object target_piece
    cdef object undo
    cdef str color
    cdef object captured_piece
    cdef object captured_index = None
    cdef object captured
    cdef object placed_piece

    if isinstance(san, int):
        from_index = _move_from_code(san)
        to_index = _move_to_code(san)
        promotion = _move_promotion_from_code(san)
    else:
        san = San.from_value(san)
        from_index = san.from_index
        to_index = san.to_index
        promotion = san.promotion

    piece = hexchess.board[from_index]
    if piece is None:
        error(f'cannot apply move from empty position: {from_index}')

    moving_piece_list = hexchess.white_pieces if piece.isupper() else hexchess.black_pieces
    enemy_piece_list = hexchess.black_pieces if piece.isupper() else hexchess.white_pieces

    target_piece = hexchess.board[to_index]
    undo = MoveUndo(
        from_index=from_index,
        to_index=to_index,
        promotion=promotion,
        moved_piece=piece,
        captured_piece=target_piece,
        captured_index=None,
        previous_ep=hexchess.ep,
        previous_turn=hexchess.turn,
        previous_halfmove=hexchess.halfmove,
        previous_fullmove=hexchess.fullmove,
        previous_white_king=hexchess.white_king,
        previous_black_king=hexchess.black_king,
        previous_hash=hexchess.zobrist_hash,
    )

    if hexchess.ep is not None:
        hexchess.zobrist_hash ^= ZOBRIST_EP[hexchess.ep]

    if target_piece is not None or (<str>piece).lower() == 'p':
        hexchess.halfmove = 0
    else:
        hexchess.halfmove += 1

    color = _piece_color(piece)
    if color == 'b':
        hexchess.fullmove += 1
        hexchess.turn = 'w'
    else:
        hexchess.turn = 'b'

    hexchess.zobrist_hash ^= ZOBRIST_TURN
    hexchess.zobrist_hash ^= _piece_hash(piece, from_index)

    hexchess.board[from_index] = None
    moving_piece_list.remove(from_index)
    if promotion is None:
        hexchess.board[to_index] = piece
    elif color == 'b':
        hexchess.board[to_index] = promotion
    else:
        hexchess.board[to_index] = promotion.upper()

    captured_piece = target_piece

    if target_piece is not None:
        hexchess.zobrist_hash ^= _piece_hash(target_piece, to_index)
        enemy_piece_list.remove(to_index)

    if to_index == undo.previous_ep and target_piece is None:
        captured = _step(to_index, 0) if piece == 'p' else _step(to_index, 6) if piece == 'P' else None
        if captured is not None:
            captured_index = captured
            captured_piece = hexchess.board[captured]
            if captured_piece is not None:
                hexchess.zobrist_hash ^= _piece_hash(captured_piece, captured)
                enemy_piece_list.remove(captured)
            hexchess.board[captured] = None

    placed_piece = hexchess.board[to_index]
    if placed_piece is None:
        error('failed to apply move: destination piece missing')
    moving_piece_list.add(to_index)
    hexchess.zobrist_hash ^= _piece_hash(placed_piece, to_index)

    if piece == 'K':
        hexchess.white_king = to_index
    elif piece == 'k':
        hexchess.black_king = to_index

    if captured_piece == 'K':
        hexchess.white_king = None
    elif captured_piece == 'k':
        hexchess.black_king = None

    if piece == 'p':
        hexchess.ep = BLACK_EN_PASSANT_TARGETS.get((from_index, to_index))
    elif piece == 'P':
        hexchess.ep = WHITE_EN_PASSANT_TARGETS.get((from_index, to_index))
    else:
        hexchess.ep = None

    if hexchess.ep is not None:
        hexchess.zobrist_hash ^= ZOBRIST_EP[hexchess.ep]

    return MoveUndo(
        from_index=undo.from_index,
        to_index=undo.to_index,
        promotion=undo.promotion,
        moved_piece=undo.moved_piece,
        captured_piece=captured_piece,
        captured_index=captured_index,
        previous_ep=undo.previous_ep,
        previous_turn=undo.previous_turn,
        previous_halfmove=undo.previous_halfmove,
        previous_fullmove=undo.previous_fullmove,
        previous_white_king=undo.previous_white_king,
        previous_black_king=undo.previous_black_king,
        previous_hash=undo.previous_hash,
    )


cdef void _unmake_move(object hexchess, object undo):
    cdef object moving_piece_list
    cdef object enemy_piece_list

    hexchess.ep = undo.previous_ep
    hexchess.turn = undo.previous_turn
    hexchess.halfmove = undo.previous_halfmove
    hexchess.fullmove = undo.previous_fullmove
    hexchess.white_king = undo.previous_white_king
    hexchess.black_king = undo.previous_black_king
    hexchess.zobrist_hash = undo.previous_hash

    moving_piece_list = hexchess.white_pieces if undo.moved_piece.isupper() else hexchess.black_pieces
    enemy_piece_list = hexchess.black_pieces if undo.moved_piece.isupper() else hexchess.white_pieces

    hexchess.board[undo.from_index] = undo.moved_piece
    hexchess.board[undo.to_index] = None if undo.captured_index is not None else undo.captured_piece
    moving_piece_list.remove(undo.to_index)
    moving_piece_list.add(undo.from_index)

    if undo.captured_index is None and undo.captured_piece is not None:
        enemy_piece_list.add(undo.to_index)

    if undo.captured_index is not None:
        hexchess.board[undo.captured_index] = undo.captured_piece
        if undo.captured_piece is not None:
            enemy_piece_list.add(undo.captured_index)


@dataclass(frozen=True, slots=True)
class San:
    from_index: int
    to_index: int
    promotion: PromotionPiece | None = None

    @classmethod
    def from_value(cls, value: 'San | str') -> 'San':
        return value if isinstance(value, San) else cls.parse(value)

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
            promotion = last

        if len(from_position) + len(to_position) + (1 if promotion else 0) != len(source):
            error(f'invalid san: {source}')

        return cls(from_index=index(from_position), to_index=index(to_position), promotion=promotion)

    def __str__(self) -> str:
        return f'{POSITIONS[self.from_index]}{POSITIONS[self.to_index]}{self.promotion or ""}'


@dataclass(frozen=True, slots=True)
class MoveUndo:
    from_index: int
    to_index: int
    promotion: PromotionPiece | None
    moved_piece: Piece
    captured_piece: Piece | None
    captured_index: int | None
    previous_ep: int | None
    previous_turn: Color
    previous_halfmove: int
    previous_fullmove: int
    previous_white_king: int | None
    previous_black_king: int | None
    previous_hash: int


def create_board() -> Board:
    return [None] * 91


def compute_piece_lists(board: Board) -> tuple[set[int], set[int]]:
    white_pieces: set[int] = set()
    black_pieces: set[int] = set()
    cdef int square
    cdef object piece

    for square, piece in enumerate(board):
        if piece is None:
            continue

        if piece.isupper():
            white_pieces.add(square)
        else:
            black_pieces.add(square)

    return white_pieces, black_pieces


def parse_board(source: str) -> Board:
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
            board[board_index] = 'K'
            board_index += 1
            i += 1
            continue

        if current == 'k':
            if black_king:
                error('parse failed: multiple black kings')
            black_king = True
            board[board_index] = 'k'
            board_index += 1
            i += 1
            continue

        if current in {'b', 'B', 'n', 'N', 'p', 'P', 'Q', 'q', 'r', 'R'}:
            board[board_index] = current
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


def stringify_board(board: Board) -> str:
    blank = 0
    result: list[str] = []

    for board_index, piece in enumerate(board):
        if piece is None:
            blank += 1
        else:
            if blank > 0:
                result.append(str(blank))
                blank = 0
            result.append(piece)

        if board_index in BOARD_ROW_BREAKS:
            if blank > 0:
                result.append(str(blank))
                blank = 0
            result.append('/')

    if blank > 0:
        result.append(str(blank))

    return ''.join(result)


def is_legal_en_passant(position: int) -> bool:
    return position in LEGAL_EN_PASSANT


@dataclass(slots=True)
class Hexchess:
    board: Board
    ep: int | None
    turn: Color
    halfmove: int
    fullmove: int
    white_king: int | None
    black_king: int | None
    white_pieces: set[int]
    black_pieces: set[int]
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

        self.board = parse_board(board_source)
        self.white_king = self.board.index('K') if 'K' in self.board else None
        self.black_king = self.board.index('k') if 'k' in self.board else None
        self.white_pieces, self.black_pieces = compute_piece_lists(self.board)

        if turn not in {'w', 'b'}:
            error(f'invalid turn color: {turn}')
        self.turn = turn

        if ep == '-':
            self.ep = None
        elif is_position(ep):
            ep_index = index(ep)
            if not is_legal_en_passant(ep_index):
                error(f'illegal en passant: {ep}')
            self.ep = ep_index
        else:
            error(f'invalid en passant: {ep}')

        try:
            parsed_halfmove = int(halfmove)
        except ValueError as exc:
            error(f'invalid halfmove: {halfmove}')
            raise exc
        self.halfmove = max(0, parsed_halfmove)

        try:
            parsed_fullmove = int(fullmove)
        except ValueError as exc:
            error(f'invalid fullmove: {fullmove}')
            raise exc
        if parsed_fullmove == 0:
            error(f'invalid fullmove: {fullmove}')
        self.fullmove = parsed_fullmove
        self.zobrist_hash = compute_zobrist_hash(self.board, self.turn, self.ep)

    @classmethod
    def from_state(
        cls,
        board: Board,
        ep: int | None,
        turn: Color,
        halfmove: int,
        fullmove: int,
        white_king: int | None,
        black_king: int | None,
        white_pieces: set[int],
        black_pieces: set[int],
        zobrist_hash: int,
    ) -> 'Hexchess':
        hexchess = cls.__new__(cls)
        hexchess.board = board
        hexchess.ep = ep
        hexchess.turn = turn
        hexchess.halfmove = halfmove
        hexchess.fullmove = fullmove
        hexchess.white_king = white_king
        hexchess.black_king = black_king
        hexchess.white_pieces = white_pieces
        hexchess.black_pieces = black_pieces
        hexchess.zobrist_hash = zobrist_hash
        return hexchess

    @classmethod
    def parse(cls, fen: str) -> 'Hexchess':
        return cls(fen)

    @classmethod
    def init(cls) -> 'Hexchess':
        return cls(INITIAL_POSITION)

    def apply(self, sequence: str) -> 'Hexchess':
        clone = self.clone()

        for move_index, part in enumerate(piece for piece in sequence.split(' ') if piece.strip()):
            try:
                san = San.parse(part)
            except NativeEngineError:
                error(f'invalid san at index {move_index}: {part}')
            try:
                clone.apply_move(san)
            except NativeEngineError:
                error(f'illegal move at index {move_index}: {part}')

        self.board[:] = clone.board
        self.ep = clone.ep
        self.turn = clone.turn
        self.halfmove = clone.halfmove
        self.fullmove = clone.fullmove
        self.white_king = clone.white_king
        self.black_king = clone.black_king
        self.white_pieces = clone.white_pieces.copy()
        self.black_pieces = clone.black_pieces.copy()
        self.zobrist_hash = clone.zobrist_hash
        return self

    def clone(self) -> 'Hexchess':
        return Hexchess.from_state(
            self.board.copy(),
            self.ep,
            self.turn,
            self.halfmove,
            self.fullmove,
            self.white_king,
            self.black_king,
            self.white_pieces.copy(),
            self.black_pieces.copy(),
            self.zobrist_hash,
        )

    def position_key(self) -> int:
        return self.zobrist_hash

    def find_king(self, color: Color) -> int | None:
        return self.black_king if color == 'b' else self.white_king

    def get(self, position: str) -> Piece | None:
        return self.board[index(position)]

    def get_color(self, color: Color) -> list[int]:
        return sorted(self.white_pieces if color == 'w' else self.black_pieces)

    def current_moves(self) -> list[San]:
        return [_san_from_code(move_code) for move_code in _current_moves(self)]

    def is_check(self) -> bool:
        king = self.find_king(self.turn)
        if king is None:
            return False

        return self.is_square_attacked(king, _other_color(self.turn))

    def is_checkmate(self) -> bool:
        return self.is_check() and len(self.current_moves()) == 0

    def is_stalemate(self) -> bool:
        return not self.is_check() and len(self.current_moves()) == 0

    def is_legal(self, san: San | str) -> bool:
        move = San.from_value(san)
        piece = self.board[move.from_index]
        if piece is None:
            return False
        if _piece_color(piece) != self.turn:
            return False
        return any(
            candidate.from_index == move.from_index
            and candidate.to_index == move.to_index
            and candidate.promotion == move.promotion
            for candidate in self.moves_from(move.from_index)
        )

    def is_threatened(self, position: int | str) -> bool:
        board_index = index(position) if isinstance(position, str) else position
        threatened_piece = self.board[board_index]
        if threatened_piece is None:
            return False

        return self.is_square_attacked(board_index, _other_color(_piece_color(threatened_piece)))

    def is_square_attacked(self, square: int, by_color: Color) -> bool:
        return _is_square_attacked(self, square, by_color)

    def is_square_attacked_by_pawn(self, square: int, by_color: Color) -> bool:
        return _is_square_attacked_by_pawn(self, square, by_color)

    def moves_from(self, from_value: int | str) -> list[San]:
        from_index = index(from_value) if isinstance(from_value, str) else from_value
        return [_san_from_code(move_code) for move_code in _moves_from(self, from_index)]

    def moves_from_unsafe(self, from_value: int | str) -> list[San]:
        from_index = index(from_value) if isinstance(from_value, str) else from_value
        return [_san_from_code(move_code) for move_code in _moves_from_unsafe(self, from_index)]

    def apply_move(self, san: San | str) -> 'Hexchess':
        if not self.is_legal(san):
            error(f'illegal move: {san}')
        return self.apply_move_unsafe(san)

    def apply_move_unsafe(self, san: San | str) -> 'Hexchess':
        _make_move_unsafe(self, san)
        return self

    def make_move_unsafe(self, san: San | str) -> MoveUndo:
        return _make_move_unsafe(self, san)

    def unmake_move(self, undo: MoveUndo) -> None:
        _unmake_move(self, undo)

    def to_string(self) -> str:
        en_passant = '-' if self.ep is None else POSITIONS[self.ep]
        return f'{stringify_board(self.board)} {self.turn} {en_passant} {self.halfmove} {self.fullmove}'

    def __str__(self) -> str:
        return self.to_string()


def _push_pawn_move(result: list[San], san: San, color: Color) -> None:
    _push_pawn_move_c(result, san, color)


def _pawn_advance(hexchess: Hexchess, start: int, from_index: int, forward: Direction) -> San | None:
    return _pawn_advance_c(hexchess, start, from_index, forward)


def _pawn_capture(hexchess: Hexchess, from_index: int, direction: Direction, friendly: Color) -> San | None:
    return _pawn_capture_c(hexchess, from_index, direction, friendly)


def pawn_moves_unsafe(hexchess: Hexchess, from_index: int, color: Color) -> list[San]:
    return [_san_from_code(move_code) for move_code in _pawn_moves_unsafe(hexchess, from_index, color)]


def king_moves_unsafe(hexchess: Hexchess, from_index: int, color: Color) -> list[San]:
    return [_san_from_code(move_code) for move_code in _king_moves_unsafe(hexchess, from_index, color)]


def knight_moves_unsafe(hexchess: Hexchess, from_index: int, color: Color) -> list[San]:
    return [_san_from_code(move_code) for move_code in _knight_moves_unsafe(hexchess, from_index, color)]


def straight_line_moves_unsafe(
    hexchess: Hexchess,
    from_index: int,
    color: Color,
    directions: list[int],
) -> list[San]:
    return [_san_from_code(move_code) for move_code in _straight_line_moves_unsafe(hexchess, from_index, color, directions)]


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


def eval_pawn(index_value: int, color: Color, options: EvalOptions) -> float:
    bonuses = WHITE_ADVANCEMENT_BONUS if color == 'w' else BLACK_ADVANCEMENT_BONUS
    return options.pawn_value + bonuses.get(index_value, 0.0)


cdef inline tuple _move_key(object san):
    return (san.from_index, san.to_index, san.promotion)


cdef inline int _move_code_from_value(object san):
    if isinstance(san, int):
        return san
    return _encode_move(san.from_index, san.to_index, san.promotion)


def score_game_state(hexchess: Hexchess, options: EvalOptions) -> float:
    sign = 1.0 if hexchess.turn == 'w' else -1.0
    if hexchess.is_checkmate():
        return sign * options.checkmate_value
    if hexchess.is_stalemate():
        return sign * options.stalemate_value
    if hexchess.is_check():
        return sign * options.check_value
    return 0.0


def score_material(hexchess: Hexchess, options: EvalOptions) -> float:
    score = 0.0
    for board_index, piece in enumerate(hexchess.board):
        if piece is None:
            continue

        color_sign = 1.0 if piece.isupper() else -1.0
        lower = piece.lower()
        if lower == 'p':
            score += color_sign * eval_pawn(board_index, piece_color(piece), options)
        elif lower == 'n':
            score += color_sign * options.knight_value
        elif lower == 'b':
            score += color_sign * options.bishop_value
        elif lower == 'r':
            score += color_sign * options.rook_value
        elif lower == 'q':
            score += color_sign * options.queen_value
        else:
            score += color_sign * options.king_value

        pawn_attack_penalty = PAWN_ATTACK_PENALTY.get(lower)
        if pawn_attack_penalty is not None and hexchess.is_square_attacked_by_pawn(board_index, other_color(piece_color(piece))):
            score -= color_sign * pawn_attack_penalty

    return score


def evaluate(hexchess: Hexchess, options: EvalOptions | None = None) -> float:
    evaluation_options = options or EvalOptions()
    return score_material(hexchess, evaluation_options)


def static_eval_for_turn(hexchess: Hexchess, options: EvalOptions) -> float:
    score = evaluate(hexchess, options)
    return score if hexchess.turn == 'w' else -score


def move_key(san: San) -> tuple[int, int, PromotionPiece | None]:
    return _move_key(san)


TranspositionMove = int
TranspositionEntry = tuple[int, str, float, TranspositionMove | None]
PVS_WINDOW = 1e-9


def is_tactical_move(hexchess: Hexchess, san: San) -> bool:
    moved_piece = hexchess.board[san.from_index]
    if moved_piece is None:
        return False

    if san.promotion is not None:
        return True

    if hexchess.board[san.to_index] is not None:
        return True

    return moved_piece.lower() == 'p' and hexchess.ep == san.to_index


cdef inline bint _is_tactical_move(object hexchess, object san):
    cdef int move_code = _move_code_from_value(san)
    cdef int from_index = _move_from_code(move_code)
    cdef int to_index = _move_to_code(move_code)
    cdef object moved_piece = hexchess.board[from_index]
    if moved_piece is None:
        return False

    if _move_promotion_from_code(move_code) is not None:
        return True

    if hexchess.board[to_index] is not None:
        return True

    return (<str>moved_piece).lower() == 'p' and hexchess.ep == to_index


cdef inline int _move_order_score(
    object hexchess,
    object san,
    int depth,
    dict killer_moves,
    dict history_table,
):
    cdef int move_code = _move_code_from_value(san)
    cdef int from_index = _move_from_code(move_code)
    cdef int to_index = _move_to_code(move_code)
    cdef object promotion = _move_promotion_from_code(move_code)
    cdef object moved_piece = hexchess.board[from_index]
    cdef int score = 0
    cdef int moved_value
    cdef object captured_piece
    cdef object captured_index
    cdef int captured_value

    if moved_piece is None:
        return 0

    moved_value = PIECE_VALUES[(<str>moved_piece).lower()]
    captured_piece = hexchess.board[to_index]

    if captured_piece is None and (<str>moved_piece).lower() == 'p' and hexchess.ep == to_index:
        captured_index = _step(to_index, 0) if moved_piece == 'p' else _step(to_index, 6)
        if captured_index is not None:
            captured_piece = hexchess.board[captured_index]

    if captured_piece is not None:
        captured_value = PIECE_VALUES[(<str>captured_piece).lower()]
        score += 10_000 + (captured_value * 100) - moved_value

    if promotion is not None:
        score += PROMOTION_ORDER_BONUS[promotion]

    if (<str>moved_piece).lower() == 'p' and captured_piece is None:
        score += 5

    if move_code in killer_moves.get(depth, ()):
        score += 9_000

    score += history_table.get(move_code, 0)
    return score


def move_order_score(
    hexchess: Hexchess,
    san: San,
    depth: int,
    killer_moves: dict[int, tuple[int, ...]],
    history_table: dict[int, int],
) -> int:
    return _move_order_score(hexchess, san, depth, killer_moves, history_table)


def optimize_for_branch_pruning(
    hexchess: Hexchess,
    sans: list[object],
    depth: int,
    killer_moves: dict[int, tuple[int, ...]],
    history_table: dict[int, int],
    tt_move: TranspositionMove | None = None,
) -> None:
    sans.sort(
        key=lambda san: (
            _move_code_from_value(san) == tt_move,
            _move_order_score(hexchess, san, depth, killer_moves, history_table),
        ),
        reverse=True,
    )


def record_killer_move(
    killer_moves: dict[int, tuple[int, ...]],
    depth: int,
    san: San | int,
) -> None:
    key = _move_code_from_value(san)
    current = tuple(existing for existing in killer_moves.get(depth, ()) if existing != key)
    killer_moves[depth] = (key, *current)[:2]


def should_reduce_late_move(
    hexchess: Hexchess,
    san: San,
    depth: int,
    move_index: int,
    in_check: bool,
) -> bool:
    return _should_reduce_late_move(hexchess, san, depth, move_index, in_check)


cdef inline bint _should_reduce_late_move(
    object hexchess,
    object san,
    int depth,
    int move_index,
    bint in_check,
):
    if depth < 3:
        return False

    if move_index < 3:
        return False

    if in_check:
        return False

    return not _is_tactical_move(hexchess, san)


def quiescence(
    hexchess: Hexchess,
    alpha: float,
    beta: float,
    evaluations: list[int],
    options: EvalOptions,
) -> float:
    cdef list tactical_moves
    cdef int move_code
    evaluations[0] += 1
    stand_pat = static_eval_for_turn(hexchess, options)

    if stand_pat >= beta:
        return stand_pat

    if stand_pat > alpha:
        alpha = stand_pat

    tactical_moves = [move_code for move_code in _current_moves(hexchess) if _is_tactical_move(hexchess, move_code)]

    if not tactical_moves:
        return stand_pat

    tactical_moves.sort(key=lambda move: _move_order_score(hexchess, move, 0, {}, {}), reverse=True)

    value = stand_pat

    for move_code in tactical_moves:
        undo = _make_move_unsafe(hexchess, move_code)
        child_value = -quiescence(hexchess, -beta, -alpha, evaluations, options)
        _unmake_move(hexchess, undo)

        if child_value >= beta:
            return child_value

        if child_value > value:
            value = child_value

        if child_value > alpha:
            alpha = child_value

    return value


def negamax(
    table: dict[int, TranspositionEntry],
    hexchess: Hexchess,
    depth: int,
    ply: int,
    alpha: float,
    beta: float,
    evaluations: list[int],
    options: EvalOptions,
    killer_moves: dict[int, tuple[int, ...]],
    history_table: dict[int, int],
) -> float:
    cdef bint in_check
    cdef list current_moves
    cdef int move_code
    cdef int reduced_depth
    alpha_orig = alpha
    key = hexchess.position_key()
    entry = table.get(key)
    tt_move = entry[3] if entry is not None else None

    if entry is not None:
        entry_depth, flag, value, _ = entry
        if entry_depth >= depth:
            if flag == 'exact':
                return value
            if flag == 'lower' and value >= beta:
                return value
            if flag == 'upper' and value <= alpha:
                return value

    current_moves = _current_moves(hexchess)

    if not current_moves:
        evaluations[0] += 1
        if hexchess.is_check():
            return options.checkmate_value if hexchess.turn == 'w' else -options.checkmate_value
        return options.stalemate_value if hexchess.turn == 'w' else -options.stalemate_value

    if depth == 0:
        return quiescence(hexchess, alpha, beta, evaluations, options)

    in_check = hexchess.is_check()
    optimize_for_branch_pruning(hexchess, current_moves, ply, killer_moves, history_table, tt_move)
    value = float('-inf')
    best_move: int | None = None

    for move_index, move_code in enumerate(current_moves):
        undo = _make_move_unsafe(hexchess, move_code)

        reduced_depth = depth - 1
        if _should_reduce_late_move(hexchess, move_code, depth, move_index, in_check):
            reduced_depth = max(0, depth - 2)

        if move_index == 0:
            child_value = -negamax(
                table,
                hexchess,
                depth - 1,
                ply + 1,
                -beta,
                -alpha,
                evaluations,
                options,
                killer_moves,
                history_table,
            )
        else:
            child_value = -negamax(
                table,
                hexchess,
                reduced_depth,
                ply + 1,
                -alpha - PVS_WINDOW,
                -alpha,
                evaluations,
                options,
                killer_moves,
                history_table,
            )

            if alpha < child_value < beta:
                child_value = -negamax(
                    table,
                    hexchess,
                    depth - 1,
                    ply + 1,
                    -beta,
                    -alpha,
                    evaluations,
                    options,
                    killer_moves,
                    history_table,
                )

        _unmake_move(hexchess, undo)

        if child_value > value:
            value = child_value
            best_move = move_code

        alpha = max(alpha, value)
        if alpha >= beta:
            if not _is_tactical_move(hexchess, move_code):
                record_killer_move(killer_moves, ply, move_code)
                history_table[move_code] = history_table.get(move_code, 0) + depth * depth
            best_move = move_code
            break

    flag = 'exact'
    if value <= alpha_orig:
        flag = 'upper'
    elif value >= beta:
        flag = 'lower'
    table[key] = (depth, flag, value, best_move)
    return value


def search(hexchess: Hexchess, depth: int, options: EvalOptions | None = None) -> dict[str, object]:
    if depth < 1:
        error(f'invalid depth: {depth}')

    evaluation_options = options or EvalOptions()
    table: dict[int, TranspositionEntry] = {}
    killer_moves: dict[int, tuple[int, ...]] = {}
    history_table: dict[int, int] = {}
    evaluations = [0]
    sans: list[dict[str, object]] = []
    cdef list root_moves
    cdef int move_code

    root_moves = _current_moves(hexchess)
    optimize_for_branch_pruning(hexchess, root_moves, 0, killer_moves, history_table)

    for move_code in root_moves:
        undo = _make_move_unsafe(hexchess, move_code)
        score = negamax(
            hexchess=hexchess,
            table=table,
            depth=depth - 1,
            ply=1,
            alpha=float('-inf'),
            beta=float('inf'),
            evaluations=evaluations,
            options=evaluation_options,
            killer_moves=killer_moves,
            history_table=history_table,
        )

        _unmake_move(hexchess, undo)
        sans.append({'san': _move_string(move_code), 'score': score})

    sans.sort(key=lambda item: item['score'])

    return {
        'depth': depth,
        'evaluations': evaluations[0],
        'sans': sans,
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

        if not isinstance(position, str):
            error('invalid position: expected string')
        if not isinstance(depth, int):
            error('invalid depth: expected integer')

        hexchess = Hexchess.parse(position)
        return search(hexchess, depth)

    error(f'Unknown engine command: {command}')

from __future__ import annotations

import re
import time
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
WHITE_ADVANCEMENT_BONUS = {
    POSITION_TO_INDEX[name]: scalar * scalar * 2.0
    for name, scalar in WHITE_ADVANCEMENT_SCALARS.items()
}
BLACK_ADVANCEMENT_BONUS = {
    POSITION_TO_INDEX[name]: scalar * scalar * 2.0
    for name, scalar in BLACK_ADVANCEMENT_SCALARS.items()
}


def piece_color(piece: Piece) -> Color:
    return 'b' if piece.islower() else 'w'


def index(position: str) -> int:
    try:
        return POSITION_TO_INDEX[position]
    except KeyError as exc:
        error(f'invalid position: {position}')
        raise exc


def is_position(source: str) -> bool:
    return source in POSITION_TO_INDEX


def step(from_index: int, direction: Direction) -> int | None:
    return GRAPH[from_index][direction]


def reverse_direction(direction: int) -> int:
    return (direction + 6) % 12


def other_color(color: Color) -> Color:
    return 'b' if color == 'w' else 'w'


def is_promotion_position(position: int, color: Color) -> bool:
    positions = WHITE_PROMOTION_POSITIONS if color == 'w' else BLACK_PROMOTION_POSITIONS
    return position in positions


def is_target(hexchess: 'Hexchess', position: int | None, color: Color) -> bool:
    return position is not None and (
        hexchess.board[position] is None or piece_color(hexchess.board[position]) != color
    )


def walk(hexchess: 'Hexchess', from_index: int, direction: Direction, color: Color) -> list[int]:
    path: list[int] = []
    position = from_index

    while True:
        next_position = step(position, direction)
        if next_position is None:
            return path

        position = next_position
        piece = hexchess.board[position]

        if piece is None:
            path.append(position)
            continue

        if piece_color(piece) == color:
            return path

        path.append(position)
        return path


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
    move: San
    moved_piece: Piece
    captured_piece: Piece | None
    captured_index: int | None
    previous_ep: int | None
    previous_turn: Color
    previous_halfmove: int
    previous_fullmove: int
    previous_white_king: int | None
    previous_black_king: int | None


def create_board() -> Board:
    return [None] * 91


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
    ) -> 'Hexchess':
        hexchess = cls.__new__(cls)
        hexchess.board = board
        hexchess.ep = ep
        hexchess.turn = turn
        hexchess.halfmove = halfmove
        hexchess.fullmove = fullmove
        hexchess.white_king = white_king
        hexchess.black_king = black_king
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
        )

    def position_key(self) -> tuple[tuple[Piece | None, ...], int | None, Color, int, int]:
        return (tuple(self.board), self.ep, self.turn, self.halfmove, self.fullmove)

    def find_king(self, color: Color) -> int | None:
        return self.black_king if color == 'b' else self.white_king

    def get(self, position: str) -> Piece | None:
        return self.board[index(position)]

    def get_color(self, color: Color) -> list[int]:
        return [board_index for board_index, piece in enumerate(self.board) if piece and piece_color(piece) == color]

    def current_moves(self) -> list[San]:
        result: list[San] = []
        for board_index in self.get_color(self.turn):
            result.extend(self.moves_from(board_index))
        return result

    def is_check(self) -> bool:
        king = self.find_king(self.turn)
        if king is None:
            return False

        return self.is_square_attacked(king, other_color(self.turn))

    def is_checkmate(self) -> bool:
        return self.is_check() and len(self.current_moves()) == 0

    def is_stalemate(self) -> bool:
        return not self.is_check() and len(self.current_moves()) == 0

    def is_legal(self, san: San | str) -> bool:
        move = San.from_value(san)
        piece = self.board[move.from_index]
        if piece is None:
            return False
        if piece_color(piece) != self.turn:
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

        return self.is_square_attacked(board_index, other_color(piece_color(threatened_piece)))

    def is_square_attacked(self, square: int, by_color: Color) -> bool:
        pawn_piece = 'P' if by_color == 'w' else 'p'
        pawn_directions = (reverse_direction(10), reverse_direction(2)) if by_color == 'w' else (reverse_direction(4), reverse_direction(8))

        for direction in pawn_directions:
            source = step(square, direction)
            if source is not None and self.board[source] == pawn_piece:
                return True

        king_piece = 'K' if by_color == 'w' else 'k'
        for direction in range(12):
            source = step(square, direction)
            if source is not None and self.board[source] == king_piece:
                return True

        knight_piece = 'N' if by_color == 'w' else 'n'
        for source in KNIGHT_ATTACK_SOURCES[square]:
            if self.board[source] == knight_piece:
                return True

        bishop_piece = 'B' if by_color == 'w' else 'b'
        rook_piece = 'R' if by_color == 'w' else 'r'
        queen_piece = 'Q' if by_color == 'w' else 'q'

        for direction in range(12):
            position = square
            while True:
                position = step(position, direction)
                if position is None:
                    break

                piece = self.board[position]
                if piece is None:
                    continue

                if piece_color(piece) != by_color:
                    break

                if piece == queen_piece:
                    return True
                if direction in ORTHOGONAL_DIRECTIONS and piece == rook_piece:
                    return True
                if direction in DIAGONAL_DIRECTIONS and piece == bishop_piece:
                    return True
                break

        return False

    def moves_from(self, from_value: int | str) -> list[San]:
        from_index = index(from_value) if isinstance(from_value, str) else from_value
        piece = self.board[from_index]
        if piece is None:
            return []

        color = piece_color(piece)
        legal_moves: list[San] = []

        for san in self.moves_from_unsafe(from_index):
            undo = self.make_move_unsafe(san)
            king = self.find_king(color)
            if king is None or not self.is_square_attacked(king, other_color(color)):
                legal_moves.append(san)
            self.unmake_move(undo)

        return legal_moves

    def moves_from_unsafe(self, from_value: int | str) -> list[San]:
        from_index = index(from_value) if isinstance(from_value, str) else from_value
        piece = self.board[from_index]
        if piece is None:
            return []

        color = piece_color(piece)
        lower = piece.lower()

        if lower == 'b':
            return straight_line_moves_unsafe(self, from_index, color, [1, 3, 5, 7, 9, 11])
        if lower == 'k':
            return king_moves_unsafe(self, from_index, color)
        if lower == 'n':
            return knight_moves_unsafe(self, from_index, color)
        if lower == 'p':
            return pawn_moves_unsafe(self, from_index, color)
        if lower == 'q':
            return straight_line_moves_unsafe(self, from_index, color, list(range(12)))
        return straight_line_moves_unsafe(self, from_index, color, [0, 2, 4, 6, 8, 10])

    def apply_move(self, san: San | str) -> 'Hexchess':
        if not self.is_legal(san):
            error(f'illegal move: {san}')
        return self.apply_move_unsafe(san)

    def apply_move_unsafe(self, san: San | str) -> 'Hexchess':
        self.make_move_unsafe(san)
        return self

    def make_move_unsafe(self, san: San | str) -> MoveUndo:
        move = San.from_value(san)
        piece = self.board[move.from_index]
        if piece is None:
            error(f'cannot apply move from empty position: {move.from_index}')

        target_piece = self.board[move.to_index]
        undo = MoveUndo(
            move=move,
            moved_piece=piece,
            captured_piece=target_piece,
            captured_index=None,
            previous_ep=self.ep,
            previous_turn=self.turn,
            previous_halfmove=self.halfmove,
            previous_fullmove=self.fullmove,
            previous_white_king=self.white_king,
            previous_black_king=self.black_king,
        )

        if target_piece is not None or piece.lower() == 'p':
            self.halfmove = 0
        else:
            self.halfmove += 1

        color = piece_color(piece)
        if color == 'b':
            self.fullmove += 1
            self.turn = 'w'
        else:
            self.turn = 'b'

        self.board[move.from_index] = None
        if move.promotion is None:
            self.board[move.to_index] = piece
        elif color == 'b':
            self.board[move.to_index] = move.promotion
        else:
            self.board[move.to_index] = move.promotion.upper()

        captured_piece = target_piece
        captured_index: int | None = None

        if move.to_index == undo.previous_ep and target_piece is None:
            captured = step(move.to_index, 0) if piece == 'p' else step(move.to_index, 6) if piece == 'P' else None
            if captured is not None:
                captured_index = captured
                captured_piece = self.board[captured]
                self.board[captured] = None

        if piece == 'K':
            self.white_king = move.to_index
        elif piece == 'k':
            self.black_king = move.to_index

        if captured_piece == 'K':
            self.white_king = None
        elif captured_piece == 'k':
            self.black_king = None

        if piece == 'p':
            self.ep = BLACK_EN_PASSANT_TARGETS.get((move.from_index, move.to_index))
        elif piece == 'P':
            self.ep = WHITE_EN_PASSANT_TARGETS.get((move.from_index, move.to_index))
        else:
            self.ep = None

        return MoveUndo(
            move=undo.move,
            moved_piece=undo.moved_piece,
            captured_piece=captured_piece,
            captured_index=captured_index,
            previous_ep=undo.previous_ep,
            previous_turn=undo.previous_turn,
            previous_halfmove=undo.previous_halfmove,
            previous_fullmove=undo.previous_fullmove,
            previous_white_king=undo.previous_white_king,
            previous_black_king=undo.previous_black_king,
        )

    def unmake_move(self, undo: MoveUndo) -> None:
        self.ep = undo.previous_ep
        self.turn = undo.previous_turn
        self.halfmove = undo.previous_halfmove
        self.fullmove = undo.previous_fullmove
        self.white_king = undo.previous_white_king
        self.black_king = undo.previous_black_king

        self.board[undo.move.from_index] = undo.moved_piece
        self.board[undo.move.to_index] = None if undo.captured_index is not None else undo.captured_piece

        if undo.captured_index is not None:
            self.board[undo.captured_index] = undo.captured_piece

    def to_string(self) -> str:
        en_passant = '-' if self.ep is None else POSITIONS[self.ep]
        return f'{stringify_board(self.board)} {self.turn} {en_passant} {self.halfmove} {self.fullmove}'

    def __str__(self) -> str:
        return self.to_string()


def _push_pawn_move(result: list[San], san: San, color: Color) -> None:
    if is_promotion_position(san.to_index, color):
        result.extend(
            [
                San(san.from_index, san.to_index, 'b'),
                San(san.from_index, san.to_index, 'n'),
                San(san.from_index, san.to_index, 'q'),
                San(san.from_index, san.to_index, 'r'),
            ]
        )
        return
    result.append(san)


def _pawn_advance(hexchess: Hexchess, start: int, from_index: int, forward: Direction) -> San | None:
    to_index = step(from_index, forward)
    if to_index is None:
        return None
    return San(start, to_index) if hexchess.board[to_index] is None else None


def _pawn_capture(hexchess: Hexchess, from_index: int, direction: Direction, friendly: Color) -> San | None:
    to_index = step(from_index, direction)
    if to_index is None:
        return None

    target = hexchess.board[to_index]
    if target is not None:
        if piece_color(target) != friendly:
            return San(from_index, to_index)
    elif hexchess.ep == to_index and hexchess.turn == friendly:
        return San(from_index, to_index)

    return None


def pawn_moves_unsafe(hexchess: Hexchess, from_index: int, color: Color) -> list[San]:
    result: list[San] = []
    forward, portside, starboard = (0, 10, 2) if color == 'w' else (6, 4, 8)

    advance1 = _pawn_advance(hexchess, from_index, from_index, forward)
    if advance1 is not None:
        _push_pawn_move(result, advance1, color)
        starting_positions = WHITE_PAWN_STARTS if color == 'w' else BLACK_PAWN_STARTS
        if from_index in starting_positions:
            advance2 = _pawn_advance(hexchess, from_index, advance1.to_index, forward)
            if advance2 is not None:
                result.append(advance2)

    for direction in (portside, starboard):
        capture = _pawn_capture(hexchess, from_index, direction, color)
        if capture is not None:
            _push_pawn_move(result, capture, color)

    return result


def king_moves_unsafe(hexchess: Hexchess, from_index: int, color: Color) -> list[San]:
    result: list[San] = []
    for direction in range(12):
        to_index = step(from_index, direction)
        if is_target(hexchess, to_index, color):
            result.append(San(from_index, to_index))
    return result


def knight_moves_unsafe(hexchess: Hexchess, from_index: int, color: Color) -> list[San]:
    result: list[San] = []
    for diagonal, orthogonal1, orthogonal2 in KNIGHT_TARGETS:
        intermediate = step(from_index, diagonal)
        if intermediate is None:
            continue

        first = step(intermediate, orthogonal1)
        second = step(intermediate, orthogonal2)

        if is_target(hexchess, first, color):
            result.append(San(from_index, first))
        if is_target(hexchess, second, color):
            result.append(San(from_index, second))

    return result


def straight_line_moves_unsafe(
    hexchess: Hexchess,
    from_index: int,
    color: Color,
    directions: list[int],
) -> list[San]:
    result: list[San] = []
    for direction in directions:
        for to_index in walk(hexchess, from_index, direction, color):
            result.append(San(from_index, to_index))
    return result


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

    return score


def evaluate(hexchess: Hexchess, options: EvalOptions | None = None) -> float:
    evaluation_options = options or EvalOptions()
    return score_material(hexchess, evaluation_options)


def optimize_for_branch_pruning(_hexchess: Hexchess, sans: list[San]) -> None:
    sans.sort(key=lambda _: 0, reverse=True)


def negamax(
    table: dict[tuple[tuple[Piece | None, ...], int | None, Color, int, int], tuple[int, str, float]],
    hexchess: Hexchess,
    depth: int,
    alpha: float,
    beta: float,
    evaluations: list[int],
    options: EvalOptions,
) -> float:
    alpha_orig = alpha
    key = hexchess.position_key()
    entry = table.get(key)

    if entry is not None:
        entry_depth, flag, value = entry
        if entry_depth >= depth:
            if flag == 'exact':
                return value
            if flag == 'lower' and value >= beta:
                return value
            if flag == 'upper' and value <= alpha:
                return value

    current_moves = hexchess.current_moves()

    if not current_moves:
        evaluations[0] += 1
        if hexchess.is_check():
            return options.checkmate_value if hexchess.turn == 'w' else -options.checkmate_value
        return options.stalemate_value if hexchess.turn == 'w' else -options.stalemate_value

    if depth == 0:
        evaluations[0] += 1
        if hexchess.turn == 'w':
            return evaluate(hexchess, options)
        return -evaluate(hexchess, options)

    optimize_for_branch_pruning(hexchess, current_moves)
    value = float('-inf')

    for san in current_moves:
        undo = hexchess.make_move_unsafe(san)
        value = max(value, -negamax(table, hexchess, depth - 1, -beta, -alpha, evaluations, options))
        hexchess.unmake_move(undo)
        alpha = max(alpha, value)
        if alpha >= beta:
            break

    flag = 'exact'
    if value <= alpha_orig:
        flag = 'upper'
    elif value >= beta:
        flag = 'lower'
    table[key] = (depth, flag, value)
    return value


def search(hexchess: Hexchess, depth: int, options: EvalOptions | None = None) -> dict[str, object]:
    if depth < 1:
        error(f'invalid depth: {depth}')

    evaluation_options = options or EvalOptions()
    table: dict[tuple[tuple[Piece | None, ...], int | None, Color, int, int], tuple[int, str, float]] = {}
    evaluations = [0]
    sans: list[dict[str, object]] = []

    for san in hexchess.current_moves():
        undo = hexchess.make_move_unsafe(san)
        score = negamax(hexchess=hexchess, table=table, depth=depth - 1, alpha=float('-inf'), beta=float('inf'), evaluations=evaluations, options=evaluation_options)
        hexchess.unmake_move(undo)
        sans.append({'san': str(san), 'score': score})

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

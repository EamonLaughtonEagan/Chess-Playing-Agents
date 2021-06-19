import math

import chess


def evaluate_moves(chessboard: chess.Board):
    return chessboard.legal_moves.count()


def get_piece_value(piece: chess.Piece):
    piece_value = 0
    piece_type = piece.piece_type
    if piece_type == chess.PAWN:
        piece_value = 9
    elif piece_type == chess.KNIGHT:
        piece_value = 30
    elif piece_type == chess.BISHOP:
        piece_value = 35
    elif piece_type == chess.ROOK:
        piece_value = 50
    elif piece_type == chess.QUEEN:
        piece_value = 90
    elif piece_type == chess.KING:
        piece_value = 900

    if piece.color == chess.WHITE:
        return piece_value
    else:
        return -piece_value


def evaluate_material(chessboard: chess.Board):
    if chessboard.is_checkmate():
        return 1e9 if chessboard.turn else -1e9
    if chessboard.is_stalemate():
        return 0

    total = 0
    piece_map = chessboard.piece_map()
    for piece_index in piece_map.keys():
        piece = piece_map[piece_index]
        total += get_piece_value(piece)
    return total


edge_squares = centre_squares = []
for e in ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8',
          'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8',
          'b1', 'c1', 'd1', 'e1', 'f1', 'g1',
          'b8', 'c8', 'd8', 'e8', 'f8', 'g8', ]:
    edge_squares.append(chess.parse_square(e))

for e in ['c3', 'd3', 'e3', 'f3',
          'c4', 'd4', 'e4', 'f4',
          'c5', 'd5', 'e5', 'f5',
          'c6', 'd6', 'e6', 'f6', ]:
    centre_squares.append(chess.parse_square(e))


# Press the green button in the gutter to run the script.
def evaluate_complex(chessboard: chess.Board):
    total = 0

    if chessboard.is_checkmate():
        return 1e9 if chessboard.turn else -1e9
    if chessboard.is_stalemate():
        return 0

    total += (chessboard.legal_moves.count() / 2)

    piece_map = chessboard.piece_map()
    for piece_index in piece_map.keys():
        piece = piece_map[piece_index]

        total += 2 * get_piece_value(piece)

    for square in edge_squares:
        piece = chessboard.piece_at(square)
        if piece is None:
            continue

        piece_type = piece.piece_type

        if piece_type == chess.KNIGHT:
            if piece.color == chess.WHITE:
                punishment = -10
            else:
                punishment = +10

            total += punishment

    for square in centre_squares:
        piece = chessboard.piece_at(square)

        if piece is not None and piece.piece_type in [chess.PAWN, chess.KNIGHT]:
            total += math.floor(get_piece_value(piece) / 4)  # Count again

    return total


files = []
files.append(chess.SquareSet.ray(chess.A1, chess.A8))


class T:
    passed = 0

    def __init__(self):
        self.f = 1

if __name__ == '__main__':
    t1 = T()
    t2 = T()

    T.passed += 1
    T.passed += 1
    print(str(t1.passed))

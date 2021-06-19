# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import math
import random
from abc import ABC, abstractmethod

from chessboard import display
import time

import chess
import chess.pgn
import chess.polyglot


# CONFIGURATION

class Config:
    GUI = True
    MOVE_SLEEP = 5
    NUM_GAMES = 20
    START_FEN = chess.STARTING_BOARD_FEN
    # START_FEN = "rnb1kbnr/ppp2ppp/3p4/4p1q1/4P1Q1/3P4/PPP2PPP/RNB1KBNR w KQkq - 0 4"
    DEBUG = True
    INDEX_MODE = True


def debug(obj):
    if Config.DEBUG:
        print(str(obj))


class Agent(ABC):
    i_board: chess.Board = None

    def __init__(self, board: chess.Board):
        self.board = board

    @abstractmethod
    def find_move(self) -> chess.Move:
        pass


class RandomAgent(Agent):
    def find_move(self) -> chess.Move:
        return random.choice([move for move in i_board.legal_moves])


class LimitMobilityAgent(Agent):

    def find_move(self) -> chess.Move:
        move_scores = {}
        best_move_score = 1000
        for move in self.board.legal_moves:
            self.board.push(move)
            move_scores[move] = evaluate_moves(self.board)
            self.board.pop()

            if move_scores[move] < best_move_score:
                best_move_score = move_scores[move]

        moves_with_best_score = []
        for move in move_scores.keys():
            if move_scores[move] == best_move_score:
                moves_with_best_score.append(move)

        return random.choice([m for m in moves_with_best_score])


class FrickAgent(Agent):
    def find_move(self) -> chess.Move:
        legal_moves = self.board.legal_moves
        legal_captures = []

        for move in legal_moves:
            self.board.push(move)
            if self.board.is_checkmate():
                return move
            self.board.pop()

            if self.board.is_into_check(move) or self.board.is_capture(move):
                legal_captures.append(move)

        if len(legal_captures) > 0:
            return random.choice([capture for capture in legal_captures])
        else:
            return random.choice([move for move in legal_moves])


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
    total = 0
    pieces = chessboard.piece_map()

    for piece_index in pieces.keys():
        total += get_piece_value(pieces[piece_index])

    return total


class MiniMaxAbstract(Agent):

    def __init__(self, board: chess.Board, depth=3):
        super().__init__(board)
        self.depth = depth

        #if Config.INDEX_MODE:
            #file_name = "./" + type(self).__name__ + "/" + depth


    evals = 0
    hashes = {}
    capturing_moves = {}
    zobrist_hash = None
    legal_moves = {}

    def sort_moves(self, moves: [chess.Move], depth) -> [chess.Move]:
        # Faster to add/remove at the end with O(1), then reverse with O(n)
        # Compare this to add/remove at the start with O(n) each time

        # Reverse ascending order of piece values
        moves.sort(key=lambda x: abs(get_piece_value(self.board.piece_at(x.from_square))), reverse=True)

        # if self.capturing_moves[depth]:
        #     for move in self.capturing_moves[depth]:
        #         if move in moves:
        #             moves.remove(move)
        #             moves.append(move)
        #
        # if self.zobrist_hash in self.hashes:
        #     zobrist_move = self.hashes[self.zobrist_hash]["bestmove"]
        #     if zobrist_move in moves:
        #         moves.remove(zobrist_move)
        #         moves.append(zobrist_move)

        return moves

    def evaluate_board(self) -> int:
        pass

    def negamax(self, depth, chessboard: chess.Board, color, alpha, beta):
        original_alpha = alpha

        self.zobrist_hash = chess.polyglot.zobrist_hash(chessboard)
        if self.zobrist_hash in self.hashes:

            hash_eval = self.hashes[self.zobrist_hash]
            if hash_eval["depth"] >= depth:

                hash_value = hash_eval["value"]
                flag = hash_eval["flag"]

                if flag == "exact":
                    return hash_eval["bestmove"], hash_value
                elif flag == "lowerbound":
                    alpha = max(alpha, hash_value)
                elif flag == "upperbound":
                    beta = min(beta, hash_value)

                if alpha >= beta:
                    return hash_eval["bestmove"], hash_value

        if depth == 0:
            return None, self.evaluate_board() * color

        
        #if self.zobrist_hash in self.legal_moves:
            #sorted_moves = self.legal_moves[self.zobrist_hash]
        #else:
        unsorted_moves = chessboard.legal_moves
        sorted_moves = []
        for um in unsorted_moves:
            sorted_moves.append(um)

        sorted_moves = self.sort_moves(sorted_moves, depth)
        self.legal_moves[self.zobrist_hash] = sorted_moves

        best_eval = -math.inf
        best_move = None

        for m in sorted_moves:
            chessboard.push(m)

            if self.board.is_capture(m):
                self.capturing_moves[depth].append(m)

            m_eval = -self.negamax(depth - 1, chessboard, -color, -beta, -alpha)[1]

            if Config.DEBUG and depth > 1:
                move_history = []
                max_history = self.depth - depth + 2

                for z in range(1, max_history):
                    prev_move = chessboard.move_stack[-z]
                    move_history.append(prev_move)

                g = chess.pgn.Game()
                g.add_line(chessboard.move_stack)

                s = ""
                for h in reversed(move_history):
                    s = s + h.uci() + ", "

                c = "white" if color else "black"
                debug(c + "(d " + str(depth) + ") " + str(m_eval) + ": " + s + "\t\t" + chessboard.fen())

            chessboard.pop()

            if m_eval > best_eval:
                best_eval = m_eval
                best_move = m

            alpha = max(alpha, best_eval)

            if beta <= alpha:
                break

        # Transposition table saving
        self.hashes[self.zobrist_hash] = {"value": best_eval}
        if best_eval <= original_alpha:
            self.hashes[self.zobrist_hash]["flag"] = "upperbound"
        elif best_eval >= beta:
            self.hashes[self.zobrist_hash]["flag"] = "lowerbound"
        else:
            self.hashes[self.zobrist_hash]["flag"] = "exact"

        self.hashes[self.zobrist_hash]["depth"] = depth
        self.hashes[self.zobrist_hash]["bestmove"] = best_move

        return best_move, best_eval

    def find_move(self) -> chess.Move:
        color = 1 if self.board.turn else -1

        for i in range(0, self.depth):
            self.capturing_moves[i + 1] = []

        start = time.time()
        nega_move, nega_eval = self.negamax(self.depth, self.board, color, -math.inf, math.inf)
        elapsed = time.time() - start

        if nega_move is None:
            print("null move!")
        else:
            print(nega_move.uci() + " = " + str(nega_eval) + " (" + str(elapsed) + " s, " + str(
                len(self.hashes)) + " hashes)")

        return nega_move


class MiniMaxMaterial(MiniMaxAbstract):
    def evaluate_board(self):
        return evaluate_material(self.board)


class MiniMaxPosition(MiniMaxAbstract):
    pos_pawn = [0, 0, 0, 0, 0, 0, 0, 0,
                50, 50, 50, 50, 50, 50, 50, 50,
                10, 10, 20, 30, 30, 20, 10, 10,
                5, 5, 10, 25, 25, 10, 5, 5,
                0, 0, 0, 20, 20, 0, 0, 0,
                5, -5, -10, 0, 0, -10, -5, 5,
                5, 10, 10, -20, -20, 10, 10, 5,
                0, 0, 0, 0, 0, 0, 0, 0]

    pos_knight = [-50, -40, -30, -30, -30, -30, -40, -50,
                  -40, -20, 0, 0, 0, 0, -20, -40,
                  -30, 0, 10, 15, 15, 10, 0, -30,
                  -30, 5, 15, 20, 20, 15, 5, -30,
                  -30, 0, 15, 20, 20, 15, 0, -30,
                  -30, 5, 10, 15, 15, 10, 5, -30,
                  -40, -20, 0, 5, 5, 0, -20, -40,
                  -50, -40, -30, -30, -30, -30, -40, -50]

    pos_bishop = [-20, -10, -10, -10, -10, -10, -10, -20,
                  -10, 0, 0, 0, 0, 0, 0, -10,
                  -10, 0, 5, 10, 10, 5, 0, -10,
                  -10, 5, 5, 10, 10, 5, 5, -10,
                  -10, 0, 10, 10, 10, 10, 0, -10,
                  -10, 10, 10, 10, 10, 10, 10, -10,
                  -10, 5, 0, 0, 0, 0, 5, -10,
                  -20, -10, -10, -10, -10, -10, -10, -20]

    pos_rook = [0, 0, 0, 0, 0, 0, 0, 0,
                5, 10, 10, 10, 10, 10, 10, 5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                -5, 0, 0, 0, 0, 0, 0, -5,
                0, 0, 0, 5, 5, 0, 0, 0]

    pos_queen = [-20, -10, -10, -5, -5, -10, -10, -20,
                 -10, 0, 0, 0, 0, 0, 0, -10,
                 -10, 0, 5, 5, 5, 5, 0, -10,
                 -5, 0, 5, 5, 5, 5, 0, -5,
                 0, 0, 5, 5, 5, 5, 0, -5,
                 -10, 5, 5, 5, 5, 5, 0, -10,
                 -10, 0, 5, 0, 0, 0, 0, -10,
                 -20, -10, -10, -5, -5, -10, -10, -20]

    pos_king = [-30, -40, -40, -50, -50, -40, -40, -30,
                -30, -40, -40, -50, -50, -40, -40, -30,
                -30, -40, -40, -50, -50, -40, -40, -30,
                -30, -40, -40, -50, -50, -40, -40, -30,
                -20, -30, -30, -40, -40, -30, -30, -20,
                -10, -20, -20, -20, -20, -20, -20, -10,
                20, 20, 0, 0, 0, 0, 20, 20,
                20, 30, 10, 0, 0, 10, 30, 20]

    def get_pos_value(self, piece: chess.Piece, pos: int):
        piece_type = piece.piece_type
        if piece_type == chess.BLACK:
            pos = 63 - pos

        if piece_type == chess.PAWN:
            return self.pos_pawn[pos]
        elif piece_type == chess.KNIGHT:
            return self.pos_knight[pos]
        elif piece_type == chess.BISHOP:
            return self.pos_bishop[pos]
        elif piece_type == chess.ROOK:
            return self.pos_rook[pos]
        elif piece_type == chess.QUEEN:
            return self.pos_queen[pos]
        elif piece_type == chess.KING:
            return self.pos_king[pos]

        raise Exception("Invalid piece " + str(piece))

    def evaluate_board(self):
        total = 0

        piece_map = self.board.piece_map()

        for piece_index in piece_map.keys():
            piece = piece_map[piece_index]
            value = self.get_pos_value(piece, piece_index)
            if piece.color == chess.BLACK:
                total -= value
            else:
                total += value

        return total


class MiniMaxMobility(MiniMaxAbstract):
    def evaluate_board(self):

        total = 0
        piece_map = self.board.piece_map()

        for piece_index in piece_map.keys():
            piece = piece_map[piece_index]

            attack_squares = self.board.attacks(piece_index)
            attack_squares_count = len(attack_squares)

            if piece.color == chess.WHITE:
                total += attack_squares_count
            else:
                total -= attack_squares_count

        return total


# Press the green button in the gutter to run the script.
def tick(tick_board):
    if Config.GUI:
        display.start(tick_board.board_fen())

    if tick_board.turn:
        agent_move = white.find_move()
    else:
        agent_move = black.find_move()

    tick_board.push(agent_move)
    if Config.GUI:
        display.start(tick_board.board_fen())

    if tick_board.is_game_over():
        time.sleep(2)
        return False
    else:
        if Config.GUI:
            time.sleep(Config.MOVE_SLEEP)
        return True


if __name__ == '__main__':

    white_wins = 0
    black_wins = 0
    draws = 0

    for i in range(0, Config.NUM_GAMES):
        i_board = chess.Board(Config.START_FEN)

        start_hash = chess.polyglot.zobrist_hash(i_board)
        print(str(start_hash))

        white = MiniMaxMaterial(i_board, 3)
        black = white
        # black = MiniMaxMobility(i_board, 3)

        while tick(i_board):
            debug(i_board.fen())
            pass

        # Game over; print results

        game = chess.pgn.Game()
        game.add_line(i_board.move_stack)
        print()

        print(game.mainline())

        outcome = i_board.outcome()
        if outcome.winner is None:
            draws += 1
        elif outcome.winner:
            white_wins += 1
        elif not outcome.winner:
            black_wins += 1

        print("Winner: {}, Reason: {}".format(outcome.winner, outcome.termination))

    print()
    print("Results:")
    print("White: {}\tBlack:{}\tDraws:{}".format(white_wins, black_wins, draws))

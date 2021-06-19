import abc
import collections
import math
import os
import pickle
import time

import chess
import chess.pgn
import chess.polyglot

import evaluate
import main

from agent import Agent, make_opening_move


class MiniMaxAbstract(Agent):
    def __init__(self, board: chess.Board, depth, *args, **kwargs):
        super().__init__(board)
        self.depth = depth

        if main.Config.INDEX_MODE:
            self.dir = str(os.getcwd()) + "\\index\\" + type(self).__name__ + "\\"
            if not os.path.exists(self.dir):
                os.makedirs(self.dir)
            self.file_name = self.dir + str(depth)

            io = None
            try:
                io = open(self.file_name, "rb")
                self.hashes = pickle.load(io)
            except (IOError, EOFError):
                pass
            finally:
                if io is not None:
                    io.close()

        self.evals = 0

        self.hashes = {}
        self.capturing_moves = {}
        self.legal_moves = {}
        self.bench_evaluate = 0

        # Benchmarks
        self.bench_sort = 0
        self.bench_index = 0
        self.bench_total = 0
        self.bench_evals = 0
        self.max_depth = 0

    def sort_moves(self, moves: chess.LegalMoveGenerator, board_hash, depth) -> collections.Iterator[chess.Move]:
        # Faster to add/remove at the end with O(1), then reverse with O(n)
        # Compare this to add/remove at the start with O(n) each time

        captures = []
        sorted_moves = []
        for um in moves:
            if self.board.is_capture(um):
                captures.append(um)
            else:
                sorted_moves.append(um)

        # captures.sort(key=lambda x: abs(evaluate.get_piece_value(self.board.piece_at(x.from_square))))

        for cap in captures:
            sorted_moves.append(cap)

        if board_hash in self.hashes:
            zobrist_move = self.hashes[board_hash]["b"]
            if zobrist_move in sorted_moves:
                sorted_moves.remove(zobrist_move)
                sorted_moves.append(zobrist_move)

        return reversed(sorted_moves)


    @abc.abstractmethod
    def evaluate_board(self) -> int:
        pass

    def negamax(self, depth, color, alpha, beta, allow_null_move):
        original_alpha = alpha

        nega_start = time.time()

        zobrist_hash = chess.polyglot.zobrist_hash(self.board)

        if main.Config.CACHE_EVALS and zobrist_hash in self.hashes:
            hash_eval = self.hashes[zobrist_hash]
            if hash_eval["d"] >= depth:
                zobrist_move = chess.Move.from_uci(hash_eval["b"])

                hash_value = hash_eval["v"]
                flag = hash_eval["f"]
                if flag == "e":
                    return zobrist_move, hash_value
                elif flag == "l":
                    alpha = max(alpha, hash_value)
                elif flag == "u":
                    beta = min(beta, hash_value)

                if alpha >= beta:
                    return zobrist_move, hash_value

        self.bench_index += (time.time() - nega_start)
        nega_start = time.time()

        if depth == 0:
            self.bench_evals += 1

            eval_start = time.time()
            board_eval = self.evaluate_board() * color
            self.bench_evaluate += (time.time() - eval_start)

            return None, board_eval

        if main.Config.NULL_PRUNE and allow_null_move and (depth - 3) >= 0 and not (self.board.is_check()):
            self.board.push(chess.Move.null())
            null_eval = -self.negamax(depth - 1, -color, -beta, -beta + 1, False)[1]
            self.board.pop()

            if null_eval >= beta:
                return None, null_eval

        move_list: [chess.Move]
        if main.Config.SORT_MOVES:
            if zobrist_hash in self.legal_moves:
                move_list = self.legal_moves[zobrist_hash]
            else:
                move_list = self.sort_moves(self.board.legal_moves, zobrist_hash, depth)
                self.legal_moves[zobrist_hash] = move_list
        else:
            move_list = self.board.legal_moves

        self.bench_sort += (time.time() - nega_start)

        best_eval = -math.inf
        best_move = None

        for m in move_list:
            self.board.push(m)
            m_eval = -self.negamax(depth - 1, -color, -beta, -alpha, True)[1]

            if main.Config.DEBUG and depth > 1:
                move_history = []
                max_history = self.depth - depth + 2

                for z in range(1, max_history):
                    prev_move = self.board.move_stack[-z]
                    move_history.append(prev_move)

                g = chess.pgn.Game()
                g.add_line(self.board.move_stack)

                s = ""
                for h in reversed(move_history):
                    s = s + h.uci() + ", "

                tabs = ""
                for i in range(0, self.depth - depth - 1):
                    tabs += "\t"

                c = "White" if self.board.turn else "Black"

                main.debug(tabs + c + "(d " + str(depth) + ") " + str(m_eval) + ": " + s + "\t" + str(
                    zobrist_hash) + "\t\t" + self.board.fen())

            self.board.pop()

            if m_eval > best_eval:
                best_eval = m_eval
                best_move = m

            alpha = max(alpha, best_eval)

            if beta <= alpha:
                break

        # Transposition table saving
        if main.Config.CACHE_EVALS and best_move is not None:
            nega_start = time.time()

            new_hash = {"v": best_eval, "d": depth, "b": best_move.uci()}

            if best_eval <= original_alpha:
                new_hash["f"] = "u"
            elif best_eval >= beta:
                new_hash["f"] = "l"
            else:
                new_hash["f"] = "e"

            self.hashes[zobrist_hash] = new_hash
            self.bench_index += (time.time() - nega_start)

        # print(str(best_move), end=" ")
        return best_move, best_eval

    def find_move(self) -> chess.Move:
        find_start = time.time()
        if self.board.fullmove_number < 10:
            opening = make_opening_move(self.board)
            if opening is not None:
                return opening

        # Color for negamax; just makes evaluation function of black negative
        color = 1 if self.board.turn else -1

        best_moves = []
        iterative_depth = 1
        iteration_search_time = 0
        for iterative_depth in range(1, self.depth + 1):
            start_time = time.time()
            start_nodes = self.bench_evals

            deep_move, deep_eval = self.negamax(iterative_depth, color, -math.inf, math.inf, False)
            best_moves.append([deep_move, deep_eval])

            elapsed_time = time.time() - start_time
            searched_nodes = (self.bench_evals - start_nodes)

            main.info("Depth " + str(iterative_depth) + " searched " + str(searched_nodes) + " in {:.2f}s\t".format(
                elapsed_time))
            iteration_search_time += elapsed_time

            if iteration_search_time >= 8.0 or deep_eval >= 100000:
                break

        main.info("Best moves: " + str(best_moves))

        self.max_depth = iterative_depth
        if self.max_depth >= 2:
            deep_eval = (best_moves[-1][1] + best_moves[-2][1]) / 2
            if len(best_moves) % 2 == 0:
                deep_move = best_moves[-1][0]
            else:
                deep_move = best_moves[-2][0]

        main.info("Benchmark ({} evals): index {}\tsort {}\tevals {}".format(self.bench_evals, self.bench_index,
                                                                             self.bench_sort, self.bench_evaluate))

        if main.Config.INDEX_MODE:
            io = None
            try:
                io = open(self.file_name, "wb")
                pickle.dump(self.hashes, io)
            except (IOError, AttributeError) as ex:
                print("Failed to save hashes: " + str(ex))
            finally:
                if io is not None:
                    io.close()

        return deep_move
        # debug("Starting negamax: turn " + str(self.board.turn) + ", color " + str(color))
        # start = time.time()
        # nega_move, nega_eval = self.negamax(self.depth, color, -math.inf, math.inf, True)
        # elapsed = time.time() - start
        #

        #
        # if nega_move is None:
        #     print("null move!")
        # else:
        #     debug(
        #         str(self.board.turn) + ", " + str(color) + ": " + nega_move.uci() + " = " + str(nega_eval) + " (" + str(
        #             elapsed) + " s, " + str(
        #             len(self.hashes)) + " hashes)")
        #     debug("Found move " + str(nega_move) + " for board: FEN " + str(self.board.fen()) + "\t hash " + str(
        #         zobrist_hash))
        #
        # self.bench_total = (time.time() - find_start)
        #
        # print("Benchmark ({} evals): index {}\tsort {}\tevals {}".format(self.bench_evals, self.bench_index,
        #                                                                  self.bench_sort, self.bench_evaluate))
        #
        # return nega_move


class MiniMaxMaterial(MiniMaxAbstract):

    def __init__(self, board: chess.Board, depth: int, *args, **kwargs):
        super().__init__(board, depth, *args, **kwargs)
        self.depth = depth
        self.eval_description = "Pure material values"

    def evaluate_board(self) -> int:
        return evaluate.evaluate_material(self.board)


class MiniMaxMobility(MiniMaxAbstract):

    def __init__(self, board: chess.Board, depth: int, *args, **kwargs):
        super().__init__(board, depth, *args, **kwargs)
        self.eval_description = "Pure mobility (number of legal moves)"

    def evaluate_board(self):
        if self.board.is_checkmate():
            return 1e9 if self.board.turn else -1e9
        if self.board.is_stalemate():
            return 0

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


# class MiniMaxPosition(MiniMaxAbstract):
#     def __init__(self, board: chess.Board, depth=3):
#         super().__init__(board, depth)
#         self.eval_description = "Pure positional values"
#
#     pos_pawn = [0, 0, 0, 0, 0, 0, 0, 0,
#                 50, 50, 50, 50, 50, 50, 50, 50,
#                 10, 10, 20, 30, 30, 20, 10, 10,
#                 5, 5, 10, 25, 25, 10, 5, 5,
#                 0, 0, 0, 20, 20, 0, 0, 0,
#                 5, -5, -10, 0, 0, -10, -5, 5,
#                 5, 10, 10, -20, -20, 10, 10, 5,
#                 0, 0, 0, 0, 0, 0, 0, 0]
#     pos_knight = [-50, -40, -30, -30, -30, -30, -40, -50,
#                   -40, -20, 0, 0, 0, 0, -20, -40,
#                   -30, 0, 10, 15, 15, 10, 0, -30,
#                   -30, 5, 15, 20, 20, 15, 5, -30,
#                   -30, 0, 15, 20, 20, 15, 0, -30,
#                   -30, 5, 10, 15, 15, 10, 5, -30,
#                   -40, -20, 0, 5, 5, 0, -20, -40,
#                   -50, -40, -30, -30, -30, -30, -40, -50]
#
#     pos_bishop = [-20, -10, -10, -10, -10, -10, -10, -20,
#                   -10, 0, 0, 0, 0, 0, 0, -10,
#                   -10, 0, 5, 10, 10, 5, 0, -10,
#                   -10, 5, 5, 10, 10, 5, 5, -10,
#                   -10, 0, 10, 10, 10, 10, 0, -10,
#                   -10, 10, 10, 10, 10, 10, 10, -10,
#                   -10, 5, 0, 0, 0, 0, 5, -10,
#                   -20, -10, -10, -10, -10, -10, -10, -20]
#
#     pos_rook = [0, 0, 0, 0, 0, 0, 0, 0,
#                 5, 10, 10, 10, 10, 10, 10, 5,
#                 -5, 0, 0, 0, 0, 0, 0, -5,
#                 -5, 0, 0, 0, 0, 0, 0, -5,
#                 -5, 0, 0, 0, 0, 0, 0, -5,
#                 -5, 0, 0, 0, 0, 0, 0, -5,
#                 -5, 0, 0, 0, 0, 0, 0, -5,
#                 0, 0, 0, 5, 5, 0, 0, 0]
#
#     pos_queen = [-20, -10, -10, -5, -5, -10, -10, -20,
#                  -10, 0, 0, 0, 0, 0, 0, -10,
#                  -10, 0, 5, 5, 5, 5, 0, -10,
#                  -5, 0, 5, 5, 5, 5, 0, -5,
#                  0, 0, 5, 5, 5, 5, 0, -5,
#                  -10, 5, 5, 5, 5, 5, 0, -10,
#                  -10, 0, 5, 0, 0, 0, 0, -10,
#                  -20, -10, -10, -5, -5, -10, -10, -20]
#
#     pos_king = [-30, -40, -40, -50, -50, -40, -40, -30,
#                 -30, -40, -40, -50, -50, -40, -40, -30,
#                 -30, -40, -40, -50, -50, -40, -40, -30,
#                 -30, -40, -40, -50, -50, -40, -40, -30,
#                 -20, -30, -30, -40, -40, -30, -30, -20,
#                 -10, -20, -20, -20, -20, -20, -20, -10,
#                 20, 20, 0, 0, 0, 0, 20, 20,
#                 20, 30, 10, 0, 0, 10, 30, 20]
#
#     def get_pos_value(self, piece: chess.Piece, pos: int):
#         piece_type = piece.piece_type
#         if piece_type == chess.BLACK:
#             pos = 63 - pos
#
#         if piece_type == chess.PAWN:
#             return self.pos_pawn[pos]
#         elif piece_type == chess.KNIGHT:
#             return self.pos_knight[pos]
#         elif piece_type == chess.BISHOP:
#             return self.pos_bishop[pos]
#         elif piece_type == chess.ROOK:
#             return self.pos_rook[pos]
#         elif piece_type == chess.QUEEN:
#             return self.pos_queen[pos]
#         elif piece_type == chess.KING:
#             return self.pos_king[pos]
#
#         raise Exception("Invalid piece " + str(piece))
#
#     def evaluate_board(self):
#         if self.board.is_checkmate():
#             return 1e9 if self.board.turn else -1e9
#         if self.board.is_stalemate():
#             return 0
#
#         total = 0
#
#         piece_map = self.board.piece_map()
#
#         for piece_index in piece_map.keys():
#             piece = piece_map[piece_index]
#             value = self.get_pos_value(piece, piece_index)
#             if piece.color == chess.BLACK:
#                 total -= value
#             else:
#                 total += value
#
#         return total


class MiniMaxComplex(MiniMaxAbstract):
    def __init__(self, board: chess.Board, depth: int, *args, **kwargs):
        super().__init__(board, depth, *args, **kwargs)
        self.eval_description = "Mixed position/material values"

    def evaluate_board(self):
        return evaluate.evaluate_complex(self.board)



import os

import random
from abc import ABC, abstractmethod

import chess
import chess.polyglot

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"


class Agent(ABC):

    # Used in puzzles.py
    passed = 0
    failed = 0
    elapsed = 0

    i_board: chess.Board = None

    def __init__(self, board: chess.Board):
        self.board = board
        self.eval_description = "Agent subclass never set eval description"

    @abstractmethod
    def find_move(self) -> chess.Move:
        pass


class RandomAgent(Agent):
    def __init__(self, board: chess.Board):
        super().__init__(board)
        self.eval_description = "Random moves"

    def find_move(self) -> chess.Move:
        return random.choice([move for move in self.board.legal_moves])


class BetterRandom(Agent):
    def __init__(self, board: chess.Board):
        super().__init__(board)
        self.eval_description = "Random moves, check/mate if possible"

    def find_move(self) -> chess.Move:
        legal_moves = self.board.legal_moves
        legal_captures = []

        for move in legal_moves:
            self.board.push(move)
            if self.board.is_checkmate():
                return move
            self.board.pop()

            if self.board.is_check() or self.board.is_capture(move):
                legal_captures.append(move)

        if len(legal_captures) > 0:
            return random.choice([capture for capture in legal_captures])
        else:
            return random.choice([move for move in legal_moves])


def make_opening_move(board: chess.Board):
    moves = []
    fen = board.fen()

    board = chess.Board(fen)

    for subdir, dirs, files in os.walk('openings'):
        for file in files:
            ext = os.path.splitext(file)[-1].lower()
            if ext in '.bin':
                with chess.polyglot.open_reader(os.path.join(subdir, file)) as reader:
                    for i, entry in enumerate(reader.find_all(board)):
                        moves.append(entry.move)

                        # Only pick from the most common openings
                        if i == 2:
                            break

    if moves:
        return random.choice(moves)
    else:
        return None

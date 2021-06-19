import random
import time

import chess
import chess.pgn

import main
from chessboard import display
import agent
import minimax


class PuzConfig:
    VALIDATE_TESTS = False  # Validate tests by assuming correct moves from puzzles

    LOAD_TESTS = 5000  # No. puzzles to read from file
    NUM_TESTS = 20  # No. puzzles to use
    BASIC_AGENTS = False # Toggle between minimax and basic agents

    RANDOM_SEED = 69  # Use static seed to load tests that that aren't the first X lines, but don't change between tests
    RANDOM_TESTS = True

    GUI = False
    GUI_PREVIEW = False

    MIN_RATING = 1501
    MAX_RATING = 1750

    MINIMAX_MIN_DEPTH = 1
    MINIMAX_MAX_DEPTH = 3


random.seed(PuzConfig.RANDOM_SEED)

if PuzConfig.LOAD_TESTS < PuzConfig.NUM_TESTS:
    PuzConfig.LOAD_TESTS = PuzConfig.NUM_TESTS

if PuzConfig.MINIMAX_MIN_DEPTH > PuzConfig.MINIMAX_MAX_DEPTH:
    PuzConfig.MINIMAX_MAX_DEPTH = PuzConfig.MINIMAX_MIN_DEPTH

def load_puzzles():
    # LiChess format: PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl
    file = open("puzzles/lichess_db_puzzle.csv", "r")

    # Sample line:
    # 000aY,r4rk1/pp3ppp/2n1b3/q1pp2B1/8/P1Q2NP1/1PP1PP1P/2KR3R w - - 0 15,g5e7 a5c3 b2c3 c6e7,1407,75,91,243,advantage master middlegame short,https://lichess.org/iihZGl6t#29

    puzzle_cache = []
    loaded_puzzles = 0

    total_ratings = 0
    for line_index, line in enumerate(file):
        if loaded_puzzles >= PuzConfig.LOAD_TESTS:
            break

        split = line.split(",")
        line_id = split[0]
        line_fen = split[1]
        line_moves = split[2]
        line_rating = split[3]
        line_rating_deviation = split[4]
        line_popularity = split[5]
        line_nb_plays = split[6]
        line_themes = split[7]
        line_gameurl = split[8]

        moves = line_moves.split(" ")
        rating = int(line_rating)
        rating_deviation = int(line_rating_deviation)
        popularity = int(line_popularity)
        plays = int(line_nb_plays)
        themes = line_themes.split(" ")

        if rating < PuzConfig.MIN_RATING or rating > PuzConfig.MAX_RATING:
            continue

        puzzle = Puzzle(line_id, line_fen, moves, rating, rating_deviation, popularity, plays, themes, line_gameurl)
        puzzle_cache.append(puzzle)

        loaded_puzzles += 1
        total_ratings += rating

    if len(puzzle_cache) < 1:
        print("WARN no puzzles loaded")
    else:
        print("Loaded {} puzzles. Average rating: {}".format(loaded_puzzles, (total_ratings / loaded_puzzles)))
    return puzzle_cache


class Puzzle:
    def __init__(self, iden: str, fen: str, uci_moves: [str], rating: int, rating_deviation: int, popularity: int,
                 plays: int,
                 themes: [str], url: str):
        self.iden = iden
        self.fen = fen
        self.moves: [chess.Move] = []
        self.rating = rating
        self.rating_deviation = rating_deviation
        self.popularity = popularity
        self.plays = plays
        self.themes = themes
        self.url = url
        self.solution_str = ""

        for uci in uci_moves:
            self.moves.append(chess.Move.from_uci(uci))
            self.solution_str = self.solution_str + " " + uci

        self.move_index = 0
        self.received_moves: [chess.Move] = []

        self.fail_reason: str = "No reason defined"
        self.failed = False

        self.is_mate_puzzle = False
        for theme in self.themes:
            if "mate" in theme.lower():
                self.is_mate_puzzle = True
                break

    def setup(self, p_board: chess.Board):
        p_board.clear()
        p_board.set_fen(self.fen)

        self.received_moves = []
        self.move_index = 0

        self.failed = False
        self.fail_reason = "No reason defined"

        initial_move = self.correct_next_move()
        self.receive_move(p_board, initial_move)

        if self.failed:
            self.fail_reason = "Puzzle setup failed: {}".format(self.fail_reason)

    def correct_next_move(self):
        return self.moves[self.move_index]

    def receive_move(self, receive_board: chess.Board, move_check: chess.Move):
        self.received_moves.append(move_check)

        if move_check is None:
            self.fail_reason = "No move returned"
            self.failed = True
        elif move_check.uci() != self.correct_next_move().uci():
            self.fail_reason = "Incorrect move " + move_check.uci()
            self.failed = True

        self.move_index += 1

        try:
            receive_board.push(move_check)
        except AssertionError:
            self.fail_reason = "Illegal move " + move_check.uci()
            self.failed = True
            return False

        if receive_board.is_checkmate():
            self.failed = False

        return not self.failed

    def is_complete(self):
        # Checkmate puzzles can be completed in multiple ways sometimes
        return self.move_index >= len(self.moves) or (self.failed and not self.is_mate_puzzle)


def hide_pieces():
    display.start("8/8/8/8/8/8/8/8 b - - 0 1")


def blink_display(blinks, fen):
    for b in range(0, blinks):
        hide_pieces()
        time.sleep(0.2)

        display.start(fen)
        time.sleep(0.2)


def preview_puzzle(previewing_board, previewing_puzzle):
    blink_display(2, previewing_puzzle.fen)
    while not previewing_puzzle.is_complete():
        time.sleep(2)

        preview_move = previewing_puzzle.correct_next_move()
        previewing_puzzle.receive_move(previewing_board, preview_move)

        display.start(previewing_board.fen())

    time.sleep(2)
    hide_pieces()
    time.sleep(2)


if __name__ == '__main__':
    main.Config.OPENING_BOOK = False

    if PuzConfig.VALIDATE_TESTS:
        PuzConfig.GUI = False
        PuzConfig.GUI_PREVIEW = False
        print("\n------------------------------------")
        print("-------  VALIDATING PUZZLES  -------")
        print("------------------------------------\n")

    if PuzConfig.LOAD_TESTS > 5000:
        print("Loading puzzles...")

    puzzles = load_puzzles()

    basic_agents = [agent.RandomAgent, agent.BetterRandom]
    minimax_agents = [minimax.MiniMaxMaterial, minimax.MiniMaxMobility, minimax.MiniMaxComplex]

    agents = []
    if PuzConfig.BASIC_AGENTS:
        for basic in basic_agents:
            agents.append(basic)
    else:
        for mini in minimax_agents:
            agents.append(mini)

    total_puzzles = min(len(puzzles), PuzConfig.NUM_TESTS)
    total_plies = 0
    passed = failed = 0

    for i in range(0, total_puzzles):
        if PuzConfig.RANDOM_TESTS:
            puz = random.choice([p for p in puzzles])
            puzzles.remove(puz)
        else:
            puz = puzzles[i]

        total_plies += len(puz.moves)
        board = chess.Board(puz.fen)

        print(
            "\nPuzzle {}/{}: {}\t\tRating: {}\t{}\tSolution: {}\tThemes:{}".format(i + 1, total_puzzles, puz.iden, puz.rating,
                                                                                 puz.url,
                                                                                 puz.solution_str, puz.themes))
        if PuzConfig.GUI_PREVIEW:
            preview_puzzle(board, puz)

        for i, agent_cls in enumerate(agents):
            agent_name = agent_cls.__name__
            depths = [-1]
            if "MiniMax" in agent_name:
                depths = [i for i in range(PuzConfig.MINIMAX_MIN_DEPTH, PuzConfig.MINIMAX_MAX_DEPTH + 1)]

            for depth in depths:
                if depth != -1:
                    agent = agent_cls(board, depth)
                else:
                    agent = agent_cls(board)

                if PuzConfig.GUI and (depth == -1 or depth == 1):
                    blink_display(1, puz.fen)
                    time.sleep(1)

                puz.setup(board)

                if PuzConfig.GUI and (depth == -1 or depth == 1):
                    display.start(board.board_fen())
                    time.sleep(1)

                if depth == -1 or depth == PuzConfig.MINIMAX_MIN_DEPTH:
                    print("\n\t{} - {}".format(agent_name, agent.eval_description))

                agent_turn = board.turn
                start_time = time.time()
                while not puz.is_complete():
                    if board.turn == agent_turn and not PuzConfig.VALIDATE_TESTS:
                        move = agent.find_move()
                    else:
                        move = puz.correct_next_move()

                    puz.receive_move(board, move)
                    if PuzConfig.GUI:
                        display.start(board.board_fen())
                        time.sleep(1)
                        start_time += 1

                elapsed = time.time() - start_time
                agent_cls.elapsed += elapsed

                agent_moves_str = ""
                for m in puz.received_moves:
                    agent_moves_str = agent_moves_str + " " + m.uci()

                if puz.failed:
                    result = "FAILED move {}: {}".format(puz.move_index, puz.fail_reason)
                    agent_cls.failed += 1
                    failed += 1
                else:
                    result = "PASSED"
                    agent_cls.passed += 1
                    passed += 1

                prefix = ""
                if depth != -1:
                    prefix = "Depth " + str(depth)
                else:
                    prefix = "Output"

                print("\t\t{}: {}".format(prefix, agent_moves_str))
                print("\t\t\t: {}: ({:.3f}s)".format(result, elapsed))

    if PuzConfig.VALIDATE_TESTS:
        print("\n------------------------------------")
        print("-------  VALIDATION RESULTS -------")
        print("------------------------------------\n")

    total_tests = passed + failed
    pass_rate = (passed / total_tests) * 100

    total_plies = total_plies / 2
    avg_puzzle_len = total_plies / total_puzzles

    print("\nSUMMARY \n\tTotal: passed {}/{} ({:.2f}%)".format(passed, total_tests, pass_rate))
    print("\tAvg. plies: {:.2f}".format(avg_puzzle_len))

    for agent in agents:
        agent_total = agent.passed + agent.failed
        agent_rate = (agent.passed / agent_total) * 100
        agent_avg_time = agent.elapsed / agent_total
        print("\t{}\t\t{}/{} ({:.2f}%) \n\t\tTime (avg): {:.4f}s\n\t\tTime (total): {:.4f}s".format(agent.__name__,
                                                                                                    agent.passed,
                                                                                                    agent_total,
                                                                                                    agent_rate,
                                                                                                    agent_avg_time,
                                                                                                    agent.elapsed))
    # \n({:.2f}% pass)"

# Puzzle 18/20: 04ilU		Rating: 1832	https://lichess.org/vfJTpFit/black#80
# 	Solution:  e7d7 g1f3 e4f3 e1d2 d7d6 d2e3	Themes:['crushing', 'endgame', 'long']
#
# 	RandomAgent - Random moves
# 		Output:  e7d7 e1f1
# 			⤷ FAILED move 2: Incorrect move e1f1: (0.000s)
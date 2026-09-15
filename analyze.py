import chess
import chess.pgn
import chess.engine

pgn_file = open("game.pgn")
game = chess.pgn.read_game(pgn_file)

engine = chess.engine.SimpleEngine.popen_uci("stockfish")

board = game.board()
previous_score = 0  # score before any moves

move_number = 0
for move in game.mainline_moves():
    move_number += 1
    player = "White" if board.turn == chess.WHITE else "Black"
    
    board.push(move)
    info = engine.analyse(board, chess.engine.Limit(time=0.2))
    score_obj = info["score"].white()
    
    # Convert score to a plain number (handle checkmate lines safely)
    if score_obj.is_mate():
        current_score = 10000 if score_obj.mate() > 0 else -10000
    else:
        current_score = score_obj.score()

    change = current_score - previous_score

    # Flag big swings as mistakes (threshold: 150 = 1.5 pawns worth)
    if abs(change) >= 150 and abs(previous_score) < 2000 and abs(current_score) < 2000:
        print(f"Move {move_number} ({player} played {move}): possible mistake! Eval swung by {change}")

    previous_score = current_score

engine.quit()
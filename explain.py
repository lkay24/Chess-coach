import time
import os
import chess
import chess.pgn
import chess.engine
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

game_name = input("Which game do you want to check? (e.g. game1, game2, game3): ")
pgn_file = open(f"games/{game_name}.pgn")
game = chess.pgn.read_game(pgn_file)

engine = chess.engine.SimpleEngine.popen_uci("stockfish")

board = game.board()
previous_score = 0
move_number = 0

for move in game.mainline_moves():
    move_number += 1
    player = "White" if board.turn == chess.WHITE else "Black"
    fen_before = board.fen()

    # Get Stockfish's suggested best move BEFORE playing the real move
    best = engine.play(board, chess.engine.Limit(time=0.3))
    better_move = best.move

    board.push(move)
    info = engine.analyse(board, chess.engine.Limit(time=0.2))
    score_obj = info["score"].white()

    if score_obj.is_mate():
        current_score = 10000 if score_obj.mate() > 0 else -10000
    else:
        current_score = score_obj.score()

    change = current_score - previous_score

    if abs(change) >= 150 and abs(previous_score) < 2000 and abs(current_score) < 2000:
        prompt = f"""
You are a chess coach. Here is a chess position in FEN notation:
{fen_before}

{player} played the move: {move}
A stronger move would have been: {better_move}

Explain in 2-3 simple sentences why {move} was a mistake compared to {better_move}.
Keep it beginner-friendly, no jargon.
"""
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        print(f"\n--- Move {move_number}: {player} played {move} ---")
        print(response.text)
        time.sleep(15)


    previous_score = current_score

engine.quit()
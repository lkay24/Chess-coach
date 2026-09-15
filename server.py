import os
import time
import io
import chess
import chess.pgn
import chess.engine
from dotenv import load_dotenv
from google import genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class GameRequest(BaseModel):
    pgn_text: str

def describe_defenders(board, square):
    """Checks direct AND backup (x-ray/battery) defenders/attackers of a square, using real chess logic."""
    piece_names = {
        chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop",
        chess.ROOK: "rook", chess.QUEEN: "queen", chess.KING: "king"
    }

    directions = [
        (1, 0), (-1, 0), (0, 1), (0, -1),      
        (1, 1), (1, -1), (-1, 1), (-1, -1)     
    ]

    is_diagonal = {(1,1), (1,-1), (-1,1), (-1,-1)}

    file_start = chess.square_file(square)
    rank_start = chess.square_rank(square)

    results = {chess.WHITE: [], chess.BLACK: []}

    for color in [chess.WHITE, chess.BLACK]:
        for sq in board.attackers(color, square):
            piece = board.piece_at(sq)
            results[color].append(f"{piece_names[piece.piece_type]} on {chess.square_name(sq)}")

    for (df, dr) in directions:
        f, r = file_start + df, rank_start + dr
        found_first = False
        while 0 <= f <= 7 and 0 <= r <= 7:
            sq = chess.square(f, r)
            piece = board.piece_at(sq)
            if piece:
                if not found_first:
                    found_first = True  
                else:
                    can_slide_this_way = (
                        piece.piece_type == chess.QUEEN or
                        (piece.piece_type == chess.ROOK and (df, dr) not in is_diagonal) or
                        (piece.piece_type == chess.BISHOP and (df, dr) in is_diagonal)
                    )
                    if can_slide_this_way:
                        label = f"{piece_names[piece.piece_type]} on {chess.square_name(sq)} (backup, behind another piece)"
                        results[piece.color].append(label)
                    break  
            f += df
            r += dr

    return {
        "square": chess.square_name(square),
        "defended_by_white": results[chess.WHITE],
        "defended_by_black": results[chess.BLACK]
    }

@app.post("/analyze")
def analyze_game(request: GameRequest):
    pgn_file = io.StringIO(request.pgn_text)
    game = chess.pgn.read_game(pgn_file)

    if game is None:
        return {"error": "Could not read this game. Check the PGN text."}

    engine = chess.engine.SimpleEngine.popen_uci("stockfish")

    board = game.board()
    previous_score = 0
    move_number = 0
    mistakes = []

    for move in game.mainline_moves():
        move_number += 1
        player = "White" if board.turn == chess.WHITE else "Black"
        fen_before = board.fen()

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
            destination_square = move.to_square
            defense_facts = describe_defenders(board, destination_square)
            prompt = f"""
You are a chess coach. Here is a chess position in FEN notation:
{fen_before}

{player} played the move: {move}
A stronger move would have been: {better_move}

VERIFIED FACTS about the square {defense_facts['square']} (use these facts exactly, do not guess or contradict them):
- Defended/attacked by White: {', '.join(defense_facts['defended_by_white']) if defense_facts['defended_by_white'] else 'nothing'}
- Defended/attacked by Black: {', '.join(defense_facts['defended_by_black']) if defense_facts['defended_by_black'] else 'nothing'}

Explain in 2-3 simple sentences why {move} was a mistake compared to {better_move}.
Keep it beginner-friendly, no jargon. Base any claim about a piece being defended or undefended strictly on the verified facts above.
"""
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                explanation = response.text
            except Exception as e:
                explanation = "Could not get an explanation right now (API limit reached). Try again shortly."

            mistakes.append({
                "move_number": move_number,
                "player": player,
                "move": str(move),
                "better_move": str(better_move),
                "explanation": explanation
            })
            time.sleep(15)

        previous_score = current_score

    engine.quit()
    return {"mistakes": mistakes}

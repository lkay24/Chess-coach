import chess
import chess.engine

# Set up a starting chess board
board = chess.Board()

# Connect to Stockfish
engine = chess.engine.SimpleEngine.popen_uci("stockfish")

# Ask Stockfish: what's the best move here?
result = engine.play(board, chess.engine.Limit(time=0.5))

print("Stockfish says the best move is:", result.move)

engine.quit()
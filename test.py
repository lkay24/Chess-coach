import chess
import chess.engine

board = chess.Board()

engine = chess.engine.SimpleEngine.popen_uci("stockfish")

result = engine.play(board, chess.engine.Limit(time=0.5))

print("Stockfish says the best move is:", result.move)

engine.quit()

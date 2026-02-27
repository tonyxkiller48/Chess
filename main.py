import chess
import chess.engine
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG =================
API_ID = 21635096
API_HASH = "4a4b6ffd717fcd895c3f71a1ad6aa712"
BOT_TOKEN = "8615950183:AAHyvQz8VUqiTLlSH8QUZDvGChiSjQf2ErE"

ENGINE_PATH = "/usr/games/stockfish"
PORT = 10000
# ==========================================

# ================= Flask ==================
web = Flask(__name__)

@web.route("/")
def home():
    return "Chess Bot Running!"

def run_web():
    web.run(host="0.0.0.0", port=PORT)
# ==========================================

# ================= Bot ====================
app = Client("chess_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
games = {}

def get_engine():
    return chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)

@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply("Choose your side:\n/white\n/black")

@app.on_message(filters.command("white"))
async def white(_, message: Message):
    games[message.from_user.id] = {
        "board": chess.Board(),
        "color": chess.WHITE
    }
    await message.reply("♟ Game started. You are White.")

@app.on_message(filters.command("black"))
async def black(_, message: Message):
    games[message.from_user.id] = {
        "board": chess.Board(),
        "color": chess.BLACK
    }
    await message.reply("♟ Game started. You are Black.")

@app.on_message(filters.command("new"))
async def new_game(_, message: Message):
    games.pop(message.from_user.id, None)
    await message.reply("Game reset. Use /white or /black")

@app.on_message(filters.command("undo"))
async def undo(_, message: Message):
    game = games.get(message.from_user.id)
    if not game or len(game["board"].move_stack) == 0:
        return await message.reply("Nothing to undo.")
    game["board"].pop()
    await message.reply("Last move undone.")

@app.on_message(filters.text & ~filters.command(["start", "white", "black", "new", "undo"]))
async def handle_move(_, message: Message):
    user_id = message.from_user.id

    if user_id not in games:
        return await message.reply("Start game first using /white or /black")

    board = games[user_id]["board"]
    user_color = games[user_id]["color"]
    move_text = message.text.strip()

    try:
        board.push_san(move_text)
    except:
        return await message.reply("Invalid move.")

    if board.turn == user_color:
        engine = get_engine()
        result = engine.analyse(board, chess.engine.Limit(depth=15))
        best_move = board.san(result["pv"][0])
        score = result["score"].relative
        engine.quit()

        await message.reply(
            f"♟ Best move: {best_move}\n"
            f"📊 Eval: {score}"
        )

# ==========================================

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    app.run()

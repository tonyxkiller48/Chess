import os
import io
import threading
import chess
import chess.engine
import chess.svg
import cairosvg
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG =================
API_ID = 21635096
API_HASH = "4a4b6ffd717fcd895c3f71a1ad6aa712"
BOT_TOKEN = "8615950183:AAHyvQz8VUqiTLlSH8QUZDvGChiSjQf2ErE"

ENGINE_PATH = "/usr/games/stockfish"
PORT = int(os.environ.get("PORT", 10000))
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
app = Client(
    "chess_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

games = {}

# ---------- Engine Creator ----------
def create_engine(elo=1800):
    engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
    engine.configure({
        "UCI_LimitStrength": True,
        "UCI_Elo": elo
    })
    return engine

# ---------- Start ----------
@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply(
        "♟ Welcome to Chess Bot\n\n"
        "Choose your side:\n"
        "/white\n"
        "/black\n\n"
        "Set strength (optional):\n"
        "/elo 1600\n"
        "/elo 1800\n"
        "/elo 2200"
    )

# ---------- Set ELO ----------
@app.on_message(filters.command("elo"))
async def set_elo(_, message: Message):
    user_id = message.from_user.id

    try:
        elo = int(message.command[1])
        if elo < 800 or elo > 3000:
            return await message.reply("Choose ELO between 800 - 3000")

        if user_id not in games:
            games[user_id] = {
                "board": chess.Board(),
                "color": chess.WHITE,
                "elo": elo
            }
        else:
            games[user_id]["elo"] = elo

        await message.reply(f"🤖 Engine strength set to {elo}")

    except:
        await message.reply("Usage: /elo 1800")

# ---------- Choose White ----------
@app.on_message(filters.command("white"))
async def white(_, message: Message):
    user_id = message.from_user.id

    games[user_id] = {
        "board": chess.Board(),
        "color": chess.WHITE,
        "elo": 1800
    }

    await message.reply("♟ Game started. You are White.")

    # Auto first move because White starts
    board = games[user_id]["board"]
    engine = create_engine(games[user_id]["elo"])

    result = engine.analyse(board, chess.engine.Limit(depth=15))
    best_move_obj = result["pv"][0]
    best_move = board.san(best_move_obj)

    board.push(best_move_obj)
    score = result["score"].relative
    engine.quit()

    await message.reply(
        f"♟ My first move: {best_move}\n"
        f"📊 Eval: {score}"
    )

# ---------- Choose Black ----------
@app.on_message(filters.command("black"))
async def black(_, message: Message):
    user_id = message.from_user.id

    games[user_id] = {
        "board": chess.Board(),
        "color": chess.BLACK,
        "elo": 1800
    }

    await message.reply("♟ Game started. You are Black.\nWaiting for opponent move.")

# ---------- New Game ----------
@app.on_message(filters.command("new"))
async def new_game(_, message: Message):
    games.pop(message.from_user.id, None)
    await message.reply("Game reset. Use /white or /black")

# ---------- Show Board ----------
@app.on_message(filters.command("board"))
async def show_board(_, message: Message):
    user_id = message.from_user.id

    if user_id not in games:
        return await message.reply("Start game first.")

    board = games[user_id]["board"]
    flipped = games[user_id]["color"] == chess.BLACK

    svg = chess.svg.board(
        board=board,
        size=500,
        flipped=flipped,
        lastmove=board.peek() if board.move_stack else None
    )

    png = cairosvg.svg2png(bytestring=svg.encode())
    bio = io.BytesIO(png)
    bio.name = "board.png"

    await message.reply_photo(bio)

# ---------- Handle Opponent Move ----------
@app.on_message(filters.text & ~filters.command(
    ["start","white","black","new","board","elo"]
))
async def handle_move(_, message: Message):
    user_id = message.from_user.id

    if user_id not in games:
        return await message.reply("Start game using /white or /black")

    board = games[user_id]["board"]
    user_color = games[user_id]["color"]
    elo = games[user_id]["elo"]

    # If it's engine's turn, block user
    if board.turn == user_color:
        return await message.reply("Waiting for opponent move.")

    try:
        board.push_san(message.text.strip())
    except:
        return await message.reply("Invalid move.")

    if board.is_game_over():
        return await message.reply("Game Over.")

    # Engine move
    if board.turn == user_color:
        engine = create_engine(elo)
        result = engine.analyse(board, chess.engine.Limit(depth=15))
        best_move_obj = result["pv"][0]
        best_move = board.san(best_move_obj)

        board.push(best_move_obj)
        score = result["score"].relative
        engine.quit()

        await message.reply(
            f"♟ My move: {best_move}\n"
            f"📊 Eval: {score}\n"
            f"🤖 Strength: {elo}"
        )

# ==========================================

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    app.run()

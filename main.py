import os
import io
import math
import threading
import chess
import chess.engine
import chess.svg
import cairosvg
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = 21635096
API_HASH = "4a4b6ffd717fcd895c3f71a1ad6aa712"
BOT_TOKEN = "8615950183:AAHyvQz8VUqiTLlSH8QUZDvGChiSjQf2ErE"

ENGINE_PATH = "/usr/games/stockfish"
PORT = int(os.environ.get("PORT", 10000))

web = Flask(__name__)

@web.route("/")
def home():
    return "Chess Bot Running!"

def run_web():
    web.run(host="0.0.0.0", port=PORT)

app = Client(
    "chess_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
engine.configure({
    "UCI_LimitStrength": True,
    "UCI_Elo": 1800
})

games = {}

def eval_to_winrate(score):
    if score.is_mate():
        return 100.0 if score.mate() > 0 else 0.0
    cp = score.score()
    if cp is None:
        return 50.0
    winrate = 100 / (1 + math.exp(-cp / 300))
    return round(winrate, 1)

def get_game_result(board):
    if board.is_checkmate():
        winner = "White" if board.turn == chess.BLACK else "Black"
        return f"🏁 Checkmate! {winner} wins."
    elif board.is_stalemate():
        return "🤝 Draw by stalemate."
    elif board.is_insufficient_material():
        return "🤝 Draw by insufficient material."
    elif board.can_claim_threefold_repetition():
        return "🤝 Draw by repetition."
    elif board.can_claim_fifty_moves():
        return "🤝 Draw by 50-move rule."
    return None

@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply(
        "♟ Choose mode:\n"
        "/mode notation\n"
        "/mode image\n\n"
        "Choose side:\n"
        "/white\n"
        "/black\n\n"
        "Set strength:\n"
        "/elo 1600"
    )

@app.on_message(filters.command("mode"))
async def set_mode(_, message: Message):
    user_id = message.from_user.id
    if len(message.command) < 2:
        return await message.reply("Usage: /mode notation OR /mode image")
    mode = message.command[1].lower()
    if mode not in ["notation", "image"]:
        return await message.reply("Choose notation or image")
    if user_id not in games:
        games[user_id] = {
            "board": chess.Board(),
            "color": chess.WHITE,
            "elo": 1800,
            "mode": mode
        }
    else:
        games[user_id]["mode"] = mode
    await message.reply(f"Mode set to {mode}")

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
                "elo": elo,
                "mode": "notation"
            }
        else:
            games[user_id]["elo"] = elo
        engine.configure({
            "UCI_LimitStrength": True,
            "UCI_Elo": elo
        })
        await message.reply(f"Engine strength set to {elo}")
    except:
        await message.reply("Usage: /elo 1800")

@app.on_message(filters.command("white"))
async def white(_, message: Message):
    user_id = message.from_user.id
    games[user_id] = {
        "board": chess.Board(),
        "color": chess.WHITE,
        "elo": 1800,
        "mode": games.get(user_id, {}).get("mode", "notation")
    }
    await message.reply("♟ Game started. You are White.")
    board = games[user_id]["board"]
    result = engine.analyse(board, chess.engine.Limit(time=0.35))
    best_move_obj = result["pv"][0]
    best_move = board.san(best_move_obj)
    board.push(best_move_obj)
    score = result["score"].relative
    mode = games[user_id]["mode"]
    if mode == "notation":
        await message.reply(f"♟ My first move: {best_move}\n📊 Eval: {score}")
    else:
        svg = chess.svg.board(
            board=board,
            size=500,
            lastmove=best_move_obj,
            fill={
                best_move_obj.from_square: "#4da6ff",
                best_move_obj.to_square: "#66ff66"
            }
        )
        png = cairosvg.svg2png(bytestring=svg.encode())
        bio = io.BytesIO(png)
        bio.name = "move.png"
        await message.reply_photo(bio, caption=f"♟ My first move: {best_move}\n📊 Eval: {score}")

@app.on_message(filters.command("black"))
async def black(_, message: Message):
    user_id = message.from_user.id
    games[user_id] = {
        "board": chess.Board(),
        "color": chess.BLACK,
        "elo": 1800,
        "mode": games.get(user_id, {}).get("mode", "notation")
    }
    await message.reply("♟ Game started. You are Black.\nWaiting for opponent move.")

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

@app.on_message(filters.command("win"))
async def win_probability(_, message: Message):
    user_id = message.from_user.id
    if user_id not in games:
        return await message.reply("Start game first.")
    board = games[user_id]["board"]
    result = engine.analyse(board, chess.engine.Limit(time=0.25))
    score = result["score"].relative
    winrate = eval_to_winrate(score)
    await message.reply(
        f"📊 Evaluation: {score}\n🔥 Win probability: {winrate}%"
    )

@app.on_message(filters.text & ~filters.command(
    ["start","white","black","mode","elo","board","win"]
))
async def handle_move(_, message: Message):
    user_id = message.from_user.id
    if user_id not in games:
        return await message.reply("Start game using /white or /black")
    board = games[user_id]["board"]
    user_color = games[user_id]["color"]
    mode = games[user_id]["mode"]
    if board.turn == user_color:
        return await message.reply("Waiting for opponent move.")
    try:
        board.push_san(message.text.strip())
    except:
        return await message.reply("Invalid move.")
    result_text = get_game_result(board)
    if result_text:
        return await message.reply(result_text)
    result = engine.analyse(board, chess.engine.Limit(time=0.35))
    best_move_obj = result["pv"][0]
    best_move = board.san(best_move_obj)
    board.push(best_move_obj)
    score = result["score"].relative
    result_text = get_game_result(board)
    if mode == "notation":
        await message.reply(
            f"♟ My move: {best_move}\n📊 Eval: {score}"
        )
    else:
        svg = chess.svg.board(
            board=board,
            size=500,
            flipped=(user_color == chess.BLACK),
            lastmove=best_move_obj,
            fill={
                best_move_obj.from_square: "#4da6ff",
                best_move_obj.to_square: "#66ff66"
            }
        )
        png = cairosvg.svg2png(bytestring=svg.encode())
        bio = io.BytesIO(png)
        bio.name = "move.png"
        await message.reply_photo(
            bio,
            caption=f"♟ My move: {best_move}\n📊 Eval: {score}"
        )
    if result_text:
        await message.reply(result_text)

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    app.run()

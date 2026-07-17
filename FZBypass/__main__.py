from FZBypass import Bypass, LOGGER, Config
from pyrogram import idle
from pyrogram.filters import command, user
from pyrogram.types import BotCommand
from os import path as ospath, execl
from asyncio import create_subprocess_exec
from sys import executable


@Bypass.on_message(command("restart") & user(Config.OWNER_ID))
async def restart(client, message):
    restart_message = await message.reply("<i>Restarting...</i>")
    await (await create_subprocess_exec("python3", "update.py")).wait()
    with open(".restartmsg", "w") as f:
        f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    try:
        execl(executable, executable, "-m", "FZBypass")
    except Exception:
        execl(executable, executable, "-m", "FZBypassBot/FZBypass")


async def restart():
    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        try:
            await Bypass.edit_message_text(
                chat_id=chat_id, message_id=msg_id, text="<i>Restarted !</i>"
            )
        except Exception as e:
            LOGGER.error(e)


Bypass.start()
LOGGER.info("FZ Bot Started!")
Bypass.loop.run_until_complete(restart())
Bypass.loop.run_until_complete(
    Bypass.set_bot_commands([
        BotCommand("start", "Bot info & usage"),
        BotCommand("bypass", "Bypass shortener/scrape link"),
        BotCommand("bp", "Shortcut for /bypass"),
        BotCommand("scrape", "Extract download links from movie sites"),
        BotCommand("log", "Get bot logs (owner only)"),
        BotCommand("restart", "Restart bot (owner only)"),
        BotCommand("bash", "Execute Python code (owner only)"),
        BotCommand("shell", "Execute shell command (owner only)"),
    ])
)
idle()
Bypass.stop()

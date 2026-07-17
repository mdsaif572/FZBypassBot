from time import time
from asyncio import create_task, gather, sleep as asleep
from re import findall as re_findall
from pyrogram.filters import command, user
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import MessageEntityType

from FZBypass import Config, Bypass, BOT_START
from FZBypass.core.bot_utils import AuthChatsTopics, convert_time, BypassFilter
from FZBypass.core.bypass_scrape_sites import scrape_site

URL_RE = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"


@Bypass.on_message(command("scrape") & (user(Config.OWNER_ID) | AuthChatsTopics))
async def scrape_handler(client, message):
    uid = message.from_user.id
    if (reply_to := message.reply_to_message) and (
        reply_to.text is not None or reply_to.caption is not None
    ):
        txt = reply_to.text or reply_to.caption
        entities = reply_to.entities or reply_to.caption_entities
    elif len(message.text.split()) > 1:
        txt = message.text
        entities = message.entities
    else:
        return await message.reply("<i>Usage: /scrape [url]</i>")

    wait_msg = await message.reply("<i>Scraping...</i>")
    start = time()

    urls = []
    if entities:
        for enty in entities:
            if enty.type == MessageEntityType.URL:
                link = txt[enty.offset : (enty.offset + enty.length)]
                urls.append(link)
            elif enty.type == MessageEntityType.TEXT_LINK:
                urls.append(enty.url)
    if not urls:
        found = re_findall(URL_RE, txt)
        urls = [u for u in found if u.startswith("http")]

    if not urls:
        return await wait_msg.edit("<i>No valid URLs found.</i>")

    results = []
    for url in urls:
        try:
            res = await Bypass.loop.run_in_executor(None, scrape_site, url, True)
            results.append(res)
        except Exception as e:
            results.append({"url": url, "error": str(e)})

    output = ""
    for res in results:
        if "error" in res:
            output += f"\n❌ <b>{res['url']}</b>\n┖ <code>{res['error']}</code>\n\n━━━━━━━✦✗✦━━━━━━━\n\n"
            continue
        output += f"\n📌 <b>{res['site']}</b> — <code>{res['title'][:80]}</code>\n"
        for blk in res["blocks"]:
            title = blk["title"][:100]
            sz = f" [{blk['size']}]" if blk.get("size") else ""
            qual = f" ({blk['quality']})" if blk.get("quality") else ""
            output += f"\n📦 <b>{title}</b>{qual}{sz}\n"
            for link in blk["links"]:
                output += f"┠ <a href='{link['url']}'><b>{link['host']}</b></a>\n"
                for r in link.get("resolved") or []:
                    output += f"┃ └ <a href='{r['url']}'>↳ {r['host']}</a>\n"
            output += "┃\n"
        output += f"\n━━━━━━━✦✗✦━━━━━━━\n\n"

        if len(output) > 3900:
            await wait_msg.edit(output, disable_web_page_preview=True)
            wait_msg = await message.reply("<i>More...</i>")
            output = ""
            await asleep(2)

    end = time()
    output += f"\n⏱ <b>Took {convert_time(end - start)}</b>"
    await wait_msg.edit(output, disable_web_page_preview=True)

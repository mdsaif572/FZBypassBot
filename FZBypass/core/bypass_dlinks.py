from base64 import b64decode
from asyncio import create_task, gather
from re import findall, DOTALL
from urllib.parse import urlparse
from uuid import uuid4

from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from lxml import etree
from requests import Session, get as rget
from aiohttp import ClientSession

from FZBypass import LOGGER, Config
from FZBypass.core.bot_utils import get_dl
from FZBypass.core.exceptions import DDLException


async def filepress(url: str):
    cget = create_scraper().request
    dl_link, tg_link = None, None
    name, size = "N/A", "N/A"
    try:
        url = cget("GET", url).url
        raw = urlparse(url)
        file_id = raw.path.split("/")[-1]
        async with ClientSession() as sess:
            json_data = {"id": file_id, "method": "publicDownlaod"}
            async with await sess.post(
                f"{raw.scheme}://{raw.hostname}/api/file/downlaod/",
                headers={"Referer": f"{raw.scheme}://{raw.hostname}"},
                json=json_data,
            ) as resp:
                d_id = await resp.json()
            if d_id.get("data", False):
                dl_link = f"https://drive.google.com/uc?id={d_id['data']}&export=download"
                soup = BeautifulSoup(cget("GET", dl_link).content, "html.parser")
                span = soup.find("span")
                if span:
                    combined = str(span).rsplit("(", maxsplit=1)
                    name = combined[0]
                    size = combined[1].replace(")", "").strip() + "B"
            del json_data["method"]
            async with await sess.post(
                f"{raw.scheme}://{raw.hostname}/api/file/telegram/downlaod/",
                headers={"Referer": f"{raw.scheme}://{raw.hostname}"},
                json=json_data,
            ) as resp:
                tg_id = await resp.json()
            if tg_id.get("data", False):
                t_url = f"https://tghub.xyz/?start={tg_id['data']}"
                bot_name = findall(
                    "filepress_[a-zA-Z0-9]+_bot", cget("GET", t_url).text
                )
                if bot_name:
                    tg_link = f"https://t.me/{bot_name[0]}/?start={tg_id['data']}"
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")

    parse_txt = f"""┏<b>Name:</b> <code>{name}</code>
┠<b>Size:</b> <code>{size}</code>
┠<b>FilePress:</b> <a href="{url}">Click Here</a>
"""
    if dl_link and Config.DIRECT_INDEX:
        parse_txt += f"┠<b>Temp Index:</b> <a href='{get_dl(dl_link)}'>Click Here</a>\n"
        parse_txt += f"┗<b>GDrive:</b> <a href='{dl_link}'>Click Here</a>"
    elif tg_link:
        parse_txt += f"┗<b>Telegram:</b> <a href='{tg_link}'>Click Here</a>"
    else:
        parse_txt += "┗<b>Telegram:</b> Unavailable"
    return parse_txt


async def gdtot(url):
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        p_url = urlparse(url)
        file_id = url.split("/")[-1]
        d_link = None

        # Method 1: Use crypt cookie + /dld endpoint (preferred, newer)
        if Config.GDTOT_CRYPT:
            cget("GET", url, cookies={"crypt": Config.GDTOT_CRYPT})
            js_script = cget(
                "GET",
                f"{p_url.scheme}://{p_url.hostname}/dld?id={file_id}",
            )
            g_id = findall("gd=(.*?)&", js_script.text)
            if g_id:
                try:
                    decoded_id = b64decode(str(g_id[0])).decode("utf-8")
                    d_link = f"https://drive.google.com/open?id={decoded_id}"
                except:
                    pass

        # Method 2: myDl regex from page HTML (works without crypt on some domains)
        if not d_link:
            main_page = cget("GET", url, cookies={"crypt": Config.GDTOT_CRYPT} if Config.GDTOT_CRYPT else {})
            drive_link = findall(r"myDl\('(.*?)'\)", main_page.text)
            if drive_link and "drive.google.com" in drive_link[0]:
                d_link = drive_link[0]

        if not d_link:
            raise DDLException(
                "Drive Link not found! Provide GDTOT_CRYPT or try in browser"
            )
    except DDLException:
        raise
    except IndexError:
        raise DDLException("File not found or user limit exceeded!")
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")
    soup = BeautifulSoup(cget("GET", url).content, "html.parser")
    meta = soup.select('meta[property^="og:description"]')
    if meta:
        parse_data = (
            meta[0]["content"].replace("Download ", "").rsplit("-", maxsplit=1)
        )
        name = parse_data[0]
        size = parse_data[-1]
    else:
        name = "N/A"
        size = "N/A"
    parse_txt = f"""┏<b>Name:</b> <code>{name}</code>
┠<b>Size:</b> <code>{size}</code>
┠<b>GDToT:</b> <a href="{url}">Click Here</a>
"""
    if Config.DIRECT_INDEX and d_link:
        parse_txt += f"┠<b>Temp Index:</b> <a href='{get_dl(d_link)}'>Click Here</a>\n"
    parse_txt += f"┗<b>GDrive:</b> <a href='{d_link}'>Click Here</a>"
    return parse_txt


async def drivescript(url, crypt, dtype):
    rs = Session()
    resp = rs.get(url)
    title_list = findall(r">(.*?)<\/h4>", resp.text)
    size_list = findall(r">(.*?)<\/td>", resp.text)
    title = title_list[0] if title_list else "N/A"
    size = size_list[1] if len(size_list) > 1 else "N/A"
    p_url = urlparse(url)
    file_id = str(url.split("/")[-1])

    dlink = ""
    if dtype != "DriveFire":
        try:
            js_query = rs.post(
                f"{p_url.scheme}://{p_url.hostname}/ajax.php?ajax=direct-download",
                data={"id": file_id},
                headers={"x-requested-with": "XMLHttpRequest"},
            ).json()
            if js_query.get("code") == "200":
                dlink = f"{p_url.scheme}://{p_url.hostname}{js_query['file']}"
        except Exception as e:
            LOGGER.error(e)

    if not dlink and crypt:
        rs.get(url, cookies={"crypt": crypt})
        try:
            js_query = rs.post(
                f"{p_url.scheme}://{p_url.hostname}/ajax.php?ajax=download",
                data={"id": file_id},
                headers={"x-requested-with": "XMLHttpRequest"},
            ).json()
            if js_query.get("code") == "200":
                dlink = f"{p_url.scheme}://{p_url.hostname}{js_query['file']}"
        except Exception as e:
            raise DDLException(f"{e.__class__.__name__}")

    if dlink:
        res = rs.get(dlink)
        soup = BeautifulSoup(res.text, "html.parser")
        gd_data = soup.select('a[class="btn btn-primary btn-user"]')
        parse_txt = f"""┏<b>Name:</b> <code>{title}</code>
┠<b>Size:</b> <code>{size}</code>
┠<b>{dtype}:</b> <a href="{url}">Click Here</a>"""
        if dtype == "HubDrive" and len(gd_data) > 1:
            parse_txt += f"""\n┠<b>Instant:</b> <a href="{gd_data[1]['href']}">Click Here</a>"""
        d_link = gd_data[0]["href"] if gd_data else None
        if d_link and Config.DIRECT_INDEX:
            parse_txt += f"\n┠<b>Temp Index:</b> <a href='{get_dl(d_link)}'>Click Here</a>"
        if d_link:
            parse_txt += f"\n┗<b>GDrive:</b> <a href='{d_link}'>Click Here</a>"
        else:
            parse_txt += "\n┗<b>GDrive:</b> Not Found"
        return parse_txt

    if not crypt:
        raise DDLException(f"{dtype} Crypt Not Provided and Direct Link Generate Failed")
    raise DDLException(f'{js_query.get("file", "Unknown error")}')


async def appflix_single_resolve(url):
    resp, _ = await _request_site(url)
    url = resp.url
    soup = BeautifulSoup(resp.text, "html.parser")
    ss = soup.select("li[class^='list-group-item']")
    name = "N/A"
    size = "N/A"
    if len(ss) > 0:
        parts = ss[0].string.split(":") if ss[0].string else []
        name = parts[1].strip() if len(parts) > 1 else ss[0].string.strip()
    if len(ss) > 2:
        parts = ss[2].string.split(":") if ss[2].string else []
        size = parts[1].strip() if len(parts) > 1 else ss[2].string.strip()
    if name == "N/A":
        h1 = soup.find("h1")
        if h1:
            name = h1.string.strip() if h1.string else "N/A"
        title_tag = soup.find("title")
        if name == "N/A" and title_tag:
            name = title_tag.string.strip() if title_tag.string else "N/A"
    dbotv2 = (
        dbot[0]["href"]
        if "gdflix" in url and (dbot := soup.select("a[href*='drivebot.lol']"))
        else None
    )
    try:
        d_link = await sharer_scraper(url)
    except Exception as e:
        if not dbotv2:
            raise DDLException(e)
        else:
            d_link = str(e)
    domain = urlparse(url).hostname or ""
    if d_link and d_link.startswith("http") and any(x in domain for x in ["driveapp", "drivehub", "gdflix", "drivesharer", "drivebit", "drivelinks", "driveace", "drivepro"]):
        try:
            resp = rget(d_link, allow_redirects=False, timeout=10)
            if resp.status_code in (301, 302, 303, 307, 308):
                d_link = resp.headers.get("Location", d_link)
            else:
                soup2 = BeautifulSoup(resp.text, "html.parser")
                btn_link = soup2.select('a[class*="btn"]')
                if btn_link:
                    d_link = btn_link[0].get("href", d_link)
        except:
            pass
    parse_txt = f"""┏<b>Name:</b> <code>{name}</code>
┠<b>Size:</b> <code>{size}</code>
┠<b>Source:</b> <code>{url}</code>"""
    if dbotv2:
        parse_txt += f"\n┠<b>DriveBot V2:</b> <a href='{dbotv2}'>Click Here</a>"
    if d_link and Config.DIRECT_INDEX and d_link.startswith("http"):
        parse_txt += f"\n┠<b>Temp Index:</b> <a href='{get_dl(d_link)}'>Click Here</a>"
    if d_link and d_link.startswith("http"):
        parse_txt += f"\n┗<b>GDrive:</b> <a href='{d_link}'>Click Here</a>"
    else:
        parse_txt += "\n┗<b>GDrive:</b> Unavailable"
    return parse_txt


async def appflix(url):
    if "/pack/" in url:
        cget = create_scraper().request
        url = cget("GET", url).url
        soup = BeautifulSoup(cget("GET", url).content, "html.parser")
        p_url = urlparse(url)
        body = ""
        atasks = [
            create_task(
                appflix_single_resolve(f"{p_url.scheme}://{p_url.hostname}" + ss["href"])
            )
            for ss in soup.select("a[href^='/file/'], a[href*='/file/']")
        ]
        completed_tasks = await gather(*atasks, return_exceptions=True)
        for bp_link in completed_tasks:
            if isinstance(bp_link, Exception):
                body += "\n\n" + f"<b>Error:</b> {bp_link}"
            else:
                body += "\n\n" + bp_link
        title = soup.title.string if soup.title else "N/A"
        return f"""┏<b>Name:</b> <code>{title}</code>
┗<b>Source:</b> <code>{url}</code>{body}"""
    return await appflix_single_resolve(url)


async def sharerpw(url: str, force=False):
    if not Config.XSRF_TOKEN and not Config.LARAVEL_SESSION:
        raise DDLException("XSRF_TOKEN or LARAVEL_SESSION not Provided!")
    cget = create_scraper(allow_brotli=False).request
    resp = cget(
        "GET",
        url,
        cookies={
            "XSRF-TOKEN": Config.XSRF_TOKEN,
            "laravel_session": Config.LARAVEL_SESSION,
        },
    )
    parse_txt = findall(r">(.*?)<\/td>", resp.text)
    ddl_btn = etree.HTML(resp.content).xpath("//button[@id='btndirect']")
    token = findall(r"_token\s=\s'(.*?)'", resp.text, DOTALL)[0]
    data = {"_token": token}
    if not force:
        data["nl"] = 1
    headers = {
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-requested-with": "XMLHttpRequest",
    }
    try:
        res = cget("POST", url + "/dl", headers=headers, data=data).json()
    except Exception as e:
        raise DDLException(str(e))
    parse_data = f"""┏<b>Name:</b> <code>{parse_txt[2]}</code>
┠<b>Size:</b> <code>{parse_txt[8]}</code>
┠<b>Added On:</b> <code>{parse_txt[11]}</code>
"""
    if res["status"] == 0:
        if Config.DIRECT_INDEX:
            parse_data += (
                f"\n┠<b>Temp Index:</b> <a href='{get_dl(res['url'])}'>Click Here</a>"
            )
        return parse_data + f"\n┗<b>GDrive:</b> <a href='{res['url']}'>Click Here</a>"
    elif res["status"] == 2:
        msg = res["message"].replace("<br/>", "\n")
        return parse_data + f"\n┗<b>Error:</b> {msg}"
    if len(ddl_btn) and not force:
        return await sharerpw(url, force=True)


async def _request_site(url, max_retries=2):
    try:
        from curl_cffi.requests import Session as cSession
        sess = cSession()
        resp = sess.get(url, impersonate="chrome110", timeout=30, allow_redirects=True)
        if resp.status_code == 200 and "Just a moment" not in resp.text:
            return resp, "curl_cffi"
    except ImportError:
        pass
    except Exception:
        pass
    cget = create_scraper().request
    for _ in range(max_retries):
        try:
            resp = cget("GET", url)
            if resp.status_code == 200 and "Just a moment" not in resp.text:
                return resp, "cloudscraper"
        except Exception:
            pass
    raise DDLException("Site blocked by Cloudflare")


async def sharer_scraper(url):
    resp, engine = await _request_site(url)
    url = resp.url
    raw = urlparse(url)
    key = findall(r'"key",\s+"(.*?)"', resp.text)
    if not key:
        raise DDLException("Download Link Key not found!")
    key = key[0]
    boundary = uuid4()
    headers = {
        "Content-Type": f"multipart/form-data; boundary=----WebKitFormBoundary{boundary}",
        "x-token": raw.hostname,
        "useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10",
    }
    data = (
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n'
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n'
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action_token"\r\n\r\n\r\n'
        f"------WebKitFormBoundary{boundary}--\r\n"
    )
    res = None
    try:
        if engine == "curl_cffi":
            from curl_cffi.requests import Session as cSession
            sess = cSession()
            res = sess.post(
                url,
                data=data,
                headers=headers,
                impersonate="chrome110",
                timeout=30
            ).json()
        else:
            cget = create_scraper().request
            res = cget("POST", url, cookies=resp.cookies, headers=headers, data=data).json()
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")
    if "url" not in res:
        raise DDLException("Drive Link not found, Try in your browser")
    if "drive.google.com" in res["url"]:
        return res["url"]
    try:
        if engine == "curl_cffi":
            from curl_cffi.requests import Session as cSession
            sess = cSession()
            resp2 = sess.get(res["url"], impersonate="chrome110", timeout=30)
        else:
            cget = create_scraper().request
            resp2 = cget("GET", res["url"])
    except Exception as e:
        raise DDLException(f"ERROR: {e.__class__.__name__}")
    if (
        drive_link := etree.HTML(resp2.content).xpath("//a[contains(@class,'btn')]/@href")
    ) and "drive.google.com" in drive_link[0]:
        return drive_link[0]
    else:
        raise DDLException("Drive Link not found, Try in your browser")

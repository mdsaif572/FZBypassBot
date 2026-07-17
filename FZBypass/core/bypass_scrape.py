from asyncio import gather, create_task, sleep as asleep
from re import search, match, sub
from requests import get as rget
from cloudscraper import create_scraper
from urllib.parse import urlparse
from bs4 import BeautifulSoup, NavigableString, Tag

from FZBypass.core.bypass_ddl import transcript
from FZBypass.core.exceptions import DDLException


async def sharespark(url: str) -> str:
    gd_txt = ""
    cget = create_scraper().request
    try:
        res = cget("GET", "?action=printpage;".join(url.split("?")))
    except:
        raise DDLException("Failed to fetch sharespark page")
    soup = BeautifulSoup(res.text, "html.parser")
    for br in soup.findAll("br"):
        next_s = br.nextSibling
        if not (next_s and isinstance(next_s, NavigableString)):
            continue
        if (
            (next2_s := next_s.nextSibling)
            and isinstance(next2_s, Tag)
            and next2_s.name == "br"
            and str(next_s).strip()
        ):
            if match(r"^(480p|720p|1080p)(.+)? Links:\Z", next_s):
                gd_txt += f'<b>{next_s.replace("Links:", "GDToT Links :")}</b>\n\n'
            for s in next_s.split():
                ns = sub(r"\(|\)", "", s)
                if match(r"https?://.+\.gdtot\.\S+", ns):
                    try:
                        soup2 = BeautifulSoup(cget("GET", ns).text, "html.parser")
                        meta = soup2.select('meta[property^="og:description"]')
                        if meta:
                            parse_data = (
                                meta[0]["content"]
                                .replace("Download ", "")
                                .rsplit("-", maxsplit=1)
                            )
                            gd_txt += f"┎ <b>Name :</b> {parse_data[0]}\n┠ <b>Size :</b> {parse_data[-1]}\n┃\n┖ <b>GDTot :</b> {ns}\n\n"
                    except:
                        gd_txt += f"┖ <b>GDTot :</b> {ns}\n\n"
                elif match(r"https?://pastetot\.\S+", ns):
                    nxt = sub(r"\(|\)|(https?://pastetot\.\S+)", "", next_s)
                    gd_txt += f"\n<b>{nxt}</b>\n┖ {ns}\n"
        if len(gd_txt) > 4000:
            return gd_txt
    if gd_txt != "":
        return gd_txt
    return "<i>No links found on this page</i>"


async def skymovieshd(url: str) -> str:
    try:
        resp = rget(url, allow_redirects=False, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
    except:
        raise DDLException("Failed to fetch skymovieshd page")
    t = soup.select('div[class^="Robiul"]')
    gd_txt = f"<i>{t[-1].text.replace('Download ', '') if t else 'N/A'}</i>"
    _cache = []
    for link in soup.select('a[href*="howblogs.xyz"], a[href*="gada.xyz"]'):
        if link["href"] in _cache:
            continue
        _cache.append(link["href"])
        gd_txt += f"\n\n<b>{link.text} :</b> \n"
        try:
            nsoup = BeautifulSoup(
                rget(link["href"], allow_redirects=False, timeout=30).text, "html.parser"
            )
            atag = nsoup.select('div[class="cotent-box"] > a[href]')
            for no, link_en in enumerate(atag, start=1):
                gd_txt += f"{no}. {link_en['href']}\n"
        except:
            gd_txt += "Failed to fetch\n"
    return gd_txt if gd_txt else "<i>No links found</i>"


async def cinevood(url: str) -> str:
    try:
        resp = rget(url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
    except:
        raise DDLException("Failed to fetch cinevood page")
    titles = soup.select("h6, h5, h4")

    post_title = soup.title.string.strip() if soup.title else "N/A"

    links_by_title = {}
    for title in titles:
        title_text = title.text.strip()
        if not title_text:
            continue
        link_targets = ["gdtot", "multiup", "filepress", "gdflix", "kolop", "zipylink", "filebee"]
        found_links = []
        for target in link_targets:
            link = title.find_next("a", href=lambda h: h and target in h.lower())
            if link:
                found_links.append(
                    f'<a href="{link["href"]}"><b>{target.title()}</b></a>'
                )
        if found_links:
            links_by_title[title_text] = found_links

    prsd = f"<b>Title:</b> {post_title}\n"
    for title, links in links_by_title.items():
        prsd += f"\n┏<b>Name:</b> <code>{title}</code>\n"
        prsd += "┗<b>Links:</b> " + " | ".join(links) + "\n"

    if not links_by_title:
        prsd += "\n<i>No download links found on this page</i>"
    return prsd


async def kayoanime(url: str) -> str:
    try:
        resp = rget(url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
    except:
        raise DDLException("Failed to fetch kayoanime page")
    titles = soup.select("h6, h5")
    gdlinks = soup.select('a[href*="drive.google.com"], a[href*="tinyurl"], a[href*="mega"]')
    prsd = f"<b>{soup.title.string if soup.title else 'N/A'}</b>"
    gd_txt = "GDrive"
    link = ""
    for n, gd in enumerate(gdlinks, start=1):
        if not gd.get("href"):
            continue
        link = gd["href"]
        if "tinyurl" in link:
            try:
                link = rget(link, timeout=10).url
            except:
                pass
            domain = urlparse(link).hostname or ""
            gd_txt = "Mega" if "mega" in domain else "G Group" if "groups" in domain else "Direct Link"
        elif "mega" in link:
            gd_txt = "Mega"
        else:
            gd_txt = "GDrive"
        prsd += f"""

{n}. <i><b>{gd.string or 'Link'}</b></i>
┗ <b>Links :</b> <a href='{link}'><b>{gd_txt}</b></a>"""
    if gdlinks:
        return prsd
    return f"{prsd}\n\n<i>No download links found</i>"


async def toonworld4all(url: str):
    try:
        if "/redirect/main.php?url=" in url:
            return f"┎ <b>Source Link:</b> {url}\n┃\n┖ <b>Bypass Link:</b> {rget(url, timeout=10).url}"
    except:
        raise DDLException("Failed to fetch redirect")
    try:
        resp = rget(url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
    except:
        raise DDLException("Failed to fetch toonworld4all page")
    if "/episode/" not in url:
        epl = soup.select('a[href*="/episode/"]')
        tls = soup.select('div[class*="mks_accordion_heading"], h5, h4')
        stitle_match = search(r"\"name\":\"(.+?)\"", resp.text)
        stitle = stitle_match.group(1) if stitle_match else (soup.title.string if soup.title else "N/A")
        prsd = f"<b><i>{stitle}</i></b>"
        for n, (t, l) in enumerate(zip(tls, epl), start=1):
            title_text = t.strong.string if t.strong else t.string
            prsd += f"""
        
{n}. <i><b>{title_text or 'Episode'}</b></i>
┖ <b>Link :</b> {l["href"]}"""
        return prsd
    links = soup.select('a[href*="/redirect/main.php?url="], a[href*="redirect"]')
    titles = soup.select("h5, h4")
    if not titles:
        return "<i>No episode titles found</i>"
    prsd = f"<b><i>{titles[0].string or 'N/A'}</i></b>"
    titles = titles[1:] if len(titles) > 1 else []
    if not links or not titles:
        return f"{prsd}\n\n<i>No episode links found</i>"
    slicer, _ = divmod(len(links), len(titles))
    atasks = []
    for sl in links:
        try:
            nsl = rget(sl["href"], allow_redirects=False, timeout=10).headers.get("location", "")
            max_redirects = 5
            while max_redirects > 0 and all(x not in nsl for x in ["rocklinks", "link1s"]):
                if not nsl:
                    break
                try:
                    nsl = rget(nsl, allow_redirects=False, timeout=10).headers.get("location", "")
                except:
                    break
                max_redirects -= 1
            if "rocklinks" in nsl:
                atasks.append(
                    create_task(
                        transcript(nsl, "https://land.povathemes.com/", "https://blog.disheye.com/", 5)
                    )
                )
            elif "link1s" in nsl:
                atasks.append(
                    create_task(transcript(nsl, "https://link1s.com", "https://anhdep24.com/", 9))
                )
            else:
                atasks.append(create_task(asleep(0)))
        except:
            atasks.append(create_task(asleep(0)))

    com_tasks = await gather(*atasks, return_exceptions=True)
    lstd = [com_tasks[i : i + slicer] for i in range(0, len(com_tasks), slicer)]

    for no, tl in enumerate(titles):
        prsd += f"\n\n<b>{tl.string or 'N/A'}</b>\n┃\n┖ <b>Links :</b> "
        for sl in lstd[no] if no < len(lstd) else []:
            if isinstance(sl, Exception):
                prsd += str(sl)
            else:
                prsd += f"<a href='{sl}'>Link</a>, "
        prsd = prsd.rstrip(", ")
    return prsd


async def tamilmv(url):
    cget = create_scraper().request
    try:
        resp = cget("GET", url, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
    except:
        raise DDLException("Failed to fetch tamilmv page")
    mag = soup.select('a[href^="magnet:?xt=urn:btih:"]')
    tor = soup.select('a[data-fileext="torrent"], a[href$=".torrent"]')
    if not mag and not tor:
        return f"<b><u>{soup.title.string if soup.title else 'N/A'}</u></b>\n\n<i>No magnet or torrent links found</i>"
    parse_data = f"<b><u>{soup.title.string if soup.title else 'N/A'}</u></b>"
    for no, (t, m) in enumerate(zip(tor, mag), start=1):
        filename = sub(r"www\S+|\- |\.torrent", "", t.string) if t.string else f"File {no}"
        parse_data += f"""
        
{no}. <code>{filename}</code>
┖ <b>Links :</b> <a href="https://t.me/share/url?url={m['href'].split('&')[0]}"><b>Magnet</b></a> | <a href="{t['href']}"><b>Torrent</b></a>"""
    for extra_m in mag[len(tor):]:
        no += 1
        parse_data += f"""
        
{no}. <b>Magnet:</b> <a href="{extra_m['href']}"><b> Magnet</b></a>"""
    for extra_t in tor[len(mag):]:
        no += 1
        filename = sub(r"www\S+|\- |\.torrent", "", extra_t.string) if extra_t.string else f"File {no}"
        parse_data += f"""
        
{no}. <code>{filename}</code>
┖ <b>Torrent:</b> <a href="{extra_t['href']}"><b>Torrent</b></a>"""
    return parse_data


async def clicknupload(url: str) -> str:
    from FZBypass.core.bypass_dlinks import _request_site
    import re as _re

    resp, _ = await _request_site(url)
    url = resp.url
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "N/A"
    form = soup.find("form")
    if not form:
        raise DDLException("clicknupload: No form found")
    data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if name:
            data[name] = inp.get("value", "")
    data.pop("method_free", None)
    data.pop("method_premium", None)
    data["method_free"] = "Slow Download"
    cget = create_scraper().request
    resp2 = cget("POST", url, data=data, allow_redirects=True)
    dl_match = _re.search(r'<a href="(https?://[^"]+)"[^>]*>Click here to download</a>', resp2.text, _re.I)
    if dl_match:
        dl_link = dl_match.group(1)
    else:
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        for a in soup2.find_all("a"):
            href = a.get("href", "")
            txt = a.get_text(strip=True).lower()
            if "download" in txt and href and href != "#" and "payments" not in href and "javascript" not in href:
                dl_link = href
                break
        else:
            raise DDLException("clicknupload: Download link not found (may require premium)")
    if "clicknupload.click" in dl_link:
        dl_link = dl_link.replace("clicknupload.click", "clicknupload.cam")
    parse_txt = f"""┏<b>Name:</b> <code>{title}</code>
┠<b>Source:</b> <code>{url}</code>
┖<b>Link:</b> <a href='{dl_link}'>Download</a>"""
    return parse_txt


async def hubcloud(url: str) -> str:
    from FZBypass.core.bypass_dlinks import _request_site
    from curl_cffi.requests import Session as cSession
    from datetime import datetime
    import re

    resp, _ = await _request_site(url)
    url = resp.url
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else "N/A"
    php_match = re.search(r"var url = '(.+?)'", resp.text)
    if not php_match:
        raise DDLException("hubcloud: PHP redirect URL not found")
    php_url = php_match.group(1)
    sess = cSession()
    php_resp = sess.get(php_url, impersonate="chrome110", timeout=30)
    php_soup = BeautifulSoup(php_resp.text, "html.parser")
    fsl = php_soup.find("a", id="fsl")
    if not fsl:
        raise DDLException("hubcloud: Download link not found")
    dl_link = fsl.get("href")
    if dl_link and "+" in php_resp.text:
        mins = datetime.now().minute
        dl_link += f"1{mins}"
    parse_txt = f"""┏<b>Name:</b> <code>{title}</code>
┠<b>Source:</b> <code>{url}</code>
┖<b>Link:</b> <a href='{dl_link}'>Download</a>"""
    return parse_txt

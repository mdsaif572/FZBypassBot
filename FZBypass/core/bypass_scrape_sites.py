import re, json, base64, time
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import cloudscraper
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    curl_requests = None
    HAS_CURL_CFFI = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
TIMEOUT = 30
MAX_WORKERS = 5

DOWNLOAD_HOSTS = [
    ("hubcloud", "HubCloud"), ("hubdrive", "HubDrive"), ("gdflix", "GDFlix"),
    ("gdtot", "GDToT"), ("filepress", "FilePress"), ("appdrive", "AppDrive"),
    ("sharespark", "ShareSpark"), ("nexdrive", "NexDrive"), ("vgmlinks", "VegaLinks"),
    ("fast-dl", "FastDL"), ("driveleech", "DriveLeech"), ("driveseed", "DriveSeed"),
    ("vcloud", "VCloud"), ("gofile", "GoFile"), ("pixeldrain", "PixelDrain"),
    ("mega.nz", "Mega"), ("drive.google", "GDrive"), ("bollydrive", "BollyDrive"),
    ("gamerxyt", "HubCloud"), ("modpro.blog", "ModPro"), ("m4ulinks", "M4ULinks"),
    ("howblogs", "HowBlogs"), ("send.now", "SendNow"), ("megaup", "MegaUp"),
    ("dropgalaxy", "DropGalaxy"), ("linkshub", "LinksHub"),
    ("inshorturl", "InShortURL"), ("mobilejsr", "MobileJSR"),
    ("acortalink", "AcortaLink"), ("ol-am.top", "OlaLinks"),
    ("links.olamovies", "OlaLinks"), ("mrfastcdn.xyz", "FastCDN"),
]

INTERMEDIATE_HOSTS = (
    "nexdrive", "fast-dl", "vgmlinks", "hubcloud", "hubdrive", "driveleech",
    "driveseed", "vcloud", "gdflix", "gdtot", "filepress", "sharespark",
    "tinyurl", "shorturl", "bit.ly", "cutt.ly", "rb.gy", "gyanilinks",
    "linkmake", "urlshortx", "shortlink", "inshorturl", "gamerxyt", ".php",
    "modpro.blog", "m4ulinks", "howblogs", "linkshub", "mobilejsr", "mrfastcdn.xyz",
)

DIRECT_RE = re.compile(
    r'(\.mkv|\.mp4|\.avi|\.mov|\.wmv|\.zip|\.rar|\.iso|'
    r'workers\.dev/|r2\.dev/|pixeldrain\.com/api/|'
    r'[?&]export=download|googleusercontent\.com/|\.b-cdn\.net/)', re.I)

ASSET_RE = re.compile(
    r'(\.js|\.css|\.png|\.jpe?g|\.gif|\.svg|\.ico|\.webp|\.woff2?|\.ttf|\.eot|'
    r'/template/|/fonts?/|/assets?/|/static/|recaptcha|bootstrap|jquery|'
    r'html5shiv|respond\.js|glyphicons|maxcdn)', re.I)

NAV_RE = re.compile(
    r'(category/|author/|/tag/|/page/|comments?/|#respond|#comment|'
    r'wp-content|wp-login|wp-admin|/feed|privacy|contact|about|dmca|'
    r'disclaimer|telegram|t\.me/|whatsapp|/how-to|login|register|'
    r'/admin|/sign|/profile|/settings|/account|/report|'
    r'cdn-cgi|email-protection|/policy|copyright-policy|/subtitles|'
    r'/file/XxXxXx|howblogs\.xyz/drive/?$)', re.I)

SITEMAP = {
    "supplygang.live": "SupplyGang", "supplygang.site": "SupplyGang",
    "themoviesflix.wtf": "MoviesFlix", "themoviesflix": "MoviesFlix",
    "vegamovies.navy": "VegaNavy", "extraflix.mobi": "ExtraFlix",
    "extraflix": "ExtraFlix", "1cinevood.live": "1CineVood",
    "1cinevood": "1CineVood", "4khdhub.one": "4KHDHub",
    "4khdhub.link": "4KHDHub",
    "hdhub4u.download": "HDHub4U", "hdhub4u.support": "HDHub4U",
    "hdhub4u.zip": "HDHub4U", "hdhub4u.digital": "HDHub4U",
    "hdhub4u.lol": "HDHub4U", "hdhub4u.in": "HDHub4U",
    "vegamovies.nz": "VegaMovies", "vegamovies.to": "VegaMovies",
    "vegamovies.yt": "VegaMovies", "vegamovie.su": "VegaMovies",
    "vegamovie": "VegaMovies", "katmoviehd.se": "KatMovieHD",
    "katmoviehd.pm": "KatMovieHD", "moviesmod.life": "MoviesMod",
    "moviesmod.food": "MoviesMod", "moviesmod.at": "MoviesMod",
    "moviezaddiction.com": "MoviezAddiction",
    "moviezaddiction.in": "MoviezAddiction",
    "moviezflixtor.com": "MoviezFlix", "filmyzilla46.com": "FilmiZilla",
    "filmizilla.com": "FilmiZilla", "filmyzilla.in": "FilmiZilla",
    "downloadhub.bid": "DownloadHub", "downloadhub.pm": "DownloadHub",
    "hackstore.fo": "HackStore", "hackstore.net": "HackStore",
    "hackstore.store": "HackStore", "mega1080p.org": "Mega1080p",
    "moviesnation.xyz": "MoviesNation", "moviesnation.land": "MoviesNation",
    "uhdmovies.tech": "UHDMovies", "movieforhd.com": "MovieForHD",
    "movieskiduniya.in": "MoviesKiDuniya", "9xmovies.life": "9xMovies",
    "bollyflix.life": "BollyFlix", "ssrmovies.org": "SSRMovies",
    "todaymovie.fun": "TodayMovie", "xdmovies.wtf": "XDMovies",
    "movies4u.clinic": "Movies4U", "movies4u.foo": "Movies4U",
    "movies4u.review": "Movies4U", "movies4u.ist": "Movies4U",
    "movies4u.gift": "Movies4U", "movies4u.trade": "Movies4U",
    "skymovieshd.ceo": "SkyMoviesHD", "skymovieshd": "SkyMoviesHD",
    "olamovies.mov": "OlaMovies", "olamovies.top": "OlaMovies",
    "olamovies": "OlaMovies", "ol-am.top": "OlaMovies",
    "cloudmoviez.shop": "CloudMoviez", "cloudmoviez.top": "CloudMoviez",
    "cloudmoviez": "CloudMoviez",
}


def host_label(href):
    low = href.lower()
    for key, label in DOWNLOAD_HOSTS:
        if key in low:
            return label
    return None


def _is_direct(url):
    if ASSET_RE.search(url):
        return False
    return bool(DIRECT_RE.search(url)) or url.lower().split("?")[0].endswith(
        (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".zip", ".rar", ".iso"))


def _next_hops(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()

    def add(href, text=""):
        href = (href or "").strip()
        if not href or href in seen:
            return
        href = href.split("#")[0]
        if href.startswith("/"):
            p = urlparse(base_url)
            href = f"{p.scheme}://{p.netloc}{href}"
        if not href.startswith("http") or ASSET_RE.search(href) or NAV_RE.search(href):
            return
        if href in seen:
            return
        seen.add(href)
        path = urlparse(href).path.strip("/")
        label = "Direct" if _is_direct(href) else host_label(href)
        if not label:
            return
        if label != "Direct" and not path:
            return
        out.append({"url": href, "host": label, "text": text[:40]})

    for a in soup.find_all("a", href=True):
        add(a["href"], a.get_text(" ", strip=True))
    for m in re.findall(r'https?://[^\s"\'<>\\]+', html):
        add(m)
    return out


def resolve_chain(url, depth=2, timeout=12):
    found, visited = [], set()

    def _fetch_page(u):
        try:
            resp = requests.get(u, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if resp.status_code in (403, 503):
                raise requests.exceptions.HTTPError(f"CF block {resp.status_code}")
            return resp
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return None
        except requests.exceptions.HTTPError:
            pass
        try:
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(u, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp
        except Exception:
            pass
        if HAS_CURL_CFFI:
            try:
                s = curl_requests.Session()
                parsed = urlparse(u)
                base = f"{parsed.scheme}://{parsed.netloc}"
                s.get(base, impersonate='chrome124', timeout=15)
                resp = s.get(u, impersonate='chrome124', timeout=timeout, allow_redirects=True)
                return resp
            except Exception:
                pass
        return None

    def walk(u, d):
        if d < 0 or u in visited or len(found) >= 12:
            return
        visited.add(u)
        resp = _fetch_page(u)
        if resp is None:
            return
        final = resp.url
        if _is_direct(final) and final not in visited:
            found.append({"url": final, "host": "Direct"})
        for hop in _next_hops(resp.text, final):
            if hop["url"] in visited:
                continue
            entry = {"url": hop["url"], "host": hop["host"]}
            if entry not in found:
                found.append(entry)
            low = hop["url"].lower()
            if hop["host"] != "Direct" and any(k in low for k in INTERMEDIATE_HOSTS):
                walk(hop["url"], d - 1)

    walk(url, depth)
    uniq, seen = [], set()
    for e in sorted(found, key=lambda x: 0 if x["host"] == "Direct" else 1):
        if e["url"] not in seen:
            seen.add(e["url"])
            uniq.append(e)
    return uniq[:12]


def resolve_blocks(blocks, max_links=24):
    jobs = []
    for b in blocks:
        for l in b["links"]:
            if any(k in l["url"].lower() for k in INTERMEDIATE_HOSTS):
                jobs.append(l)
    jobs = jobs[:max_links]
    if not jobs:
        return blocks
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        fut = {ex.submit(resolve_chain, l["url"]): l for l in jobs}
        for f in as_completed(fut):
            try:
                res = f.result()
            except Exception:
                res = []
            fut[f]["resolved"] = res
    return blocks


class SiteScraper:
    @staticmethod
    def detect(url):
        domain = urlparse(url).netloc.lower()
        domain = re.sub(r'^www\.', '', domain)
        for pattern, name in SITEMAP.items():
            if pattern in domain:
                return name
        return "Unknown"

    def scrape(self, url, html, soup):
        return []


class Scraper4KHDHub(SiteScraper):
    def scrape(self, url, html, soup):
        results = []
        items = soup.find_all("div", class_="download-item")
        for di in items:
            ft = di.find(class_="file-title")
            title = ft.get_text(strip=True) if ft else ""
            links, seen = [], set()
            for a in di.find_all("a", href=True):
                href = a["href"].strip()
                label = host_label(href)
                if label and href not in seen:
                    seen.add(href)
                    links.append({"url": href, "host": label})
            if links:
                header = di.find(class_="download-header")
                htext = header.get_text(" ", strip=True) if header else title
                size = re.search(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', htext, re.I)
                quality = re.search(r'(\d+p|4K|8K|REMUX|BluRay|WEB[\s-]?DL|HDRip|HEVC)', htext, re.I)
                results.append({
                    "title": title or htext[:120],
                    "size": size.group(1) if size else "",
                    "quality": quality.group(1) if quality else "",
                    "links": links,
                })
        return results


class ScraperGeneric(SiteScraper):
    def scrape(self, url, html, soup):
        results = []
        seen = set()
        page_name = ScraperVegaMovies._movie_name(soup) if hasattr(ScraperVegaMovies, '_movie_name') else ""
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            label = host_label(href)
            if not label or href in seen:
                continue
            seen.add(href)
            title = ""
            node = a
            for _ in range(6):
                node = node.parent
                if node is None:
                    break
                h = node.find_previous(["h1", "h2", "h3", "h4", "p", "strong"])
                if h:
                    t = h.get_text(strip=True)
                    if t and len(t) > 8:
                        title = t[:150]
                        break
            size_m = re.search(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', title, re.I)
            qual_m = re.search(r'(\d+p|4K|8K|HEVC|BluRay|WEB[\s-]?DL|HDRip)', title, re.I)
            results.append({
                "title": title or page_name or "Download",
                "size": size_m.group(1) if size_m else "",
                "quality": qual_m.group(1) if qual_m else "",
                "links": [{"url": href, "host": label}],
            })
        return results


class ScraperFilmiZilla(SiteScraper):
    SIZE = re.compile(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', re.I)
    QRE = re.compile(r'(480p|720p|1080p|2160p|4K|8K|HEVC|10bit|x264|x265|WEB[\s-]?DL|HDRip|BluRay|HDTC)', re.I)

    def scrape(self, url, html, soup):
        results = []
        base_domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("/"):
                href = base_domain + href
            if "/server/" not in href.lower():
                continue
            if href in seen:
                continue
            seen.add(href)
            text = a.get_text(" ", strip=True)
            size_m = self.SIZE.search(text)
            qual_m = self.QRE.search(text)
            results.append({
                "title": text[:200] or "Download",
                "size": size_m.group(1) if size_m else "",
                "quality": qual_m.group(0) if qual_m else "",
                "links": [{"url": href, "host": "FilmiZilla"}],
            })
        return results


class ScraperVegaMovies(SiteScraper):
    QRE = re.compile(r'(480p|720p|1080p|2160p|4K|8K|HEVC|10bit|x264|x265|HDTC|WEB[\s-]?DL|HDRip|BluRay|HQ)', re.I)
    SIZE = re.compile(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', re.I)

    def scrape(self, url, html, soup):
        results = []
        cur_quality = ""
        movie_name = self._movie_name(soup)
        for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "a"]):
            if el.name != "a":
                t = el.get_text(" ", strip=True)
                if t and len(t) < 60 and self.QRE.search(t) and "download" not in t.lower():
                    cur_quality = t
                continue
            href = el.get("href", "").strip()
            label = host_label(href)
            if not label:
                continue
            btext = el.get_text(" ", strip=True)
            size = self.SIZE.search(btext) or self.SIZE.search(cur_quality)
            parts = [p for p in (movie_name, cur_quality or btext) if p]
            title = " — ".join(parts) or "Download"
            results.append({
                "title": title, "size": size.group(1) if size else "",
                "quality": cur_quality,
                "links": [{"url": href, "host": label}],
            })
        return results

    @staticmethod
    def _movie_name(soup):
        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else ""
        if not name and soup.title and soup.title.string:
            name = soup.title.string.strip()
        name = re.sub(r'\s*[-|–]\s*(download|watch online|vegamovies?).*$', '', name, flags=re.I)
        name = re.sub(r'\s*(download|watch online|free download)\b.*$', '', name, flags=re.I)
        return name.strip()[:120]


class ScraperSkyMoviesHD(SiteScraper):
    SIZE = re.compile(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', re.I)
    QRE = re.compile(r'(480p|720p|1080p|2160p|4K|HEVC|10bit|x264|x265|WEB[\s-]?DL|HDRip|BluRay|HDTC)', re.I)

    def scrape(self, url, html, soup):
        movie = ScraperVegaMovies._movie_name(soup)
        results, seen = [], set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            label = host_label(href)
            if not label or href in seen:
                continue
            seen.add(href)
            btext = a.get_text(" ", strip=True) or "Download"
            qual = self.QRE.search(btext) or self.QRE.search(movie)
            size = self.SIZE.search(btext) or self.SIZE.search(movie)
            parts = [p for p in (movie, btext) if p]
            results.append({
                "title": " — ".join(parts) or btext, "size": size.group(1) if size else "",
                "quality": qual.group(1) if qual else btext[:30],
                "links": [{"url": href, "host": label}],
            })
        return results


class ScraperMoviesNation(SiteScraper):
    def scrape(self, url, html, soup):
        results = []
        wrappers = soup.find_all("div", class_="dl-btn-wrapper")
        for w in wrappers:
            text = w.get_text(strip=True)
            a = w.find("a", href=True)
            if not a:
                continue
            href = a["href"].strip()
            label = host_label(href)
            size = ""
            quality = ""
            size_m = re.search(r'\[([^\]]+)\]', text)
            if size_m:
                size = size_m.group(1)
            qual_m = re.search(r'(\d+p|4K|8K|REMUX|BluRay|WEB[\s-]?DL|HDRip|HEVC)', text, re.I)
            if qual_m:
                quality = qual_m.group(1)
            results.append({
                "title": text[:120] if text else "Download Link",
                "size": size, "quality": quality,
                "links": [{"url": href, "host": label or "BollyDrive"}],
            })
        generic = ScraperGeneric()
        generic_results = generic.scrape(url, html, soup)
        seen_urls = {r["links"][0]["url"] for r in results if r["links"]}
        for gr in generic_results:
            if gr["links"] and gr["links"][0]["url"] not in seen_urls:
                results.append(gr)
        return results


class ScraperMoviesMod(SiteScraper):
    QRE = re.compile(r'(480p|720p|1080p|2160p|4K|8K|HEVC|10bit|x264|x265|HDTC|WEB[\s-]?DL|HDRip|BluRay|HQ)', re.I)
    SIZE = re.compile(r'\[([^\]]*(?:GB|MB|KB)[^\]]*)\]', re.I)
    QUALITY_CLEAN = re.compile(r'(480p|720p|1080p|2160p|4K|8K)', re.I)

    def scrape(self, url, html, soup):
        results = []
        cur_quality = ""
        cur_size = ""
        quality_tag = ""
        movie_name = self._movie_name(soup)
        for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "a", "p"]):
            t = el.get_text(" ", strip=True)
            if el.name != "a":
                if self.QRE.search(t) and len(t) < 120:
                    cur_quality = t
                    qm = self.QUALITY_CLEAN.search(t)
                    quality_tag = qm.group(1) if qm else ""
                    sz = self.SIZE.search(t)
                    cur_size = sz.group(1) if sz else ""
                continue
            href = el.get("href", "").strip()
            if not href or href.startswith("#") or "javascript" in href:
                continue
            label = host_label(href)
            if not label:
                continue
            parts = [p for p in (movie_name, cur_quality) if p]
            title = " — ".join(parts) or "Download"
            if not movie_name:
                title = cur_quality or "Download"
            results.append({
                "title": title, "size": cur_size, "quality": quality_tag,
                "links": [{"url": href, "host": label}],
            })
        return results

    @staticmethod
    def _movie_name(soup):
        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else ""
        if not name and soup.title and soup.title.string:
            name = soup.title.string.strip()
        name = re.sub(r'\s*[-|–]\s*(download|watch online|moviesmod?).*$', '', name, flags=re.I)
        name = re.sub(r'\s*(download|watch online|free download)\b.*$', '', name, flags=re.I)
        name = re.sub(r'\s*\(Season\s+\d+\).*$', '', name, flags=re.I)
        return name.strip()[:120]


class ScraperMovies4U(SiteScraper):
    SIZE = re.compile(r'\[([^\]]*(?:GB|MB|KB)[^\]]*)\]', re.I)
    QUALITY = re.compile(r'(\d+p\s*(?:HEVC)?|4K|8K)', re.I)

    def scrape(self, url, html, soup):
        results = []
        dl_div = soup.find('div', class_='download-links-div')
        if not dl_div:
            return ScraperGeneric().scrape(url, html, soup)
        current_h4 = None
        for child in dl_div.find_all(['h4', 'div'], recursive=False):
            if child.name == 'h4':
                current_h4 = child.get_text(' ', strip=True)
            elif child.name == 'div' and 'downloads-btns-div' in (child.get('class') or []):
                if current_h4:
                    links = []
                    for a in child.find_all('a', href=True):
                        href = a['href'].strip()
                        label = host_label(href)
                        if label:
                            links.append({"url": href, "host": label})
                    if links:
                        size_m = self.SIZE.search(current_h4)
                        qual_m = self.QUALITY.search(current_h4)
                        title = re.sub(r'\s*\[.*?\]\s*', ' ', current_h4).strip()
                        results.append({
                            "title": title[:200], "size": size_m.group(1) if size_m else "",
                            "quality": qual_m.group(1) if qual_m else "", "links": links,
                        })
                    current_h4 = None
        if not results:
            return ScraperGeneric().scrape(url, html, soup)
        return results


class ScraperExtraFlix(SiteScraper):
    SIZE = re.compile(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', re.I)
    QRE = re.compile(r'(480p|720p|1080p|2160p|4K|8K|HEVC|10bit|x264|x265|WEB[\s-]?DL|HDRip|BluRay|HDTC|REMUX|HQ)', re.I)

    def scrape(self, url, html, soup):
        results, seen = [], set()
        page_name = self._get_movie_name(soup)
        sections = soup.find_all(['div', 'section'],
            class_=re.compile(r'download-options-section|Untouched-download-links-section', re.I))
        for section in sections:
            section_text = section.get_text(" ", strip=True)
            for a in section.find_all("a", href=True):
                href = a["href"].strip()
                label = host_label(href)
                if not label or href in seen:
                    continue
                seen.add(href)
                context = ""
                prev_node = a.previous_sibling
                if prev_node and isinstance(prev_node, str) and prev_node.strip():
                    context = prev_node.strip()
                else:
                    parent = a.parent
                    if parent:
                        for child in parent.children:
                            if child == a:
                                break
                            if isinstance(child, str) and child.strip():
                                context = child.strip()
                                break
                qual = ""
                size = ""
                if context:
                    size_m = self.SIZE.search(context)
                    if size_m:
                        size = size_m.group(1)
                    qual_m = self.QRE.search(context)
                    if qual_m:
                        qual = qual_m.group(0)
                if not qual:
                    qual_m = self.QRE.search(section_text)
                    if qual_m:
                        qual = qual_m.group(0)
                if not size:
                    size_m = self.SIZE.search(section_text)
                    if size_m:
                        size = size_m.group(1)
                parts = [p for p in [page_name, qual] if p]
                title = " — ".join(parts) or "Download"
                results.append({
                    "title": title[:200], "size": size, "quality": qual,
                    "links": [{"url": href, "host": label}],
                })
        if not results:
            return ScraperGeneric().scrape(url, html, soup)
        return results

    @staticmethod
    def _get_movie_name(soup):
        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else ""
        if not name and soup.title and soup.title.string:
            name = soup.title.string.strip()
        name = re.sub(r'\s*[-–|]\s*(watch|download|free|full movie|online|extraflix?).*$', '', name, flags=re.I)
        name = re.sub(r'\s*(watch online|free download|download|full movie)\b.*$', '', name, flags=re.I)
        return name.strip()[:120]


class Scraper1CineVood(SiteScraper):
    SIZE = re.compile(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', re.I)
    QRE = re.compile(r'(480p|720p|1080p|2160p|4K|8K|HEVC|10bit|x264|x265|WEB[\s-]?DL|HDRip|BluRay|HDTC|REMUX|ESUBS?)', re.I)

    def scrape(self, url, html, soup):
        results, seen = [], set()
        page_name = self._get_page_name(soup)
        post_content = soup.find(['div', 'article'],
            class_=re.compile(r'post-content|entry-content|the-content|post-entry|article-body|td-post-content', re.I))
        container = post_content if post_content else soup
        for a in container.find_all("a", href=True):
            href = a["href"].strip()
            label = host_label(href)
            if not label or href in seen:
                continue
            seen.add(href)
            btext = a.get_text(" ", strip=True)
            parent_text = ""
            node = a
            for _ in range(4):
                node = node.parent
                if node is None:
                    break
                parent_text = node.get_text(" ", strip=True)
                if len(parent_text) > 20:
                    break
            context = parent_text or btext or page_name
            size_m = self.SIZE.search(context)
            qual_m = self.QRE.search(context)
            parts = [p for p in [page_name, qual_m.group(0) if qual_m else ""] if p]
            title = " — ".join(parts) or btext[:100] or "Download"
            results.append({
                "title": title[:200], "size": size_m.group(1) if size_m else "",
                "quality": qual_m.group(0) if qual_m else "",
                "links": [{"url": href, "host": label}],
            })
        if not results:
            return ScraperGeneric().scrape(url, html, soup)
        return results

    @staticmethod
    def _get_page_name(soup):
        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else ""
        if not name and soup.title and soup.title.string:
            name = soup.title.string.strip()
        name = re.sub(r'\s*[-–|]\s*(watch|download|free|full movie|online|1cinevood?).*$', '', name, flags=re.I)
        name = re.sub(r'\s*(watch online|free download|download|full movie)\b.*$', '', name, flags=re.I)
        return name.strip()[:120]


class ScraperOlaMovies(SiteScraper):
    SIZE = re.compile(r'\[([^\]]*(?:GB|MB|KB)[^\]]*)\]|(\d+[\.\d]*\s*(?:GB|MB|KB))', re.I)
    QRE = re.compile(
        r'(2160p|1080p|720p|480p|4K|8K|DS4K|SDR|HDR10\+?|DV|Dolby\s*Vision|REMUX|'
        r'HEVC|x265|x264|10bit|WEB[\s-]?DL|WEBRip|Atmos)', re.I)

    def scrape(self, url, html, soup):
        results, seen = [], set()
        movie = self._movie_name(soup)
        box = soup.find(['div', 'article'],
            class_=re.compile(r'entry-content|post-content|the-content|td-post-content|entry-inner', re.I)) or soup
        cur_release = ""
        for el in box.find_all(["h2", "h3", "h4", "h5", "h6", "p", "a"]):
            if el.name != "a":
                t = el.get_text(" ", strip=True)
                if t and 8 < len(t) < 160 and self.QRE.search(t) and "free download" not in t.lower():
                    cur_release = t
                continue
            href = el.get("href", "").strip()
            label = host_label(href)
            if not label or href in seen:
                continue
            seen.add(href)
            btext = el.get_text(" ", strip=True)
            ctx = f"{cur_release} {btext}"
            sm = self.SIZE.search(btext) or self.SIZE.search(cur_release)
            size = (sm.group(1) or sm.group(2)) if sm else ""
            qm = self.QRE.search(btext) or self.QRE.search(cur_release)
            quality = qm.group(1) if qm else ""
            ep = re.search(r'episode\s*\d+', btext, re.I)
            bits = [b for b in (movie, quality, ep.group(0).title() if ep else "") if b]
            title = " — ".join(bits) or btext or "Download"
            results.append({
                "title": title[:200], "size": size, "quality": quality,
                "links": [{"url": href, "host": label}],
            })
        if not results:
            return ScraperGeneric().scrape(url, html, soup)
        return results

    @staticmethod
    def _movie_name(soup):
        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else ""
        if not name and soup.title and soup.title.string:
            name = soup.title.string.strip()
        name = re.sub(r'\s*[-–|]\s*(watch|download|free|full movie|online|olamovies?).*$', '', name, flags=re.I)
        name = re.sub(r'^\s*(free\s+)?download\s+', '', name, flags=re.I)
        name = re.sub(r'\s+(720p|1080p|2160p|480p|4K|8K|DS4K|WEB[\s-]?DL|WEBRip|HDR|DV|x26[45]|HEVC|BluRay).*$',
                      '', name, flags=re.I)
        return name.strip()[:120]


class ScraperCloudMoviez(SiteScraper):
    SIZE = re.compile(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', re.I)
    QRE = re.compile(r'(2160p|1080p|720p|576p|480p|360p|4K|8K|HEVC|x265|x264|10bit|'
                     r'WEB[\s-]?DL|WEBRip|HDRip|BluRay|CVBR|CBR)', re.I)

    @staticmethod
    def _decode_token(href):
        m = re.search(r'/file/([A-Za-z0-9_\-=]+)', href)
        if not m:
            return None, ""
        tok = m.group(1)
        tok += "=" * (-len(tok) % 4)
        try:
            data = json.loads(base64.b64decode(tok).decode("utf-8", "replace"))
            return (data.get("url") or "").strip() or None, (data.get("title") or "").strip()
        except Exception:
            return None, ""

    def scrape(self, url, html, soup):
        results, seen = [], set()
        movie = ScraperVegaMovies._movie_name(soup)
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "/file/" not in href:
                continue
            real, emb_title = self._decode_token(href)
            if not real or real in seen:
                continue
            seen.add(real)
            label = host_label(real) or "GDFlix"
            btext = a.get_text(" ", strip=True)
            ctx = f"{emb_title} {btext}"
            size = ""
            sm = self.SIZE.search(btext) or self.SIZE.search(emb_title)
            if sm:
                size = sm.group(1)
            quality = ""
            qm = self.QRE.search(emb_title) or self.QRE.search(btext)
            if qm:
                quality = qm.group(1)
            bits = [b for b in (movie, quality) if b]
            title = " — ".join(bits) or emb_title[:80] or "Download"
            results.append({
                "title": title[:200], "size": size, "quality": quality,
                "links": [{"url": real, "host": label}],
            })
        if not results:
            return ScraperGeneric().scrape(url, html, soup)
        return results


class ScraperSupplyGang(SiteScraper):
    SIZE = re.compile(r'(\d+[\.\d]*\s*(?:GB|MB|KB))', re.I)
    QRE = re.compile(r'(480p|720p|1080p|2160p|4K|8K|HEVC|10bit|x264|x265|WEB[\s-]?DL|HDRip|BluRay|HDTC)', re.I)

    def scrape(self, url, html, soup):
        results, seen_gateways = [], set()
        movie_name = ScraperVegaMovies._movie_name(soup)
        info_blocks = []
        for a in soup.find_all("a", class_="dlbtn"):
            text = a.get_text(" ", strip=True)
            if not text:
                continue
            sm = self.SIZE.search(text)
            qm = self.QRE.search(text)
            info_blocks.append({"text": text, "size": sm.group(1) if sm else "",
                                "quality": qm.group(1) if qm else ""})
        qualities = {}
        for blk in info_blocks:
            q = blk["quality"] or "Download"
            if q not in qualities:
                qualities[q] = {"size": blk["size"], "quality": q}
        gateway_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = a.get_text(" ", strip=True).upper()
            if any(ext in href.lower() for ext in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"]):
                continue
            label = host_label(href)
            is_gateway = label is not None or "mrfastcdn" in href.lower()
            if not is_gateway and "DOWNLOAD NOW" not in text and "DOWNLOAD" not in text.split()[:2]:
                continue
            if not is_gateway:
                label = "SupplyGang"
            if href in seen_gateways:
                continue
            seen_gateways.add(href)
            gateway_links.append({"url": href, "host": label or "SupplyGang",
                                  "text": a.get_text(" ", strip=True)})
        if gateway_links:
            if not qualities:
                title = movie_name or "Download"
                results.append({"title": title[:200], "size": "", "quality": "",
                    "links": [{"url": gl["url"], "host": gl["host"]} for gl in gateway_links]})
            else:
                for qkey, qinfo in qualities.items():
                    title_parts = [p for p in (movie_name, qinfo["quality"]) if p]
                    title = " — ".join(title_parts) or "Download"
                    results.append({"title": title[:200], "size": qinfo["size"],
                        "quality": qinfo["quality"],
                        "links": [{"url": gl["url"], "host": gl["host"]} for gl in gateway_links]})
        else:
            return ScraperGeneric().scrape(url, html, soup)
        return results


SCRAPER_MAP = {
    "SupplyGang": ScraperSupplyGang(), "ExtraFlix": ScraperExtraFlix(),
    "1CineVood": Scraper1CineVood(), "4KHDHub": Scraper4KHDHub(),
    "HDHub4U": ScraperGeneric(), "VegaMovies": ScraperVegaMovies(),
    "KatMovieHD": ScraperGeneric(), "MoviesMod": ScraperMoviesMod(),
    "MoviezAddiction": ScraperGeneric(), "MoviezFlix": ScraperGeneric(),
    "FilmiZilla": ScraperFilmiZilla(), "DownloadHub": ScraperGeneric(),
    "HackStore": ScraperGeneric(), "Mega1080p": ScraperGeneric(),
    "MoviesNation": ScraperMoviesNation(), "UHDMovies": ScraperGeneric(),
    "MovieForHD": ScraperGeneric(), "MoviesKiDuniya": ScraperGeneric(),
    "9xMovies": ScraperGeneric(), "BollyFlix": ScraperGeneric(),
    "SSRMovies": ScraperGeneric(), "TodayMovie": ScraperGeneric(),
    "XDMovies": ScraperGeneric(), "Movies4U": ScraperMovies4U(),
    "SkyMoviesHD": ScraperSkyMoviesHD(), "OlaMovies": ScraperOlaMovies(),
    "CloudMoviez": ScraperCloudMoviez(), "VegaNavy": ScraperGeneric(),
    "MoviesFlix": ScraperGeneric(), "Unknown": ScraperGeneric(),
}


def scrape_site(url, deep=True):
    try:
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        html = resp.text
    except Exception:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            raise Exception(f"Failed to fetch {url}: {e}")

    soup = BeautifulSoup(html, "html.parser")
    site_name = SiteScraper.detect(url)
    page_title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"

    scraper_obj = SCRAPER_MAP.get(site_name, ScraperGeneric())
    blocks = scraper_obj.scrape(url, html, soup)
    if not blocks and not isinstance(scraper_obj, ScraperGeneric):
        blocks = ScraperGeneric().scrape(url, html, soup)

    if deep:
        blocks = resolve_blocks(blocks)

    total = sum(len(b["links"]) for b in blocks)
    return {
        "url": url,
        "site": site_name,
        "title": page_title,
        "blocks": blocks,
        "total_links": total,
    }

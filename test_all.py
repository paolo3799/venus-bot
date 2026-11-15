import os, re, time
from playwright.sync_api import sync_playwright

PROXY_SERVER = os.getenv("PROXY_SERVER", "")
PROXY_USER = os.getenv("PROXY_USER", "")
PROXY_PASS = os.getenv("PROXY_PASS", "")

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

if __name__ == "__main__":
    proxy_cfg = None
    if PROXY_SERVER:
        proxy_cfg = {"server": PROXY_SERVER}
        if PROXY_USER: proxy_cfg["username"] = PROXY_USER
        if PROXY_PASS: proxy_cfg["password"] = PROXY_PASS
    with sync_playwright() as p:
        launch_kwargs = {"headless": True, "args": ["--no-sandbox"]}
        if proxy_cfg: launch_kwargs["proxy"] = proxy_cfg
        b = p.chromium.launch(**launch_kwargs)
        pg = b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        pg.goto("https://www.goaloo.com/", wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(15000)
        html = pg.content()
        log(f"HTML len={len(html)} URL={pg.url} Titolo={pg.title()}")
        log(f"COUNT table={html.count('<table')} tr={html.count('<tr')} div={html.count('<div')} iframe={html.count('<iframe')}")
        # Tutti gli id che contengono tr o match
        ids = re.findall(r'id="([^"]+)"', html)
        log(f"TOT ID trovati: {len(ids)}")
        for i in ids[:40]:
            log(f"ID: {i}")
        # Cerca righe con minuto tipo 55'
        mins = re.findall(r"(\d{1,3})['’]", html)
        log(f"Minuti trovati nel HTML: {len(mins)} primi: {mins[:20]}")
        # Cerca iframe
        for f in pg.query_selector_all("iframe"):
            log(f"IFRAME src={f.get_attribute('src')}")
        # Cerca script con live / score / data
        for s in pg.query_selector_all("script"):
            src = s.get_attribute("src") or ""
            if any(k in src.lower() for k in ["live", "score", "match", "data", "soccer"]):
                log(f"SCRIPT: {src}")
        # Prova altri selettori
        for sel in ["tr", "tr[id]", ".match", "[data-match]", "[data-id]", "table tbody tr"]:
            try:
                n = len(pg.query_selector_all(sel))
                log(f"SELETTORE {sel} -> {n}")
            except Exception as e:
                log(f"SELETTORE {sel} ERR {e}")
        # Testo visibile, prime 2000 lettere
        try:
            txt = pg.inner_text("body")[:2000]
            log(f"TESTO VISIBILE INIZIO:\n{txt}")
        except Exception as e:
            log(f"TESTO ERR {e}")
        b.close()

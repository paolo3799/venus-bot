import urllib.request
import re
import ssl

URL = "https://www.goaloo.com/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.goaloo.com/",
}

print("TEST GOALOO - inizio", flush=True)

try:
    req = urllib.request.Request(URL, headers=headers)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        print(f"Status code: {resp.status}", flush=True)
        text = resp.read().decode("utf-8", errors="ignore")
        print(f"Lunghezza pagina: {len(text)}", flush=True)

        for squadra in ["Portugal", "Austria", "Real Oviedo", "Sweden"]:
            if squadra in text:
                print(f"TROVATA: {squadra}", flush=True)
            else:
                print(f"NON TROVATA: {squadra}", flush=True)

        if "Portugal" in text:
            print("RISULTATO: GOALOO NON BLOCCA - possiamo andare avanti", flush=True)
        else:
            print("RISULTATO: GOALOO NON MOSTRA DATI - serve altro metodo", flush=True)

except Exception as e:
    print(f"ERRORE: {type(e).__name__}: {e}", flush=True)
    print("RISULTATO: BLOCCATO / ERRORE", flush=True)

print("TEST FINITO", flush=True)

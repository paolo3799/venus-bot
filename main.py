import requests
import re
import sys

URL = "https://www.goaloo.com/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.goaloo.com/",
}

print("TEST GOALOO - inizio", flush=True)

try:
    r = requests.get(URL, headers=headers, timeout=30)
    print(f"Status code: {r.status_code}", flush=True)
    print(f"Lunghezza pagina: {len(r.text)}", flush=True)

    if r.status_code != 200:
        print(f"BLOCCATO - status {r.status_code}", flush=True)
        sys.exit(0)

    # Conta quante partite live ci sono nel codice
    # Goaloo le mette come team names nel JS
    partite = re.findall(r'"homeName"\s*:\s*"([^"]+)"', r.text)
    if not partite:
        # prova secondo pattern
        partite = re.findall(r"team.*?(Oviedo|Portugal|Austria)", r.text)

    print(f"Partite trovate (pattern1): {len(partite)}", flush=True)

    # Controllo semplice: la pagina contiene le squadre che hai visto tu?
    for squadra in ["Portugal", "Austria", "Real Oviedo", "Sweden"]:
        if squadra in r.text:
            print(f"TROVATA: {squadra}", flush=True)
        else:
            print(f"NON TROVATA: {squadra}", flush=True)

    if "Portugal" in r.text:
        print("RISULTATO: GOALOO NON BLOCCA - possiamo andare avanti", flush=True)
    else:
        print("RISULTATO: GOALOO NON MOSTRA DATI - forse serve altro metodo", flush=True)

except Exception as e:
    print(f"ERRORE: {type(e).__name__}: {e}", flush=True)
    print("RISULTATO: BLOCCATO / ERRORE", flush=True)

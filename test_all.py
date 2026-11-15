import os
import bot as B

matches = B.get_live_matches()
print(f"TROVATI: {len(matches)}")

righe = []
for m in matches:
    op, cu = B.get_spread_averages(m["id"])
    righe.append(
        f"{m['home']} vs {m['away']} | "
        f"ID:{m['id']} | Min:{m['minute']} | "
        f"Ris:{m['sh']}-{m['sa']} | "
        f"OP:{op} | CU:{cu} | "
        f"Regola: - | Segnale: - | Key:{m['id']}-{m['minute']}-{m['sh']}-{m['sa']}"
    )

body = f"TEST VENUS - Partite viste: {len(matches)}\n\n" + "\n".join(righe)
print(body)
B.send_mail(f"TEST VENUS - {len(matches)} partite live viste", body)

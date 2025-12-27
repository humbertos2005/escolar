#!/usr/bin/env python3
# Analisa arquivos em templates/ para detectar possível mojibake (cp1252/latin1 vs utf-8)
# NÃO altera nenhum arquivo — apenas imprime um diagnóstico.
import os
import sys

root = "templates"
if not os.path.isdir(root):
    print("ERRO: diretório templates/ não encontrado onde o script foi executado.")
    sys.exit(1)

bad_tokens = ["Ã","Â","�","â","Ã¡","Ã©","Ãª","Ã§","Ãµ","Ã­","Ã³","Ã£"]
good_tokens = ["ã","õ","ç","é","á","ó","í","â","ê","ô","ú","à","Ã"]  # include some to evaluate patterns

def score_text(t):
    bad = sum(t.count(x) for x in bad_tokens)
    good = sum(t.count(x) for x in good_tokens)
    return bad, good

def analyze_file(path):
    with open(path, "rb") as f:
        b = f.read()
    # try utf-8 decode
    try:
        u = b.decode("utf-8")
        u_ok = True
    except Exception:
        u = b.decode("utf-8", errors="replace")
        u_ok = False
    # cp1252 decode
    cp = b.decode("cp1252", errors="replace")
    latin1 = b.decode("latin1", errors="replace")
    # score each candidate
    u_bad, u_good = score_text(u)
    cp_bad, cp_good = score_text(cp)
    lat_bad, lat_good = score_text(latin1)
    # choose best by minimizing bad and maximizing good (simple heuristic)
    candidates = [
        ("utf-8", u_bad, u_good, u_ok, u),
        ("cp1252", cp_bad, cp_good, True, cp),
        ("latin1", lat_bad, lat_good, True, latin1),
    ]
    # sort by (bad, -good)
    best = sorted(candidates, key=lambda x: (x[1], -x[2]))[0]
    return {
        "path": path,
        "utf8_bad": u_bad, "utf8_good": u_good, "utf8_decodable": u_ok,
        "cp1252_bad": cp_bad, "cp1252_good": cp_good,
        "latin1_bad": lat_bad, "latin1_good": lat_good,
        "best_encoding": best[0],
        "best_bad": best[1], "best_good": best[2],
        "best_preview": best[4][:260].replace("\n","\\n")
    }

results = []
for dirpath, dirs, files in os.walk(root):
    for fn in files:
        if fn.lower().endswith((".html", ".htm", ".txt", ".jinja", ".j2")):
            path = os.path.join(dirpath, fn)
            try:
                res = analyze_file(path)
                results.append(res)
            except Exception as e:
                print(f"ERRO analisando {path}: {e}")

# print report
print("Análise de codificação para templates/\n")
for r in results:
    path = r["path"]
    print("Arquivo:", path)
    print("  Melhor candidato:", r["best_encoding"], f"(bad={r['best_bad']}, good={r['best_good']})")
    print("  utf-8: bad={}, good={}, decodable={}".format(r["utf8_bad"], r["utf8_good"], r["utf8_decodable"]))
    print("  cp1252: bad={}, good={}".format(r["cp1252_bad"], r["cp1252_good"]))
    print("  latin1: bad={}, good={}".format(r["latin1_bad"], r["latin1_good"]))
    print("  Preview do melhor candidato (até 260 chars):")
    print("    ", r["best_preview"])
    print("-" * 72)

# summary
need_fix = [r for r in results if r["best_encoding"] != "utf-8" or r["utf8_bad"]>0]
print("\nResumo:")
print(f"  Total arquivos verificados: {len(results)}")
print(f"  Arquivos que provavelmente precisam correção: {len(need_fix)}")
for r in need_fix:
    print("   -", r["path"], "=> melhor:", r["best_encoding"], f"(bad={r['best_bad']})")
print("\nObservação: este é apenas um diagnóstico. Depois que você colar a saída, eu proponho o próximo e único comando para CONVERTER os arquivos apontados — um por vez, conforme sua regra.")
#!/usr/bin/env python3
"""DETECTOR DE INTEGRIDAD v3 (definitivo).

Neutraliza la marca en AMBOS lados (nuestra version y la de upstream) y
compara. Lo que quede distinto es diferencia REAL: aportacion propia
legitima o contenido congelado / auto-merge incompleto.

Este es el gate que faltaba al proceso de sync: un archivo puede quedar
sintacticamente valido, pasar la auditoria de marca y aun asi llamar a un
metodo que su archivo hermano congelado nunca definio.

Uso: integrity_check3.py [--list-only]
"""
import difflib
import re
import subprocess

BRAND = re.compile(r"Hermes Agent|Nous Research|Digital Services LLC|IYARI|\bHermes\b|hermes-agent|digital-services-llc|NousResearch")
EXT = (".py", ".ts", ".tsx", ".js", ".cjs")
SKIP = ("website/", "locales/", "contributors/")


def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout


def neutral(text):
    return [BRAND.sub("@B@", l) for l in text.split("\n")]


changed = [l for l in sh("git diff --name-only HEAD upstream/main").split("\n") if l]
print(f"archivos que difieren de upstream: {len(changed)}")

reales = []
for f in changed:
    if not f.endswith(EXT) or any(f.startswith(s) for s in SKIP):
        continue
    try:
        ours = open(f, encoding="utf-8", errors="surrogateescape").read()
    except OSError:
        continue
    theirs = sh(f"git show upstream/main:{f!r}")
    if not theirs:
        continue
    a, b = neutral(theirs), neutral(ours)
    if a == b:
        continue
    d = [l for l in difflib.unified_diff(a, b, lineterm="", n=0)
         if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    reales.append((f, len(d), d[:6]))

reales.sort(key=lambda x: -x[1])
print(f"\nARCHIVOS CON DIFERENCIA REAL (no marca): {len(reales)}")
print(f"{'lineas':>7}  archivo")
for f, n, _ in reales:
    print(f"{n:>7}  {f}")

print("\n" + "=" * 74)
for f, n, sample in reales[:12]:
    print(f"\n--- {f} ({n} lineas reales) ---")
    for l in sample:
        print("   ", l[:150])
open("/opt/data/tmp/diferencias-reales.txt", "w").write("\n".join(f for f, _, _ in reales))

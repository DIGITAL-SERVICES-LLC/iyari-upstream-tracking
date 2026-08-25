#!/usr/bin/env python3
"""DETECTOR DE INTEGRIDAD POST-SYNC.

Encuentra archivos que difieren de upstream SIN tener marca propia ni cambios
legitimos nuestros: eso es contenido congelado o auto-merge incompleto, y es
la causa de AttributeError como '_get_session_rich_rows_batch' (metodo llamado
pero nunca definido porque su archivo quedo en version vieja).

Criterio: si el archivo difiere de upstream/main y NO contiene "IYARI" ni
"Digital Services LLC" ni "digital-services-llc", entonces no tenemos nada
propio ahi y deberia ser byte-identico a upstream.

Uso: integrity_check.py [--fix]
"""
import subprocess
import sys

FIX = "--fix" in sys.argv
EXT = (".py", ".ts", ".tsx", ".js", ".cjs", ".mjs")
SKIP_PREFIX = ("website/", "locales/", "contributors/", "tests-js/")
MARKS = ("IYARI", "Digital Services LLC", "digital-services-llc", "iyari")

# Excepciones conocidas: difieren de upstream y NO contienen marca, pero la
# diferencia es aportacion propia legitima (verificado con
# `git log <merge-base>..origin/main -- <archivo>`: los toca un commit de fase,
# no solo los commits de sync). Revisar esta lista en cada sync; si un archivo
# de aqui deja de tener trabajo propio, quitarlo.
ALLOWLIST = {
    "agent/system_prompt.py":
        "Fase 1.1: capa de meta-prompt no anulable por soul.md (agent/meta_prompt.py)",
    "tests/agent/test_prompt_builder.py":
        "fix propio ba1c4ba042: comprueba DEFAULT_SOUL_MD, no la marca de upstream",
    "ui-tui/src/components/appChrome.tsx":
        "GRUPO 1-3: simbolo del prompt propio en vez del caduceo de upstream",
    "ui-tui/src/components/appLayout.tsx":
        "GRUPO 1-3: simbolo del prompt propio en vez del caduceo de upstream",
}


def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout


changed = [l for l in sh("git diff --name-only HEAD upstream/main").split("\n") if l]
print(f"archivos que difieren de upstream/main: {len(changed)}")

sospechosos = []
excepciones = []
for f in changed:
    if not f.endswith(EXT) or f.startswith(SKIP_PREFIX):
        continue
    try:
        ours = open(f, encoding="utf-8", errors="surrogateescape").read()
    except OSError:
        continue  # borrado en nuestro lado a proposito
    if any(m in ours for m in MARKS):
        continue  # tenemos marca propia: la diferencia es legitima
    theirs = sh(f"git show upstream/main:{f!r}")
    if not theirs:
        continue  # nuevo/borrado
    n = len([1 for l in sh(f"git diff HEAD upstream/main -- {f!r}").split("\n")
             if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))])
    if f in ALLOWLIST:
        excepciones.append((f, n, ALLOWLIST[f]))
        continue
    sospechosos.append((f, n, len(ours.split("\n")), len(theirs.split("\n"))))

sospechosos.sort(key=lambda x: -x[1])
print(f"\nDESALINEADOS SIN MARCA PROPIA (candidatos a contenido congelado): {len(sospechosos)}")
if not sospechosos:
    print("  ninguno — arbol integro respecto a upstream")
else:
    print(f"{'lineas_dif':>11} {'nuestro':>8} {'upstream':>9}  archivo")
    for f, n, a, b in sospechosos[:40]:
        print(f"{n:>11} {a:>8} {b:>9}  {f}")
    if len(sospechosos) > 40:
        print(f"  ... (+{len(sospechosos) - 40})")

if excepciones:
    print(f"\nEXCEPCIONES CONOCIDAS (aportacion propia, NO tocar): {len(excepciones)}")
    for f, n, motivo in excepciones:
        print(f"  [{n:3d} lineas] {f}\n               -> {motivo}")

if FIX and sospechosos:
    print("\n--- APLICANDO version de upstream ---")
    for f, n, a, b in sospechosos:
        subprocess.run(f"git checkout upstream/main -- {f!r}", shell=True)
        print(f"  OK {f}")
    print(f"total: {len(sospechosos)} archivos alineados con upstream")

open("/opt/data/tmp/desalineados.txt", "w").write("\n".join(f for f, _, _, _ in sospechosos))

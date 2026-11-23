"""Punto de entrada CLI unificado para REPOSITORIO-codigo (Nexus IA v2 & Auditoría Casos Legales)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nexus_ia import ejecutar_nexus


def listar_casos_locales(base_dir: Path) -> list[dict[str, str]]:
    casos_dir = base_dir / "CASOS_LEGALES"
    if not casos_dir.exists():
        return []
    salida: list[dict[str, str]] = []
    for item in sorted(casos_dir.iterdir()):
        if item.is_dir():
            archivos = [p.name for p in item.rglob("*") if p.is_file()]
            salida.append({"caso": item.name, "total_archivos": str(len(archivos))})
    return salida


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI Nexus IA v2 — Drive, Gmail y Casos Legales")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("nexus", help="Ejecutar síntesis cruzada Drive + Gmail con Gemini 2.5")
    sub.add_parser("casos", help="Listar carpetas en CASOS_LEGALES")

    args = parser.parse_args()
    root = Path(__file__).resolve().parent

    if args.cmd == "casos":
        print(json.dumps(listar_casos_locales(root), indent=2, ensure_ascii=False))
    elif args.cmd == "nexus":
        res = ejecutar_nexus(output_dir=root / "output", interactive_oauth=False)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

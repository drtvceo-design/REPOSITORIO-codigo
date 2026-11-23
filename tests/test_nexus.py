"""Unit and integration tests for Nexus IA v2 and REPOSITORIO-codigo CLI."""

from __future__ import annotations

from pathlib import Path

from main import listar_casos_locales
from nexus_ia import analizar_con_gemini, ejecutar_nexus


def test_analizar_sin_api_key_no_aborta() -> None:
    salida = analizar_con_gemini("Documento de prueba NUREJ 10170321", api_key="")
    assert "MODO AUDITORÍA LOCAL" in salida


def test_listar_casos_locales() -> None:
    root = Path(__file__).resolve().parent.parent
    casos = listar_casos_locales(root)
    assert any("YUCRA_JUDITH" in c["caso"] for c in casos)


def test_ejecutar_nexus_genera_digest_json(tmp_path: Path) -> None:
    reporte = ejecutar_nexus(output_dir=tmp_path, interactive_oauth=False)
    assert "generated_at" in reporte
    assert (tmp_path / "latest_nexus_digest.json").exists()

"""Nexus IA v2 — Cruce estratégico de Google Drive + Gmail con el SDK oficial google-genai (Gemini 2.5)."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai

from drive_connection import auth_google, exportar_doc_por_cli_gdrive, extraer_contexto_drive_oauth

load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
PINNED_CONCILIACION_DOC_ID = "10ECGZt8KlMEbvXx3SEjk77MGBGWZN_JlWNVWv4_5g5U"


def extraer_contexto_gmail(creds: Any, max_results: int = 3) -> str:
    """Lee en modo solo-lectura los últimos mensajes de la bandeja de entrada."""
    if creds is None:
        return ""
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=max_results).execute()
    messages = results.get("messages", [])

    bloques: list[str] = []
    for msg in messages:
        try:
            txt = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
            payload = txt.get("payload", {})
            headers = payload.get("headers", [])

            asunto = next((h["value"] for h in headers if h.get("name") == "Subject"), "Sin Asunto")
            remitente = next((h["value"] for h in headers if h.get("name") == "From"), "Desconocido")

            cuerpo = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain":
                        data = part.get("body", {}).get("data")
                        if data:
                            cuerpo = base64.urlsafe_bdecode(data).decode("utf-8", errors="replace")
                            break
            elif payload.get("body", {}).get("data"):
                cuerpo = base64.urlsafe_bdecode(payload["body"]["data"]).decode("utf-8", errors="replace")

            bloques.append(
                f"\n--- EMAIL RECIBIDO ---\nDe: {remitente}\nAsunto: {asunto}\nCuerpo: {cuerpo[:1000]}...\n"
            )
        except Exception:
            continue
    return "".join(bloques)


def construir_contexto_dual(interactive_oauth: bool = False) -> dict[str, str]:
    """Obtiene contexto desde OAuth local o desde el CLI conectado 'gdrive' en entornos cloud."""
    creds = auth_google(interactive=interactive_oauth)
    datos_drive = ""
    datos_gmail = ""

    if creds is not None:
        datos_drive = extraer_contexto_drive_oauth(creds)
        datos_gmail = extraer_contexto_gmail(creds)
    else:
        exportado = exportar_doc_por_cli_gdrive(PINNED_CONCILIACION_DOC_ID)
        if exportado:
            datos_drive = f"\n--- DOC DRIVE (CLI gdrive): Conciliación Definitiva ---\n{exportado}\n"

    return {"drive": datos_drive, "gmail": datos_gmail}


def analizar_con_gemini(contexto_total: str, api_key: str | None = None, model_name: str | None = None) -> str:
    """Ejecuta síntesis estratégica usando el SDK unificado google-genai (Gemini 2.5)."""
    resolved_key = (api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")).strip()
    resolved_model = (model_name or DEFAULT_MODEL).strip()

    if not resolved_key:
        return (
            "[MODO AUDITORÍA LOCAL SIN GEMINI_API_KEY]\n"
            f"Contexto verificado correctamente ({len(contexto_total)} caracteres). "
            "Define GEMINI_API_KEY en tu archivo .env para activar la síntesis generativa con "
            f"{resolved_model}."
        )

    client = genai.Client(api_key=resolved_key)
    instruccion = (
        "Realiza un análisis cruzado basado estrictamente en la verdad material de mis documentos "
        "corporativos/legales y mis correos más recientes. Sintetiza la información estratégica aplicable."
    )
    prompt_final = f"Contexto extraído:\n{contexto_total}\n\nInstrucción: {instruccion}"
    respuesta = client.models.generate_content(model=resolved_model, contents=prompt_final)
    return (respuesta.text or "").strip()


def ejecutar_nexus(output_dir: Path | None = None, interactive_oauth: bool = False) -> dict[str, Any]:
    """Ejecuta el pipeline completo de Nexus IA y guarda un reporte JSON trazable."""
    fuentes = construir_contexto_dual(interactive_oauth=interactive_oauth)
    datos_drive = fuentes["drive"]
    datos_gmail = fuentes["gmail"]
    contexto_total = f"--- DATOS DE DRIVE ---\n{datos_drive}\n--- DATOS DE GMAIL ---\n{datos_gmail}"

    sintesis = analizar_con_gemini(contexto_total) if (datos_drive.strip() or datos_gmail.strip()) else (
        "[SISTEMA] No hay contexto procesable en Drive ni en Gmail."
    )

    reporte = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": DEFAULT_MODEL,
        "drive_chars": len(datos_drive),
        "gmail_chars": len(datos_gmail),
        "synthesis": sintesis,
    }

    target_dir = output_dir or (Path(__file__).resolve().parent / "output")
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "latest_nexus_digest.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return reporte


def main() -> None:
    reporte = ejecutar_nexus(interactive_oauth=False)
    print("\n================ RESPUESTA DE NEXUS IA v2 ================\n")
    print(reporte["synthesis"])
    print("\n==========================================================\n")


if __name__ == "__main__":
    main()

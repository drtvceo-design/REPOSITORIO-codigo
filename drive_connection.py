"""Conector modular de solo lectura para Google Drive (OAuth API v3 + fallback CLI gdrive)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def auth_google(
    token_path: str = "token.json",
    credentials_path: str = "credentials.json",
    interactive: bool = True,
) -> Any:
    """Autentica contra Google Workspace en modo solo-lectura."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not interactive or not os.path.exists(credentials_path):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds


def extraer_contexto_drive_oauth(creds: Any, page_size: int = 5) -> str:
    """Extrae texto reciente de Google Docs usando la API oficial de Drive v3."""
    from googleapiclient.discovery import build

    service = build("drive", "v3", credentials=creds)
    results = (
        service.files()
        .list(
            pageSize=page_size,
            q="mimeType='application/vnd.google-apps.document'",
            orderBy="modifiedTime desc",
            fields="files(id, name)",
        )
        .execute()
    )
    items = results.get("files", [])
    bloques: list[str] = []
    for item in items:
        try:
            req = service.files().export_media(fileId=item["id"], mimeType="text/plain")
            texto = req.execute().decode("utf-8", errors="replace")
            bloques.append(f"\n--- DOC DRIVE: {item['name']} ---\n{texto[:1500]}...\n")
        except Exception:
            continue
    return "".join(bloques)


def exportar_doc_por_cli_gdrive(file_id: str) -> str:
    """Usa el plugin conectado 'gdrive readonly export' cuando no hay token.json local."""
    gdrive_bin = shutil.which("gdrive")
    if not gdrive_bin:
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        out_md = Path(tmp) / "exported.md"
        proc = subprocess.run(
            [gdrive_bin, "readonly", "export", file_id, str(out_md), "--format", "md"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if proc.returncode == 0 and out_md.exists():
            return out_md.read_text(encoding="utf-8", errors="replace")[:2500]
    return ""

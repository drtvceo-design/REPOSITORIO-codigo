# 🧠 REPOSITORIO-codigo — Nexus IA v2 (Drive + Gmail + Gemini 2.5)

Integración modular en solo-lectura de **Google Drive**, **Gmail** y **Casos Legales** impulsada por el SDK unificado `google-genai` (`gemini-2.5-flash`).

## 🚀 Uso Rápido

```bash
python3 -m pip install -r requirements.txt
python3 main.py casos
python3 main.py nexus
pytest tests/ -v
```

## 🔒 Seguridad
- Configura `GEMINI_API_KEY` en `.env` (ignorado por Git).
- `credentials.json`, `token.json` y `output/` están excluidos de control de versiones.

import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# 1. Autenticación de Gemini
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Falta GEMINI_API_KEY en el archivo .env")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

# 2. Autenticación de Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def auth_drive():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def extraer_contexto_drive(service):
    print("[SISTEMA] Escaneando tus últimos Google Docs en Drive...")
    # Busca los 3 documentos de Google Docs más recientes
    results = service.files().list(
        pageSize=3,
        q="mimeType='application/vnd.google-apps.document'",
        orderBy="modifiedTime desc",
        fields="files(id, name)"
    ).execute()
    
    items = results.get('files', [])
    contexto = ""
    
    for item in items:
        print(f"[EXTRACCIÓN] Leyendo: {item['name']}")
        try:
            # Exporta el contenido del documento a texto plano
            request = service.files().export_media(fileId=item['id'], mimeType='text/plain')
            texto = request.execute().decode('utf-8')
            contexto += f"\n--- DOCUMENTO: {item['name']} ---\n{texto}\n"
        except Exception as e:
            print(f"[ERROR] No se pudo leer {item['name']}: {e}")
            
    return contexto

def main():
    try:
        # Conectar a Drive y extraer la información
        drive_service = auth_drive()
        contexto_base = extraer_contexto_drive(drive_service)
        
        if not contexto_base.strip():
            print("[SISTEMA] No hay contexto en Drive. Crea un Google Doc primero.")
            return

        # Consultar a Gemini con el contexto de tus documentos
        pregunta_usuario = "¿Haz un resumen legal o estratégico basado en estos documentos?"
        prompt_final = f"Este es el contexto extraído de mis archivos en Google Drive:\n{contexto_base}\n\nInstrucción: {pregunta_usuario}"
        
        print("\n[GEMINI] Analizando información...")
        respuesta = model.generate_content(prompt_final)
        
        print("\n================ RESPUESTA DE LA IA ================\n")
        print(respuesta.text)
        print("\n====================================================\n")
        
    except Exception as e:
        print(f"Error crítico en la ejecución: {e}")

if __name__ == '__main__':
    main()

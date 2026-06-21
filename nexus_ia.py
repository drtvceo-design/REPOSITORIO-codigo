import os
import base64
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR CRÍTICO: Falta GEMINI_API_KEY en el archivo .env")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def auth_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                if os.path.exists('token.json'):
                    os.remove('token.json')
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def extraer_contexto_drive(creds):
    service = build('drive', 'v3', credentials=creds)
    print("[SISTEMA] Escaneando documentos en Drive...")
    results = service.files().list(
        pageSize=3,
        q="mimeType='application/vnd.google-apps.document'",
        orderBy="modifiedTime desc",
        fields="files(id, name)"
    ).execute()
    
    items = results.get('files', [])
    contexto = ""
    for item in items:
        try:
            request = service.files().export_media(fileId=item['id'], mimeType='text/plain')
            texto = request.execute().decode('utf-8')
            contexto += f"\n--- DOC DRIVE: {item['name']} ---\n{texto[:1500]}...\n"
        except Exception:
            pass
    return contexto

def extraer_contexto_gmail(creds):
    service = build('gmail', 'v1', credentials=creds)
    print("[SISTEMA] Escaneando bandeja de entrada de Drtvceo@gmail.com...")
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=3).execute()
    messages = results.get('messages', [])
    
    contexto = ""
    for msg in messages:
        try:
            txt = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            payload = txt['payload']
            headers = payload.get("headers")
            
            asunto = next((header['value'] for header in headers if header['name'] == 'Subject'), "Sin Asunto")
            remitente = next((header['value'] for header in headers if header['name'] == 'From'), "Desconocido")
            
            cuerpo = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data')
                        if data:
                            cuerpo = base64.urlsafe_bdecode(data).decode('utf-8')
                            break
            elif 'body' in payload and payload['body'].get('data'):
                cuerpo = base64.urlsafe_bdecode(payload['body']['data']).decode('utf-8')
                
            contexto += f"\n--- EMAIL RECIBIDO ---\nDe: {remitente}\nAsunto: {asunto}\nCuerpo: {cuerpo[:1000]}...\n"
        except Exception:
            pass
    return contexto

def main():
    try:
        creds = auth_google()
        datos_drive = extraer_contexto_drive(creds)
        datos_gmail = extraer_contexto_gmail(creds)
        
        contexto_total = f"--- DATOS DE DRIVE ---\n{datos_drive}\n--- DATOS DE GMAIL ---\n{datos_gmail}"
        
        if not datos_drive.strip() and not datos_gmail.strip():
            print("[SISTEMA] No hay contexto procesable en Drive ni en Gmail.")
            return

        pregunta_usuario = "Realiza un análisis cruzado basado estrictamente en la verdad material de mis documentos corporativos/legales y mis correos más recientes. Sintetiza la información estratégica aplicable a mi entorno."
        prompt_final = f"Contexto extraído:\n{contexto_total}\n\nInstrucción: {pregunta_usuario}"
        
        print("\n[GEMINI] Analizando información dual (Drive + Gmail)...")
        respuesta = model.generate_content(prompt_final)
        
        print("\n================ RESPUESTA DE LA IA ================\n")
        print(respuesta.text)
        print("\n====================================================\n")
        
    except Exception as e:
        print(f"Error crítico en la ejecución: {e}")

if __name__ == '__main__':
    main()

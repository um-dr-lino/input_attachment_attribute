import imaplib
import email as email_parser
import os
import base64
from ..CCR.main import get_full_text

download_folder = "/tmp" 
os.makedirs(download_folder, exist_ok=True)

def connect_email():
    """Conecta ao servidor IMAP e retorna a conexão."""
    print("[DEBUG] Iniciando conexão ao servidor de email")
    mail = imaplib.IMAP4_SSL(host)
    print(f"[DEBUG] Tentando login com usuário: {email}")
    mail.login(email, password)
    print("[DEBUG] Login bem-sucedido")
    return mail
def process_new_emails():
    # Busca o último e-mail não lido e processa seus anexos.
    collection_attachment = {'document_file': []}
    extract_emails = []  # Lista para armazenar multiplos anexos
    mail = connect_email()
    mail.select("inbox")

    # Buscar e-mails não lidos
    status, email_ids = mail.search(None, '(UNSEEN)')
    email_list = email_ids[0].split()
    
    if not email_list:
        print("Nenhum e-mail não lido encontrado.")
        return None, None  # Retorna None para indicar que não há emails

    latest_email_id = email_list[-1]  # Pega o último e-mail não lido
    status, email_data = mail.fetch(latest_email_id, "(RFC822)")

    raw_email = email_data[0][1]
    # Se raw_email for uma string, converta para bytes
    if isinstance(raw_email, str):
        raw_email = raw_email.encode('utf-8')
        msg = email_parser.message_from_bytes(raw_email)

    msg = email_parser.message_from_bytes(raw_email) 

    print("=" * 50)
    print(f"**De:** {msg['From']}")
    print(f"**Assunto:** {msg['Subject']}")
    print("[DEBUG] Procurando por anexos no email")
    has_attachments = False
    # Função para verificar se dentro do email tem anexo
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        if part.get("Content-Disposition") is None:
            continue    
        filename = part.get_filename()
        if filename:
            clean_name = filename.strip().lower()
            if clean_name.startswith("outlook-"):
                print(f"({filename}) ignorado: começa com 'Outlook-'")
                continue
            
            has_attachments = True
            print(f"[DEBUG] Anexo encontrado: {filename}")     
            extract_email = {'file_name': filename}
            file_path = os.path.join(download_folder, filename)
            with open(file_path, "wb") as f:
                payload = part.get_payload(decode=True)
                f.write(payload)
            # Ler os bytes do documento diretamente
            with open(file_path, "rb") as doc_file:
                document_bytes = doc_file.read()
                base64_encoded = base64.b64encode(document_bytes).decode('utf-8')
                extract_email['base64_file'] = base64_encoded
                result = get_full_text(document_bytes)
                extract_email['extracted_text'], extract_email['text_confidence'] = result
            # Add the processed attachment to our list
            extract_emails.append(extract_email)
            # Also update the collection_attachment
            data = {'Name': filename, 'Content': base64_encoded}
            collection_attachment.get('document_file').append(data)
    if not has_attachments:
        print("Nenhum anexo encontrado.")
    print("[DEBUG] Processamento de email concluído!")
    return extract_emails, collection_attachment
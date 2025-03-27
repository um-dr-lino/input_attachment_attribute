from extract_utils import extract_rg, extract_cpf, clean_text,extract_nome,extract_registration_voter,work_card,extract_birthdate,extract_validity_date, extract_street_name
import imaplib
import json
import os
import boto3
import re
from typing import Dict, Any, Optional, Tuple
import traceback
import urllib3
import email as email_parser
import base64
import unicodedata 
from lxml import etree as et

cache = ()
#CONFIGURAÇÕES DE USUARIO, EMAIL E SENHA
host = 'imap.gmail.com'
email = 'linolinocatolica@gmail.com'
password = 'yrzj nqna lota tzwp'
#FIM DA CONFIGURAÇÃO DE EMAIL E SENHA

'''CHAMA A FUNÇÃO TEXTRACT DA LAMBDA E FALA QUAL É O NOME'''
textract = boto3.client('textract', region_name='us-east-1')
http = urllib3.PoolManager()

download_folder = "/tmp" #Local para salvar o arquivo por enquanto vai ficar no meu temp
os.makedirs(download_folder, exist_ok=True)

def connect_email():
    """Conecta ao servidor IMAP e retorna a conexão."""
    print("[DEBUG] Iniciando conexão ao servidor de email")
    mail = imaplib.IMAP4_SSL(host)
    print(f"[DEBUG] Tentando login com usuário: {email}")
    mail.login(email, password)
    print("[DEBUG] Login bem-sucedido")
    return mail

def generation_dynamic_xml(iddocument, nome, cpf, rg, birth_date, voter_registration, validity_date, street_name_value, data):
    
    parser = et.XMLParser(remove_blank_text=True)
    payload = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:document">
            <soapenv:Header/>
            <soapenv:Body>
            <urn:newDocument2>
                <urn:CategoryID>novocolaborador</urn:CategoryID>
                <urn:DocumentID>{iddocument}</urn:DocumentID>
                <urn:Title>{nome}</urn:Title>
                <urn:Summary>Importado via integracao</urn:Summary>
                <urn:Attributes>
                    <urn:item>
                    <urn:ID>cpfnovo</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{cpf}</urn:Value>
                        </urn:item>
                    </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>novorg</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{rg}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>aniver</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{birth_date}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>tituloeleitor</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{voter_registration}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>validadecnh</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{validity_date}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>streetname</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{street_name_value}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                        </urn:Attributes>
                    <urn:Files>
                    </urn:Files>
                    </urn:newDocument2>
                </soapenv:Body>
            </soapenv:Envelope>"""
    
    root = et.fromstring(payload, parser)
    ns = {'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/', 'urn': 'urn:document'}
    
    file_selection = root.find(".//urn:Files", namespaces=ns)
    
    for data_info in data.get('document_file',[]):
        item = et.Element("{urn:document}item")
        Name = et.SubElement(item, "{urn:document}Name")
        Name.text = data_info['Name']
        Content = et.SubElement(item, "{urn:document}Content")
        Content.text = data_info['Content']
        
        file_selection.append(item)
    return et.tostring(root, pretty_print=True, encoding='utf-8').decode('utf-8')

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

def get_full_text(document_bytes: bytes) -> Optional[Tuple[str, dict]]:
    try:
        #Envia documento de anexo para o textract
        print(f"[DEBUG] Enviando documento para o Textract")
        response = textract.detect_document_text(Document={'Bytes': document_bytes})
        # print("[DEBUG] Resposta recebida do Textract")        
        text_blocks = [item.get('Text', '') for item in response.get('Blocks', []) if item.get('BlockType') == 'LINE']
        # print(f"[DEBUG] Número de blocos de texto extraídos: {len(text_blocks)}")
        #Pega a confiabilidade do documento lido
        text_confidence = {
            item.get("Text", ""): item.get("Confidence", 0.0)
            for item in response.get("Blocks", [])
            if item.get("BlockType") in ("LINE", "WORD")
        }
        # print(f"[DEBUG] Número de entradas de confiança: {len(text_confidence)}")
        #Junta todos os blocos de texto em uma única string'''
        full_text = " ".join(text_blocks)
        print("AQUI JAS FULL_TEXT: ", full_text)
        return full_text, text_confidence
    except Exception as e:
        print(f"[ERROR] Textract error: {str(e)}")
        print(f"[ERROR] Traceback1: {traceback.format_exc()}")
        return None  # Retornando None para indicar erro

#importa para dentro do documento
def create_document(extract_email, data):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager()
    url = "https://isc.softexpert.com/apigateway/se/ws/dc_ws.php"
    authorization = "eyJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3MzkyOTk0NTAsImV4cCI6MTg5NzA2NTg1MCwiaWRsb2dpbiI6ImFsaW5vIn0.UY5DZHix28g_pr-V8A-rJYpOCU9MPta6Lc3uKkoGxqw"
    headers = {
        "Authorization": authorization,
        "SOAPAction": "urn:document#newDocument2",
        "Content-Type": "text/xml;charset=utf-8"
    }
    # Safely extract values with fallback
    cpf = extract_email.get("cpf_number", (None, 0.0))
    nome = extract_email.get("nome_social", (None, 0.0))
    rg = extract_email.get("rg_number", (None, 0.0))
    base64_rg = extract_email.get("base64_file")
    file_name = extract_email.get("file_name")
    birth_date = extract_email.get("birth_date", (None, 0.0))
    voter_registration = extract_email.get("voter_registration", (None, 0.0))
    validity_date = extract_email.get("validity_date", (None, 0.0))
    street_name = extract_email.get("street_name", (None, 0.0))
    
    
    print(f"CPF extraído: {cpf}")
    print(f"RG extraído: {rg}")
    print(f"Data de nascimento extraída: {birth_date}")
    print(f"Título de eleitor extraído: {voter_registration}")
    print(f"Data de validade extraída: {validity_date}")
    print(f"Nome da rua: {street_name}")
    # Safely extract the first element or use None
    cpf_value = cpf[0] if cpf and len(cpf) > 0 else None
    nome_value = nome[0] if nome and len(nome) > 0 else None
    rg_value = rg[0] if rg and len(rg) > 0 else None
    birth_date_value = birth_date[0] if birth_date and len(birth_date) > 0 else None
    voter_registration_value = voter_registration[0] if voter_registration and len(voter_registration) > 0 else None   
    validity_date_value = validity_date[0] if validity_date and len(validity_date) > 0 else None
    street_name_value = street_name[0] if street_name and len(street_name) > 0 else None
    # Check required fields
    if not (cpf_value and nome_value and rg_value):
        print(f"[ERRO] Dados obrigatórios ausentes! CPF: {cpf_value}, Nome: {nome_value}, RG: {rg_value}")
        return {"status_code": 400, "message": "Erro: Dados incompletos."}
    # Clean nome if it exists
    if nome_value:
        nome_value = clean_text(nome_value)
    iddocument = f"{cpf_value} - {nome_value}"
    payload = generation_dynamic_xml(iddocument, nome_value, cpf_value, rg_value, birth_date_value, voter_registration_value, validity_date_value, street_name_value, data)
    http = urllib3.PoolManager()
    req = http.request('POST', url=url, headers=headers, body=payload)
    print("Resposta: ", req.data.decode('utf-8'))
    
    xml_response = req.data.decode('utf-8')
    root = et.fromstring(xml_response.encode('utf-8'))

    # Definição do namespace correto
    namespace = {'ns': 'urn:document'}

    # Extração do status
    status_element = root.xpath('.//ns:Code', namespaces=namespace)
    status = status_element[0].text if status_element else "UNKNOWN"
    print("Este é o status que retornou:", status)
    
    return status, iddocument

def update_information(extract_email, iddocument):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager()
    url = "https://isc.softexpert.com/apigateway/se/ws/dc_ws.php"
    authorization = "eyJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3MzkyOTk0NTAsImV4cCI6MTg5NzA2NTg1MCwiaWRsb2dpbiI6ImFsaW5vIn0.UY5DZHix28g_pr-V8A-rJYpOCU9MPta6Lc3uKkoGxqw"
    headers = {
        "Authorization": authorization,
        "SOAPAction": "urn:document#newDocument",
        "Content-Type": "text/xml;charset=utf-8"
    }    
    
    fields = ["cpf_number", "rg_number", "birth_date", "voter_registration", "validity_date", "street_name"]
    values = {}

    for field in fields:
        data = extract_email.get(field, (None, 0.0))
        
        if data is None or data[0] is None:  # Se não houver valor, pula para o próximo
            continue

        values[field] = data[0]

    # Se precisar acessar os valores depois:
    cpf = values.get("cpf_number")
    rg = values.get("rg_number")
    birth_date = values.get("birth_date")
    voter_registration = values.get("voter_registration")
    validity_date = values.get("validity_date")
    street_name = values.get("street_name")
    # cpf = extract_email.get("cpf_number", (None, 0.0))[0]
    # rg = extract_email.get("rg_number", (None, 0.0))[0]
    # birth_date = extract_email.get("birth_date", (None, 0.0))[0]
    # voter_registration = extract_email.get("voter_registration", (None, 0.0))
    # validity_date = extract_email.get("validity_date", (None, 0.0))[0]   
    # street_name = extract_email.get("street_name", (None, 0.0))[0]   
       
    parser = et.XMLParser(remove_blank_text=True)   
    # Lista de nomes para identificar os campos
    campos = [
        'cpfnovo',
        'novorg', 
        'aniver',
        'tituloeleitor',
        'validadecnh',
        'streetname'
    ]
    # Lista com os dados
    combined_data = [
        cpf,
        rg,
        birth_date,
        voter_registration,
        validity_date,
        street_name
    ]
    # Cria uma lista de dicionários apenas para campos preenchidos
    campos_preenchidos = [
        {campo: valor} 
        for campo, valor in zip(campos, combined_data) if valor is not None and valor != ""
    ]
    # Itera sobre os campos preenchidos
    for campo_dict in campos_preenchidos:
        # Obtém o nome do campo e seu valor
        for campo, valor in campo_dict.items():
            payload = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:document">
            <soapenv:Header/>
            <soapenv:Body>
                <urn:setAttributeValue>
                    <urn:iddocument>{iddocument}</urn:iddocument>
                    <urn:idattribute>{campo}</urn:idattribute>
                    <urn:vlattribute>{valor}</urn:vlattribute>
                </urn:setAttributeValue>
            </soapenv:Body>
            </soapenv:Envelope>
            """
            # Realiza a requisição para cada campo
            req = http.request('POST', url=url, headers=headers, body=payload)
            print(f"Resposta para {campo}: {req.data.decode('utf-8')}")
            
    return

def update_eletronic_files(extract_email_list, iddocument):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager()
    url = "https://isc.softexpert.com/apigateway/se/ws/dc_ws.php"
    authorization = "eyJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3MzkyOTk0NTAsImV4cCI6MTg5NzA2NTg1MCwiaWRsb2dpbiI6ImFsaW5vIn0.UY5DZHix28g_pr-V8A-rJYpOCU9MPta6Lc3uKkoGxqw"
    headers = {
        "Authorization": authorization,
        "SOAPAction": "urn:document#newDocument",
        "Content-Type": "text/xml;charset=utf-8"
    } 
    
    # Verificar se extract_email_list é uma lista de dicionários
    if not isinstance(extract_email_list, list):
        # Se não for uma lista, converte para lista
        extract_email_list = [extract_email_list]
    
    for idx, extract_email in enumerate(extract_email_list, 1):
        # Verifica se o item é um dicionário, se não for, tenta converter
        if not isinstance(extract_email, dict):
            try:
                extract_email = dict(extract_email)
            except:
                print(f"Não foi possível processar o anexo {idx}")
                continue
        
        base64_file = extract_email.get('base64_file')
        file_name = extract_email.get('file_name')
        
        # Verifica se os campos necessários estão presentes
        if not base64_file or not file_name:
            print(f"Anexo {idx} ignorado: dados incompletos")
            continue
    
        payload = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:document">
        <soapenv:Header/>
        <soapenv:Body>
            <urn:uploadEletronicFile>
                <urn:iddocument>{iddocument}</urn:iddocument>
                <urn:file>
                    <urn:item>
                    <urn:NMFILE>{base64_file}</urn:NMFILE>
                    <urn:BINFILE>{file_name}</urn:BINFILE>
                    </urn:item>
                </urn:file>
            </urn:uploadEletronicFile>
        </soapenv:Body>
        </soapenv:Envelope>"""
        
        try:
            req = http.request('POST', url=url, headers=headers, body=payload)
            print(f"Resposta para anexo {idx} ({file_name}): {req.data.decode('utf-8')}")
        except Exception as e:
            print(f"Erro ao fazer upload do anexo {idx} ({file_name}): {str(e)}")
    
    
def lambda_handler(event, context):
    global cache
    try:
        # Processar um único email e obter o texto extraído
        extract_emails, data = process_new_emails()

        # Verificar se o email foi extraído corretamente
        if not extract_emails:
            print("[DEBUG] Nenhum email encontrado ou sem texto extraído. Processando corpo da solicitação...")
            return {
                'statusCode': 404, 
                'body': json.dumps({
                    'message': 'No content to process'
                })
            }
        
        # Combined data from all attachments
        combined_data = {
            'cpf_number': None,
            'rg_number': None,
            'nome_social': None,
            'birth_date': None,
            'validity_date': None,
            'voter_registration': None,
            'street_name': None,
            'base64_file': None,
            'file_name': None
        }
            
        # Process each attachment separately to extract data
        for i, extract_email in enumerate(extract_emails):
            print(f"[DEBUG] Processing attachment {i+1}/{len(extract_emails)}: {extract_email.get('file_name')}")
            
            if 'extracted_text' not in extract_email or not extract_email['extracted_text']:
                print(f"[DEBUG] No text extracted from attachment {i+1}")
                continue                
            
            # Extract data from this attachment
            cpf = extract_cpf(extract_email['extracted_text'], extract_email['text_confidence'])
            rg = extract_rg(extract_email['extracted_text'], extract_email['text_confidence'])
            nome = extract_nome(extract_email['extracted_text'], extract_email['text_confidence'])
            birth_date = extract_birthdate(extract_email['extracted_text'], extract_email['text_confidence']) 
            validity_date = extract_validity_date(extract_email['extracted_text'], extract_email['text_confidence'])
            voter_reg = extract_registration_voter(extract_email['extracted_text'], extract_email['text_confidence'])
            street_name = extract_street_name(extract_email['extracted_text'], extract_email['text_confidence'])
            
            # Update combined data with non-None values
            if cpf[0] and not combined_data['cpf_number']:
                combined_data['cpf_number'] = cpf
            if rg[0] and not combined_data['rg_number']:
                combined_data['rg_number'] = rg
            if nome[0] and not combined_data['nome_social']:
                combined_data['nome_social'] = nome
            if birth_date[0] and not combined_data['birth_date']:
                combined_data['birth_date'] = birth_date
            if validity_date[0] and not combined_data['validity_date']:
                combined_data['validity_date'] = validity_date
            if voter_reg[0] and not combined_data['voter_registration']:
                combined_data['voter_registration'] = voter_reg
            if street_name[0] and not combined_data['street_name']:
                combined_data['street_name'] = street_name
            
            # Save the first attachment info for document creation
            # This assumes the first attachment (RG) is the one we want to upload
            if i == 0:
                combined_data['base64_file'] = extract_email.get('base64_file')
                combined_data['file_name'] = extract_email.get('file_name')

        # Add the combined data to cache
        cache += (combined_data,)
        
        # Create a single document with the combined data
        status, iddocument = create_document(combined_data, data)
        
        # Nova validação: Verifica se o nome do arquivo contém o CPF
        if status == '18':
            update_information(combined_data, iddocument)
            update_eletronic_files(combined_data, iddocument)
                                
        return {
            'statusCode': 200, 
            'body': json.dumps({
                'message': f'Email processed successfully with {len(extract_emails)} attachments'
            })
        }

    except Exception as e:
        print(f"[ERROR] Erro no processamento: {str(e)}")
        print(f"[ERROR] Traceback2: {traceback.format_exc()}")
        return {
            'statusCode': 500, 
            'body': json.dumps({
                'error': str(e)
            })
        }
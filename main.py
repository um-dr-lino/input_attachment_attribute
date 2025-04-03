from extract_utils import *
from read_document import read_document
from connectemail import process_new_emails
import imaplib
import json
import os
import boto3
from typing import Dict, Any, Optional, Tuple
import traceback
import urllib3
import email as email_parser
from lxml import etree as et

cache = ()
#CONFIGURAÇÕES DE USUARIO, EMAIL E SENHA
host = os.environ.get('host')
email = os.environ.get('email')
password = os.environ.get('password')
#FIM DA CONFIGURAÇÃO DE EMAIL E SENHA

#CHAMA A FUNÇÃO TEXTRACT DA LAMBDA E FALA QUAL É O NOME'''
textract = boto3.client('textract', region_name='us-east-1')
http = urllib3.PoolManager()

download_folder = "/tmp" #Local para salvar o arquivo por enquanto vai ficar no meu temp
os.makedirs(download_folder, exist_ok=True)

def generation_dynamic_xml(campos):
    parser = et.XMLParser(remove_blank_text=True)
    payload = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:document">
            <soapenv:Header/>
            <soapenv:Body>
            <urn:newDocument2>
                <urn:CategoryID>novocolaborador</urn:CategoryID>
                <urn:DocumentID>{campos['iddocument']}</urn:DocumentID>
                <urn:Title>{campos['nome']}</urn:Title>
                <urn:Summary>Importado via integracao</urn:Summary>
                <urn:Attributes>
                    <urn:item>
                    <urn:ID>cpfnovo</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{campos['cpf']}</urn:Value>
                        </urn:item>
                    </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>novorg</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{campos['rg']}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>aniver</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{campos['birth_date']}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>tituloeleitor</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{campos['voter_registration']}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>validadecnh</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{campos['validity_date']}</urn:Value>
                        </urn:item>
                        </urn:Values>
                    </urn:item>
                    <urn:item>
                    <urn:ID>streetname</urn:ID>
                    <urn:Values>
                        <urn:item>
                            <urn:Value>{campos['street_name_value']}</urn:Value>
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
    
    for data_info in campos['data'].get('document_file',[]):
        item = et.Element("{urn:document}item")
        Name = et.SubElement(item, "{urn:document}Name")
        Name.text = data_info['Name']
        Content = et.SubElement(item, "{urn:document}Content")
        Content.text = data_info['Content']
        file_selection.append(item)
    return et.tostring(root, pretty_print=True, encoding='utf-8').decode('utf-8')

def get_full_text(document_bytes: bytes) -> Optional[Tuple[str, dict]]:
    try:
        #Envia documento de anexo para o textract
        print(f"[DEBUG] Enviando documento para o Textract")
        response = textract.detect_document_text(Document={'Bytes': document_bytes})      
        text_blocks = [item.get('Text', '') for item in response.get('Blocks', []) if item.get('BlockType') == 'LINE']
        text_confidence = {
            item.get("Text", ""): item.get("Confidence", 0.0)
            for item in response.get("Blocks", [])
            if item.get("BlockType") in ("LINE", "WORD")
        }
        full_text = " ".join(text_blocks)
        return full_text, text_confidence
    except Exception as e:
        print(f"[ERROR] Textract error: {str(e)}")
        print(f"[ERROR] Traceback1: {traceback.format_exc()}")
        return None

#importa para dentro do documento
def create_document(extract_email, data):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager()
    url = "https://isc.softexpert.com/apigateway/se/ws/dc_ws.php"
    headers = {
        "Authorization": os.getenv("Authorization"),
        "SOAPAction": "urn:document#newDocument2",
        "Content-Type": "text/xml;charset=utf-8"
    }
    campos = {}
    campos['cpf'] = extract_email.get("cpf_number", (None, 0.0))
    campos['nome'] = extract_email.get("nome_social", (None, 0.0))
    campos['rg'] = extract_email.get("rg_number", (None, 0.0))
    campos['birth_date'] = extract_email.get("birth_date", (None, 0.0))
    campos['voter_registration'] = extract_email.get("voter_registration", (None, 0.0))
    campos['validity_date'] = extract_email.get("validity_date", (None, 0.0))
    campos['street_name'] = extract_email.get("street_name", (None, 0.0))

    # Safely extract the first element or use None
    campos['cpf_value'] = campos['cpf'] if campos['cpf'] and len(campos['cpf']) > 0 else None
    campos['nome_value'] = campos['nome'][0] if campos['nome'] and len(campos['nome']) > 0 else None
    campos['rg_value'] = campos['rg'][0] if campos['rg'] and len(campos['rg']) > 0 else None
    campos['birth_date_value'] = campos['birth_date'][0] if campos['birth_date'] and len(campos['birth_date']) > 0 else None
    campos['voter_registration_value'] = campos['voter_registration'][0] if campos['voter_registration'] and len(campos['voter_registration']) > 0 else None
    campos['validity_date_value'] = campos['validity_date'][0] if campos['validity_date'] and len(campos['validity_date']) > 0 else None
    campos['street_name_value'] = campos['street_name'][0] if campos['street_name'] and len(campos['street_name']) > 0 else None
    if nome_value:
        nome_value = clean_text(nome_value)
    iddocument = (f"['cpf_value']  - campos['nome_value']")
    # Check required fields
    if not (campos['cpf_value'] and nome_value and campos['rg_value']):
        print(f"[ERRO] Dados obrigatórios ausentes!")
        print("Mandando para conferir se o cadastro já existe")
        read_document(extract_email)
        return {"status_code": 400, "message": "Erro: Dados incompletos."}
    # Clean nome if it exists
    payload = generation_dynamic_xml(campos)
    http = urllib3.PoolManager()
    req = http.request('POST', url=url, headers=headers, body=payload)
    # print("Resposta: ", req.data.decode('utf-8'))
    xml_response = req.data.decode('utf-8')
    root = et.fromstring(xml_response.encode('utf-8'))
    # Definição do namespace correto
    namespace = {'ns': 'urn:document'}

    # Extração do status
    status_element = root.xpath('.//ns:Code', namespaces=namespace)
    status = status_element[0].text if status_element else "UNKNOWN"
    print("Este é o status que retornou:", status)
    
    return status, iddocument          
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
        if status == '18':
            read_document(combined_data)
                              
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
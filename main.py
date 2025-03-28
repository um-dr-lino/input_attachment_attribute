from .extract_utils import extract_rg, extract_cpf, clean_text,extract_nome,extract_registration_voter,work_card,extract_birthdate,extract_validity_date, extract_street_name
from CCR.connectemail import connect_email, process_new_emails
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
host = os.environ.get('host')
email = os.environ.get('email')
password = os.environ.get('password')

textract = boto3.client('textract', region_name='us-east-1')
http = urllib3.PoolManager()

download_folder = "/tmp" 
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
        "Authorization": os.environ.get('Authorization'),
        "SOAPAction": "urn:document#newDocument2",
        "Content-Type": "text/xml;charset=utf-8"
    }
    campos = {}
    # Safely extract values with fallback
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

    # Check required fields
    if not (campos['cpf_value'] and nome_value and campos['rg_value']):
        print(f"[ERRO] Dados obrigatórios ausentes! CPF: ['cpf_value'] , Nome: {nome_value}, RG: campos['rg_value']")
        return {"status_code": 400, "message": "Erro: Dados incompletos."}
    # Clean nome if it exists
    if nome_value:
        nome_value = clean_text(nome_value)
    iddocument = (f"['cpf_value']  - campos['nome_value']")
    payload = generation_dynamic_xml(campos)
    http = urllib3.PoolManager()
    req = http.request('POST', url=url, headers=headers, body=payload)
    xml_response = req.data.decode('utf-8')
    root = et.fromstring(xml_response.encode('utf-8'))
    # Definição do namespace correto
    namespace = {'ns': 'urn:document'}
    # Extração do status
    status_element = root.xpath('.//ns:Code', namespaces=namespace)
    status = status_element[0].text if status_element else "UNKNOWN"
    return status, iddocument

def update_information(extract_email, iddocument):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager()
    url = "https://isc.softexpert.com/apigateway/se/ws/dc_ws.php"
    headers = {
        "Authorization": os.environ.get('Authorization'),
        "SOAPAction": "urn:document#newDocument",
        "Content-Type": "text/xml;charset=utf-8"
    }      
    fields = ["cpf_number", "rg_number", "birth_date", "voter_registration", "validity_date", "street_name"]
    values = {}

    for field in fields:
        data = extract_email.get(field, (None, 0.0))      
        if data and data[0] is not None: values[field] = data[0]

    # Se precisar acessar os valores depois:
    cpf = values.get("cpf_number")
    rg = values.get("rg_number")
    birth_date = values.get("birth_date")
    voter_registration = values.get("voter_registration")
    validity_date = values.get("validity_date")
    street_name = values.get("street_name")       
    # Lista de nomes para identificar os campos
    campos = ['cpfnovo','novorg','aniver','tituloeleitor','validadecnh','streetname']
    # Lista com os dados
    combined_data = [cpf,rg,birth_date,voter_registration,validity_date,street_name]
    # Cria uma lista de dicionários apenas para campos preenchidos
    campos_preenchidos = [{campo: valor} 
        for campo, valor in zip(campos, combined_data) if valor is not None and valor != ""
    ]
    # Itera sobre os campos preenchidos
    for campo_dict in campos_preenchidos:
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
            http.request('POST', url=url, headers=headers, body=payload)     
    return

def update_eletronic_files(extract_email_list, iddocument):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager()
    url = "https://isc.softexpert.com/apigateway/se/ws/dc_ws.php"
    headers = {
        "Authorization": os.environ.get('Authorization'),
        "SOAPAction": "urn:document#newDocument",
        "Content-Type": "text/xml;charset=utf-8"
    }  
    if not isinstance(extract_email_list, list):
        extract_email_list = [extract_email_list]
    for idx, extract_email in enumerate(extract_email_list, 1):
        if not isinstance(extract_email, dict):
            try:
                extract_email = dict(extract_email)
            except:
                print(f"Não foi possível processar o anexo {idx}")
                continue
        base64_file = extract_email.get('base64_file')
        file_name = extract_email.get('file_name')
        
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
                    <urn:NMFILE>{file_name}</urn:NMFILE>
                    <urn:BINFILE>{base64_file}</urn:BINFILE>
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
        extract_emails, data = process_new_emails()
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
            'cpf_number': None,'rg_number': None,'nome_social': None,'birth_date': None,'validity_date': None,
            'voter_registration': None,'street_name': None,'base64_file': None,'file_name': None}
        # Process each attachment separately to extract data
        for i, extract_email in enumerate(extract_emails):
            print(f"[DEBUG] Processing attachment {i+1}/{len(extract_emails)}: {extract_email.get('file_name')}")
            if 'extracted_text' not in extract_email or not extract_email['extracted_text']:
                print(f"[DEBUG] Nenhum texto extraído do anexo {i+1}")
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
            combined_data['cpf_number'] = cpf if cpf and not combined_data.get('cpf_number') else combined_data['cpf_number']
            combined_data['rg_number'] = rg if rg and not combined_data.get('rg_number') else combined_data['rg_number']
            combined_data['nome_social'] = nome if nome and not combined_data.get('nome_social') else combined_data['nome_social']
            combined_data['birth_date'] = birth_date if birth_date and not combined_data.get('birth_date') else combined_data['birth_date']
            combined_data['validity_date'] = validity_date if validity_date and not combined_data.get('validity_date') else combined_data['validity_date']
            combined_data['voter_registration'] = voter_reg if voter_reg and not combined_data.get('voter_registration') else combined_data['voter_registration']
            combined_data['street_name'] = street_name if street_name and not combined_data.get('street_name') else combined_data['street_name']      
            # This assumes the first attachment (RG) is the one we want to upload
            if i == 0:
                combined_data['base64_file'] = extract_email.get('base64_file')
                combined_data['file_name'] = extract_email.get('file_name')
        # Armazena a informação em memória "cache"
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
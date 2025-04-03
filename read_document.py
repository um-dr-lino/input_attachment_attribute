import json
import re
import urllib3
import os
from extract_utils import clean_text
from lxml import etree as et

def update_information(extract_email, iddocument):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager()
    url = "https://isc.softexpert.com/apigateway/se/ws/dc_ws.php"
    headers = {
        "Authorization": os.getenv("Authorization"),
        "SOAPAction": "urn:document#newDocument",
        "Content-Type": "text/xml;charset=utf-8"
    }     
    fields = ["voter_registration", "validity_date", "street_name"]
    values = {}

    for field in fields:
        data = extract_email.get(field, (None, 0.0))
        if data is None or data[0] is None:  # Se não houver valor, pula para o próximo
            continue
        values[field] = data[0]
    # Se precisar acessar os valores depois:
    voter_registration = values.get("voter_registration")
    validity_date = values.get("validity_date")
    street_name = values.get("street_name")
    parser = et.XMLParser(remove_blank_text=True)   
    # Lista de nomes para identificar os campos
    campos = [
        'tituloeleitor',
        'validadecnh',
        'streetname'
    ]
    # Lista com os dados
    combined_data = [
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
    headers = {
        "Authorization": os.getenv("Authorization"),
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
        # Normaliza o nome do arquivo
        clean_name = file_name.strip().lower()
        if clean_name.startswith("outlook-"):
            print(f"Anexo {idx} ({file_name}) ignorado: começa com 'Outlook-'")
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

def read_document(extract_email):
    fields = ["file_name", "voter_registration", "validity_date", "street_name"]
    values = {}
    for field in fields:
        data = extract_email.get(field, (None, 0.0))
        if data is None or data[0] is None:  # Se não houver valor, pula para o próximo
            continue
        values[field] = data
    file_name = clean_text(values.get("file_name")) 
    file_name = ''.join(re.findall(r'\d+', file_name))  
    cpf = file_name    
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    http = urllib3.PoolManager()
    url = "https://isc.softexpert.com/apigateway/v1/dataset-integration/textract"
    headers = {
        "Authorization": os.getenv("Authorization"),
        "Content-Type": "application/json"
    }
    payload = { 
        "cpf": cpf
    }
    response = http.request('POST', url=url, headers=headers, body=json.dumps(payload))
    response_data = json.loads(response.data.decode("utf-8"))
    formatted_response = json.dumps(response_data, indent=4, ensure_ascii=False)
    if (response_data[0]["cpf"]) == cpf:
        update_information(extract_email, response_data[0]["titulo"])   
        update_eletronic_files(extract_email, response_data[0]["titulo"])
    else:
        print("Não foi possível encontrar o CPF no documento.")
    return response_data
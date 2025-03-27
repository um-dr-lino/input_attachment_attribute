import re
import unicodedata 

def clean_text(texto):
   #Remove acentos e caracteres especiais, mantendo apenas letras, números e espaços.
    if not isinstance(texto, str):  
        return texto  # Retorna como está se não for string

    # Remove acentos
    texto_sem_acentos = ''.join(
        c for c in unicodedata.normalize('NFD', texto) 
        if unicodedata.category(c) != 'Mn'
    )
    # Remove caracteres especiais (mantém apenas letras, números e espaços)
    texto_limpo = re.sub(r'[^A-Za-z0-9\s]', '', texto_sem_acentos)
    
    return texto_limpo

def extract_rg(text: str, confidence_score: dict):
    match = re.search(r'\D(\d{1}\.\d{3}\.\d{3})\D', text)
    if not match:
        match = re.search(r'\D(\d{2}\.\d{3}\.\d{3}-\d{1})\D', text)  
        if not match:
            match = re.search(r'UF\s*(\d+)', text)
            if not match:
                match = re.search(r'GERAL\s*(\d+)', text)
                if not match:
                    match = re.search(r'(\S+)\s*SSP', text)
    if match:
        result = match.group(1)      
        # buscar o confidence de um trecho de texto
        confidence = confidence_score.get(result, 0.0)
        print(f"[DEBUG] RG encontrado: {result}, Confiança para o RG: {confidence}")
        return result, confidence
    print("[DEBUG] RG not found.")
    return None, 0.0  # Valor padrão para quando não encontrado

def extract_street_name(text: str, confidence_score: dict):
    matches = re.findall(r'\b(?:Rua|R\.|Avenida|Travessa|Estrada|Alameda|Rodovia|R)\s+([A-Za-zÀ-ÿ\s]+)', text, re.IGNORECASE)
    if not matches:  # Se não encontrar nada, retorna None e confiança 0.0
        print("[DEBUG] Nenhum nome de rua encontrado.")
        return None, 0.0
    # Se houver mais de um resultado, pega o segundo; senão, pega o primeiro
    result = matches[1] if len(matches) > 1 else matches[0]
    # Só busca a confiança se `result` não for None
    confidence = confidence_score.get(result, 0.0)
    print(f"[DEBUG] Nome da rua encontrado: {result}, Confiança: {confidence}")
    return result, confidence


#Extrai o número de CPF em diferentes formatos.
def extract_cpf(text: str, confidence_score: dict):
    #Extrai o número de CPF em diferentes formatos.
    
    # Define os padrões de CPF
    patterns = [
        r'\b\d{9}/\d{2}\b', # 000000000/00
        r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b',  # 000.000.000-00
        r'\b\d{3}-\d{3}-\d{3}-\d{2}\b',    # 000-000-000-00
        r'\b\d{3} \d{3} \d{3} \d{2}\b',    # 000 000 000 00
        r'\b\d{11}\b',                     # 00000000000
        r'\b\d{3}\.\d{3}\.\d{3}\b',        # 000.000.000
        r'\b\d{3}/\d{3}/\d{3}-\d{2}\b',    # 000/000/000-00
        r'\[\b\d{3}\.\d{3}\.\d{3}-\d{2}\b\]',  # [000.000.000-00]
        r'\(\b\d{3}\.\d{3}\.\d{3}-\d{2}\b\)',  # (000.000.000-00)
        r'\b\d{3}\.\s*\d{3}\.\s*\d{3}-\s*\d{2}\b',  # 000. 000. 000- 00
        r'\b\d{3}-\s*\d{3}-\s*\d{3}-\s*\d{2}\b'  # 000- 000- 000- 00
    ]
    
    # Percorre todos os padrões
    for i, pattern in enumerate(patterns, 1):
        match = re.search(pattern, text)
        
        if match:
            raw_cpf = match.group(0)
            result = re.sub(r'\D', '', raw_cpf)
            # Garante que o resultado tenha 11 dígitos
            if len(result) == 11:
                # Adiciona formatação padrão 000.000.000-00
                result = f"{result[:3]}.{result[3:6]}.{result[6:9]}-{result[9:]}"
            confidence = confidence_score.get(result, 0.0)
            print(f"[DEBUG] CPF encontrado: {result}, Confiança do CPF: {confidence}")
            return result, confidence
    
    print("[DEBUG] Nenhum CPF encontrado.")
    return None, 0.0

#Extrai o Nome Social do texto, mesmo que esteja tudo em uma única linha.
def extract_nome(text: str, confidence_score: dict):
    match = re.search(r'NOME\s+([A-ZÁÀÉÈÍÌÓÒÚÙÇãõâêîôûäëïöü\s]+)\s+FILIAÇÃO', text)
    if not match:
        match = re.search(r'NOME\s+([A-ZÁÀÉÈÍÌÓÒÚÙÇãõâêîôûäëïöü\s]+)\s+DOC', text)
        if not match: 
            match = re.search(r'HABILITAÇÃO\s+([A-ZÁÀÉÈÍÌÓÒÚÙÇãõâêîôûäëïöü\s]+)\s+\d', text)
    if match:
            result = match.group(1).strip()
            confidence = confidence_score.get(result, 0.0)  
            print(f"[DEBUG] Nome encontrado: {result}, Confiança para o Nome: {confidence}")
            return result, confidence
    print("[DEBUG] Nenhum nome encontrado.")
    return None, 0.0  

def extract_registration_voter(text: str, confidence_score: dict):    
    patterns = [
        r'\b\d{12}\b', #000000000000
        r'\b\d{4} \d{4} \d{4}\b',  # 0000 0000 0000
        r'\b\d{4}\.\d{4}\.\d{4}\b',  # 0000.0000.0000
        r'\b\d{3}\.\d{4} \d{4}\b',  # 000.0000 0000
        r'\b\d{3} \d{4}\.\d{4}\b',   # 000 0000.0000
        r'\b\d{4}\.\d{4} \d{4}\b',  # 0000.0000 0000
        r'\b\d{4} \d{4}\.\d{4}\b'   # 0000 0000.0000
    ]
    match = re.search(r"(.*?)\bMUNICÍPIO\b", text, re.IGNORECASE)
    
    if match:
        texto_antes_municipio = match.group(1)  # Trecho antes de MUNICÍPIO
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, texto_antes_municipio)
            if match:
                result = match.group(0)
                confidence = confidence_score.get(result, 0.0)  # Obtém a confiança do dicionário
                print(f"[DEBUG] Número do título de eleitor encontrado: {result} (Confiança: {confidence})")
                return result, confidence
            else:
                print(f"[DEBUG] Padrão {i+1} não encontrou correspondência")
    
    # Fallback: try searching the entire text if we couldn't find anything before MUNICÍPIO
    for i, pattern in enumerate(patterns):
        match = re.search(pattern, text)
        if match:
            result = match.group(0)
            confidence = confidence_score.get(result, 0.0)
            print(f"[DEBUG] Número do título de eleitor encontrado no texto completo: {result} (Confiança: {confidence})")
            return result, confidence

    print("[DEBUG] Nenhum número de título de eleitor encontrado.")
    return None, 0.0

def work_card(text: str, confidence_score: dict):
    match = re.search(r'\b\d{3}\.\d{5}\.\d{2}-\d\b', text)
    result = match.group(0) if match else None
    confidence = confidence_score.get(result, 0.0)   
    if match:
            result = match.group(0).strip()
            print(f"[DEBUG] Nome encontrado: {result}")
            confidence = confidence_score.get(result, 0.0)  # Busca a confiança
            print(f"[DEBUG] Confiança para o Nome: {confidence}")
            return result, confidence
        
def extract_birthdate(text: str, confidence_score: dict):
    date_pattern = r'\b(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b'
    # Encontra todas as datas no texto
    matches = re.findall(date_pattern, text)
    if len(matches) >= 2:
        result = matches[1]  # Retorna a segunda data encontrada
        print(f"[DEBUG] Segunda data de nascimento encontrada: {result}")
    elif matches:
        result = matches[0]  # Se houver apenas uma data, retorna essa
        print(f"[DEBUG] Apenas uma data encontrada: {result}")
    else:
        print("[DEBUG] Nenhuma data de nascimento encontrada.")
        return None, 0.0  # Retorno padrão caso não encontre nenhuma data
    # Obtém a confiança da data extraída (se existir no dicionário)
    confidence = confidence_score.get(result, 0.0)
    print(f"[DEBUG] Confiança para a data de nascimento: {confidence}")
    return result, confidence

def extract_validity_date(text: str, confidence_score: dict):
    # Expressão regular para encontrar a data após a palavra "VALIDADE"
    match = re.search(r'VALIDADE.*?(\d{2}/\d{2}/\d{4})', text)
    
    if match:
        result = match.group(1)
    else:
        print("[DEBUG] Nenhuma data de validade encontrada.")
        return None, 0.0  # Retorno padrão caso não encontre a data
    
    # Obtém a confiança da data extraída (se existir no dicionário)
    confidence = confidence_score.get(result, 0.0)
    print(f"[DEBUG] Data de validade encontrada: {result}, Confiança para a data de validade: {confidence}")
    
    return result, confidence

def extract_validity_date(text: str, confidence_score: dict):
    match = re.search(r'VALIDADE.*?(\d{2}/\d{2}/\d{4}).*?(\d{2}/\d{2}/\d{4})', text)
    if match:
        result = match.group(2)  # Pegamos a SEGUNDA data encontrada
    else:
        print("[DEBUG] Nenhuma data de validade encontrada.")
        return None, 0.0  # Retorno padrão caso não encontre a data
    
    # Obtém a confiança da data extraída (se existir no dicionário)
    confidence = confidence_score.get(result, 0.0)
    print(f"[DEBUG] Data de validade encontrada: {result}, Confiança para a data de validade: {confidence}")
    
    return result, confidence
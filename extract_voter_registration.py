import re
def extract_registration_voter(text: str, confidence_score: dict):
    """Extrai o número do título de eleitor em diferentes formatos."""
    
    # Define patterns at the beginning of the function so they're always available
    patterns = [
        r'\b\d{4} \d{4} \d{4}\b',  # 0000 0000 0000
        r'\b\d{4}\.\d{4}\.\d{4}\b',  # 0000.0000.0000
        r'\b\d{3}\.\d{4} \d{4}\b',  # 000.0000 0000
        r'\b\d{3} \d{4}\.\d{4}\b',   # 000 0000.0000
        r'\b\d{4}\.\d{4} \d{4}\b',  # 0000.0000 0000
        r'\b\d{4} \d{4}\.\d{4}\b'   # 0000 0000.0000
    ]
    
    print(f"[DEBUG] Procurando 'MUNICÍPIO' no texto...")
    municipio_match = re.search(r"\bMUNICÍPIO\b", text, re.IGNORECASE)
    if municipio_match:
        print(f"[DEBUG] 'MUNICÍPIO' encontrado na posição {municipio_match.start()}")
    else:
        print(f"[DEBUG] 'MUNICÍPIO' não encontrado no texto!")
    
    match = re.search(r"(.*?)\bMUNICÍPIO\b", text, re.IGNORECASE)
    
    if match:
        texto_antes_municipio = match.group(1)  # Trecho antes de MUNICÍPIO
        print(f"[DEBUG] Texto antes de MUNICÍPIO: '{texto_antes_municipio}'")

        for i, pattern in enumerate(patterns):
            print(f"[DEBUG] Tentando padrão {i+1}: '{pattern}'")
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
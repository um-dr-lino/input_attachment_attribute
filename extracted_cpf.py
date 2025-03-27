import re
def extract_cpf(text: str, confidence_score: dict):
   
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
        print(f"[DEBUG] Tentando padrão {i}: '{pattern}'")
        match = re.search(pattern, text)
        
        if match:
            raw_cpf = match.group(0)
            result = re.sub(r'\D', '', raw_cpf)
            # Garante que o resultado tenha 11 dígitos
            if len(result) == 11:
                # Adiciona formatação padrão 000.000.000-00
                result = f"{result[:3]}.{result[3:6]}.{result[6:9]}-{result[9:]}"
            confidence = confidence_score.get(result, 0.0)
            print(f"[DEBUG] CPF encontrado: {result}")
            print(f"[DEBUG] Confiança do CPF: {confidence}")
            return result, confidence
    
    print("[DEBUG] Nenhum CPF encontrado.")
    return None, 0.0
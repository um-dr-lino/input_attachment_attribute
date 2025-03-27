import re
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
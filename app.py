import os
import json
import base64
import re
from flask import Flask, request, jsonify
import anthropic

# === TUTAJ WKLEJ SWÓJ KLUCZ API OD ANTHROPIC (CLAUDE) ===
CLAUDE_API_KEY = "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" 
# =======================================================

app = Flask(__name__)

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

@app.route('/api/vision/analyze-cards', methods=['POST'])
def analyze_hand():
    if 'image' not in request.files:
        return jsonify({"error": "Brak pliku 'image' w żądaniu"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Nie wybrano żadnego pliku"}), 400

    file_bytes = file.read()
    print(f"\n[CLAUDE VISION] Odebrano zdjęcie do analizy: {file.filename} ({len(file_bytes)} bajtów)")

    image_base64 = base64.b64encode(file_bytes).decode('utf-8')

    prompt = """
    Jesteś profesjonalnym systemem brydżowym AI. Twoim zadaniem jest wykryć i wypisać wszystkie karty brydżowe widoczne na zdjęciu.
    
    Zwróć wynik BEZWZGLĘDNIE i WYŁĄCZNIE jako czстый, surowy format JSON (obiekt zawierający klucz "cards"):
    {"cards": ["KARTA1", "KARTA2", ...]}
    
    ZASADY BEZPIECZEŃSTWA:
    1. Jeśli na zdjęciu jest mniej lub więcej niż 13 kart (np. tylko 1 karta), po prostu wypisz ją w liście, np. {"cards": ["AP"]}.
    2. NIE DOPISUJ żadnych komentarzy, wyjaśnień, ostrzeżeń ani zdań w stylu "Na zdjęciu widoczna jest...".
    3. Nie używaj formatowania markdown (```json). Zwróć wyłącznie nawiasy klamrowe i dane.
    
    Oznaczenia kolorów: P (Pik), C (Czerwień/Kier), K (Karo), T (Trefl)
    Oznaczenia figur: A (As), K (Król), Q (Dama), J (Walet), 10, 9, 8, 7, 6, 5, 4, 3, 2
    """

    try:
        print("[CLAUDE VISION] Wysyłam zapytanie do modelu Claude Sonnet 5...")
        
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64}},
                        {"type": "text", "text": prompt}
                    ],
                }
            ],
        )

        # OFICJALNY POPRAWNY SPOSÓB: Wyciąganie tekstu z pierwszego bloku odpowiedzi content
        response_text = ""
        if response.content and len(response.content) > 0:
            response_text = response.content[0].text.strip()
        
        print(f"[CLAUDE VISION] Surowa odpowiedź od AI: {response_text}")

        # OBRONA PRZED KOMENTARZAMI: Filtrujemy dane, izolując wyłącznie strukturę nawiasów klamrowych { }
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
            print(f"[CLAUDE VISION] Oczyszczono tekst do formatu JSON: {response_text}")
        else:
            raise ValueError("Serwer AI nie zwrócił poprawnego formatu JSON wewnątrz tekstu odpowiedzi.")

        # Parsowanie oczyszczonego tekstu i bezpieczny zwrot do telefonu
        result_json = json.loads(response_text)
        print(f"[CLAUDE VISION] SUKCES! Przesyłam do telefonu: {result_json.get('cards', [])}")
        return jsonify(result_json)

    except Exception as e:
        print(f"[CLAUDE VISION] Wystąpił błąd podczas analizy lub parsowania: {str(e)}")
        return jsonify({"error": "Problem z przetworzeniem wyników przez serwer"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

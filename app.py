import os
import json
import base64
import re
from flask import Flask, request, jsonify
import anthropic

# Bezpieczne pobieranie klucza z pamięci chmury Render (zmienna środowiskowa)
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

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

    # STABILNY POLSKI PROMPT - WYMUSZA FORMAT: FIGURA+KOLOR
    prompt = """
    Jesteś profesjonalnym systemem brydżowym AI. Twoim zadaniem jest wykryć i wypisać wszystkie karty brydżowe widoczne na zdjęciu.
    
    Zwróć wynik BEZWZGLĘDNIE i WYŁĄCZNIE jako czysty, surowy format JSON (obiekt zawierający klucz "cards"):
    {"cards": ["KARTA1", "KARTA2", ...]}
    
    ZASADY BEZPIECZEŃSTWA:
    1. Każda karta w pliku JSON musi zawierać wartość oraz litere koloru wyłącznie w formacie międzynarodowym: S (Pik), H (Kier), D (Karo), C (Trefl). Przykład: "AS" (As Pik), "KD" (Król Karo), "6H" (Szóstka Kier), "2C" (Dwójka Trefl). Bezwzględnie nie używaj litery K dla koloru Karo!
    2. W tradycyjnej talii brydżowej KAŻDA KARTA JEST UNIKALNA. Niedozwolone jest, aby w wyniku pojawiła się ta sama karta dwa razy.
    3. Zwróć szczególną uwagę na karty 6 i 9. Sprawdź orientację indeksu na podstawie ułożenia pozostałych kart, aby upewnić się, czy to 6, czy 9.
    4. Przed zwróceniem wyniku zrób wewnętrzny test: policz wszystkie wykryte karty. Na ręce brydżysty powinno być dokładnie 13 kart. Jeśli wykryłeś więcej kart, usuń nadmiarowe omamy optyczne, aby dopasować wynik do 13 kart realnie leżących na stole.
    5. Nie dopisuj żadnych komentarzy, wyjaśnień ani formatowania markdown (```json). Zwróć czysty tekst obiektu JSON.
    """

    try:
        print("[CLAUDE VISION] Wysyłam zapytanie do precyzyjnego modelu Claude Sonnet 5...")
        
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

        # Bezpieczne filtrowanie bloków myślowych Sonnet 5 (ochrona przed błędem ThinkingBlock)
        text_segments = []
        for block in response.content:
            if block.type == "text" and hasattr(block, "text"):
                text_segments.append(block.text)
        
        response_text = "".join(text_segments).strip()
        print(f"[CLAUDE VISION] Surowa odpowiedź od AI: {response_text}")

        # Izolacja czystego formatu JSON z klamer { }
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
            print(f"[CLAUDE VISION] Oczyszczono tekst do formatu JSON: {response_text}")
        else:
            raise ValueError("Serwer AI nie zwrócił poprawnej struktury JSON.")

        result_json = json.loads(response_text)
        print(f"\n[CLAUDE VISION] SUKCES! Przesyłam do telefonu: {result_json.get('cards', [])}")
        return jsonify(result_json)

    except Exception as e:
        print(f"[CLAUDE VISION] Wystąpił błąd podczas analizy lub parsowania: {str(e)}")
        return jsonify({"error": "Problem z przetworzeniem wyników przez serwer"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

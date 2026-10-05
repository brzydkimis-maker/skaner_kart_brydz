import os
import json
import base64
import re
from flask import Flask, request, jsonify
import anthropic

# Bezpieczne pobieranie klucza z pamięci chmury Render (bez ujawniania go światu!)
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

    prompt = """
    Jesteś profesjonalnym systemem brydżowym AI. Twoim zadaniem jest wykryć i wypisać wszystkie karty brydżowe widoczne na zdjęciu.
    
    Zwróć wynik BEZWZGLĘDNIE i WYŁĄCZNIE jako czysty, surowy format JSON (obiekt zawierający klucz "cards"):
    {"cards": ["KARTA1", "KARTA2", ...]}
    
    ZASADY BEZPIECZEŃSTWA:
    1. Jeśli na zdjęciu jest mniej lub więcej niż 13 kart (np. tylko 1 karta), po prostu wypisz ją w liście, np. {"cards": ["AP"]}.
    2. NIE DOPISUJ żadnych komentarzy, wyjaśnień, ostrzeżeń ani zdań w stylu "Na zdjęciu widoczna jest...".
    3. Nie używaj formatowania markdown (```json). Zwróć wyłącznie nawiasy klamrowe i dane.
    
    Oznaczenia kolorów: P (Pik), C (Czerwień/Kier), K (Karo), T (Trefl)
    Oznaczenia figur: A (As), K (Król), Q (Dama), J (Walet), 10, 9, 8, 7, 6, 5, 4, 3, 2

    RYGORYSTYCZNE ZASADY WERYFIKACJI (6 VS 9):
    1. Zwróć szczególną uwagę na karty "6" i "9". Ze względu na obrót i perspektywę łatwo je pomylić lub uznać jedną fizyczną kartę za dwie osobne (szóstkę i dziewiątkę równocześnie).
    2. Przed zwróceniem wyniku zrób wewnętrzny test: policz wszystkie wykryte karty. W brydżu na ręce gracza może być dokładnie 13 kart.
    3. Jeżeli w Twojej wstępnej analizie liczba kart wynosi 14 lub więcej, oznacza to, że popełniłeś błąd i błędnie zinterpretowałeś obróconą szóstkę jako dziewiątkę (lub odwrotnie). 
    4. W takiej sytuacji bezwzględnie usuń nadmiarową kartę (6 lub 9), upewniając się, że ostateczny wynik zawiera dokładnie te 13 kart, które realnie leżą na stole.

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

        # BEZBŁĘDNE WYCIĄGANIE TEKSTU Z MODELU SONNET 5 (Z OMINIĘCIEM BLOKÓW THINKING):
        text_segments = []
        for block in response.content:
            # Filtrujemy bloki i wyciągamy tekst wyłącznie z elementów o typie 'text'
            if block.type == "text" and hasattr(block, "text"):
                text_segments.append(block.text)
        
        response_text = "".join(text_segments).strip()
        print(f"[CLAUDE VISION] Surowa odpowiedź od AI: {response_text}")

        # OBRONA PRZED KOMENTARZAMI LUDZKIMI: Izolujemy wyłącznie zawartość klamer { }
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
            print(f"[CLAUDE VISION] Oczyszczono tekst do formatu JSON: {response_text}")
        else:
            raise ValueError("Serwer AI nie zwrócił poprawnej struktury JSON.")

        # Parsowanie końcowe i bezpieczna wysyłka wyniku do telefonu
        result_json = json.loads(response_text)
        print(f"[CLAUDE VISION] SUKCES! Przesyłam do telefonu: {result_json.get('cards', [])}")
        return jsonify(result_json)

    except Exception as e:
        print(f"[CLAUDE VISION] Wystąpił błąd podczas analizy lub parsowania: {str(e)}")
        return jsonify({"error": "Problem z przetworzeniem wyników przez serwer"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

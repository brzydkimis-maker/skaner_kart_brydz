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

    # PRZYWRÓCONY: Pełny, dokładny prompt brydżowy z weryfikacją matematyczną 6 vs 9
prompt = """
    You are a professional Bridge AI vision system. Your task is to detect and list all bridge cards visible in the photo.
    
    CRITICAL OUTPUT RULE:
    Return the result STRICTLY and EXCLUSIVELY as a raw JSON object (containing only the "cards" key):
    {"cards": ["CARD1", "CARD2", ...]}
    
    Strictly NO markdown blocks (```json), NO explanations, NO comments, NO prose. Output only pure JSON.
    
    SAFETY & LOGIC RULES:
    1. Every card in a bridge hand is UNIQUE. No duplicate card codes are allowed in the output.
    2. Pay extreme attention to "6" and "9" ranks. They often look identical when inverted. Verify their orientation based on the layout of neighboring cards.
    3. Perform a strict internal count before outputting: A valid bridge hand has EXACTLY 13 cards.
    4. If your initial count detects 14 or more cards, it means you misidentified an inverted 6 as a 9 (or vice versa). In this case, you MUST re-evaluate, fix the 6/9 flip, and remove the ghost card to match exactly 13 real cards.
    
    SUIT & RANK CODES (STRICT):
    Suits MUST be international letters:
    S - Spades (Pik)
    H - Hearts (Kier)
    D - Diamonds (Karo) -> Use ONLY 'D' for Diamonds to avoid conflict with the King (K)!
    C - Clubs (Trefl)
    
    Format: [Rank][Suit] (Examples: Ace of Spades is "AS", King of Diamonds is "KD", 6 of Hearts is "6H", Jack of Clubs is "JC" or "WC"). Both English and Polish rank letters (J/W, Q/D, K) are acceptable.
    """

    try:
        print("[CLAUDE VISION] Wysyłam zapytanie do precyzyjnego modelu Claude Sonnet 5...")
        
        # PRZYWRÓCONO: Najlepszy i najbardziej inteligentny model inżynieryjny Sonnet 5
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
        print(f"[CLAUDE VISION] SUKCES! Przesyłam do telefonu: {result_json.get('cards', [])}")
        return jsonify(result_json)

    except Exception as e:
        print(f"[CLAUDE VISION] Wystąpił błąd podczas analizy lub parsowania: {str(e)}")
        return jsonify({"error": "Problem z przetworzeniem wyników przez serwer"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

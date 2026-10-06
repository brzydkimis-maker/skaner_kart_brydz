mport os
import json
import base64
import re
from flask import Flask, request, jsonify
import anthropic

# Bezpieczne pobieranie klucza z pamięci chmury Render
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

    # Odchudzona, błyskawiczna instrukcja dla modelu Haiku 4.5
    prompt = """
    Identify all bridge cards in the photo. 
    Return ONLY clean JSON object: {"cards": ["RANK+SUIT", ...]}. No markdown, no prose.
    Suits: P, C, K, T. Ranks: A, K, Q, J, 10-2. Max 13 cards. Fix 6/9 flips orientationally.
    """

    try:
        print("[CLAUDE VISION] Wysyłam zapytanie do superszybkiego modelu Claude Haiku...")
        
        response = client.messages.create(
            model="claude-haiku-4.5",
            max_tokens=1000,
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

        # Filtrowanie bloków i bezpieczne wyciąganie tekstu (ochrona przed ThinkingBlock)
        text_segments = []
        for block in response.content:
            if block.type == "text" and hasattr(block, "text"):
                text_segments.append(block.text)
        
        response_text = "".join(text_segments).strip()
        print(f"[CLAUDE VISION] Surowa odpowiedź od AI: {response_text}")

        # Izolacja samego formatu JSON
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

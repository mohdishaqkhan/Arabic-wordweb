import os
import json
import requests
from flask import Flask, jsonify, request, render_template
# REMOVED: from dotenv import load_dotenv
from flask_cors import CORS

# REMOVED: load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

import gc

# Add this after your imports
@app.after_request
def after_request(response):
    gc.collect()  # Force garbage collection after each request
    return response

@app.route('/')
def serve_index():
    """Serves the index.html file."""
    # Assumes index.html is in a 'templates' folder
    return render_template('index.html')


@app.route('/api/data', methods=['POST'])
def get_data():
    """
    Handles POST requests to the /api/data endpoint.
    Retrieves data from the Gemini API using a strict JSON schema.
    """
    # 1. LOG: Confirm the API route was successfully hit.
    print("--- API ROUTE HIT: /api/data ---")

    # CRITICAL: Get the API Key directly from the environment (Railway handles this)
    gm_api_key = os.environ.get('GM_API_KEY')
    if not gm_api_key:
        print("ERROR: API key not found. Ensure 'GM_API_KEY' is set in Railway Variables.")
        # This error is now for logic only, not deployment crash
        return jsonify({"error": "API key not found in environment variables."}), 500

    # Input validation
    if not request.json:
        print("ERROR: Request body was not JSON.")
        return jsonify({"error": "Request body must be JSON."}), 400

    user_prompt = request.json.get('prompt')
    if not user_prompt:
        print("ERROR: Prompt missing from request.")
        return jsonify({"error": "Missing 'prompt' in request body."}), 400

    # 2. LOG: Print the prompt received from the frontend.
    print(f"PROMPT RECEIVED: {user_prompt}")

    # Use the reliable Gemini 2.5 Flash model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={gm_api_key}"

    # Define the JSON schema for the dictionary output (CRITICAL for frontend parsing)
    json_schema = {
        "type": "OBJECT",
        "properties": {
            "definition_arabic": {"type": "STRING"},
            "definition_english": {"type": "STRING"},
            "root_word_arabic": {"type": "STRING"},
            "root_word_english": {"type": "STRING"},
            "synonyms": {
                "type": "ARRAY",
                "items": {"type": "OBJECT", "properties": {"arabic": {"type": "STRING"}, "english": {"type": "STRING"}}}
            },
            "antonyms": {
                "type": "ARRAY",
                "items": {"type": "OBJECT", "properties": {"arabic": {"type": "STRING"}, "english": {"type": "STRING"}}}
            },
            "example_sentences": {
                "type": "ARRAY",
                "items": {"type": "OBJECT", "properties": {"arabic": {"type": "STRING"}, "english": {"type": "STRING"}}}
            },
            "derivations": {
                "type": "ARRAY",
                "items": {"type": "OBJECT", "properties": {"arabic": {"type": "STRING"}, "english": {"type": "STRING"}}}
            },
            "cultural_notes": {"type": "STRING"}
        }
    }

    # System instruction to guide the model's behavior
    system_instruction = (
        "You are an expert Arabic linguist and lexicographer. "
        "Provide a comprehensive, structured dictionary entry for the user's word. "
        "Your response MUST be a single JSON object strictly following the provided schema. "
        "Do not include any text outside of the JSON object."
    )

    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": json_schema,
            "maxOutputTokens": 1000  # Limit response size
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        gemini_response_data = response.json()

        if 'candidates' in gemini_response_data and len(gemini_response_data['candidates']) > 0:
            generated_content = gemini_response_data['candidates'][0]['content']['parts'][0]['text']

            # 3. LOG: Print the raw JSON output from the Gemini API.
            print(f"GEMINI RAW JSON RESPONSE (Start): {generated_content[:500]}...")

            # Parse the generated JSON string
            parsed_data = json.loads(generated_content)
            return jsonify(parsed_data)
        else:
            print(f"ERROR: Gemini API returned no candidates or an error: {gemini_response_data}")
            return jsonify({"error": "Gemini API did not return content. Check the key and try a simpler word."}), 500

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request to Gemini API failed: {e}")
        return jsonify({"error": "Failed to connect to the Gemini API due to a network or rate limit error."}), 500
    except (KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: Error parsing Gemini response JSON: {e}")
        return jsonify({"error": "The Gemini API returned malformed JSON. Retrying may fix the issue."}), 500


if __name__ == '__main__':
    # Use the PORT environment variable provided by Railway, defaulting to 5000
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
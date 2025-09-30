import os
import json
import requests
from flask import Flask, jsonify, request, render_template # Added render_template
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes for development.
CORS(app)


# The new route to serve the index.html file.
# When a user visits the main URL (e.g., http://127.0.0.1:5000/),
# this function will be executed.
@app.route('/')
def serve_index():
    """Serves the index.html file."""
    # This renders the index.html file located in the 'templates' folder.
    return render_template('index.html')


@app.route('/api/data', methods=['POST'])
def get_data():
    """
    Handles POST requests to the /api/data endpoint.
    It takes a prompt from the frontend, sends it to the Gemini API,
    and returns a JSON response.
    """
    gm_api_key = os.environ.get('GM_API_KEY')
    if not gm_api_key:
        return jsonify({"error": "API key not found in environment variables."}), 500

    if not request.json:
        return jsonify({"error": "Request body must be JSON."}), 400

    user_prompt = request.json.get('prompt')
    if not user_prompt:
        return jsonify({"error": "No 'prompt' field in the request body."}), 400

    # The URL for the Gemini API
    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gm_api_key}'

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": user_prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    try:
        # Make the request to the Gemini API
        response = requests.post(url, json=payload)
        response.raise_for_status()  # This will raise an HTTPError for bad responses (4xx or 5xx)

        gemini_response_data = response.json()

        if 'candidates' in gemini_response_data and len(gemini_response_data['candidates']) > 0:
            generated_content = gemini_response_data['candidates'][0]['content']['parts'][0]['text']
            # The API returns a string that is a JSON object, so we need to parse it.
            parsed_data = json.loads(generated_content)
            return jsonify(parsed_data)
        else:
            return jsonify({"error": "Gemini API did not return a valid response."}), 500

    except requests.exceptions.RequestException as e:
        # Catches network-related errors during the request
        print(f"Request to Gemini API failed: {e}")
        return jsonify({"error": "Failed to connect to the Gemini API."}), 500
    except (KeyError, json.JSONDecodeError) as e:
        # Catches errors if the JSON response is malformed or keys are missing
        print(f"Error parsing Gemini response: {e}")
        return jsonify({"error": "Invalid or malformed JSON response from Gemini API."}), 500


if __name__ == '__main__':
    # Get the port from an environment variable, defaulting to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
import os
import json
import requests
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

import gc
import sys
import datetime



def render_log(message):
    """The least-bad option for Render"""
    timestamp = datetime.datetime.now().isoformat()
    full_message = f"[{timestamp}] {message}"

    # Try everything
    print(full_message, flush=True)
    sys.stdout.write(full_message + "\n")
    sys.stdout.flush()
    sys.stderr.write(full_message + "\n")
    sys.stderr.flush()


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


@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "Server is running"})


@app.route('/api/data', methods=['POST'])
def get_data():
    """
    Handles POST requests to the /api/data endpoint.
    Retrieves data from the Gemini API using a strict JSON schema.
    """
    # 1. LOG: Confirm the API route was successfully hit.
    print("--- API ROUTE HIT: /api/data ---", flush=True)
    # Log request details
    print(f"📨 BACKEND: Request method: {request.method}", flush=True)
    print(f"📨 BACKEND: Request headers: {dict(request.headers)}", flush=True)
    print(f"📨 BACKEND: Request content type: {request.content_type}", flush=True)
    print(f"📨 BACKEND: Request data: {request.data}", flush=True)
    print(f"📨 BACKEND: Request JSON: {request.json}", flush=True)

    # If it's a GET request (for testing), return simple response
    if request.method == 'GET':
        return jsonify({"message": "API is working!", "status": "success"})

    # CRITICAL: Get the API Key directly from the environment (Railway handles this)
    gm_api_key = os.environ.get('GM_API_KEY')
    print(f"🔑 BACKEND: API Key present: {bool(gm_api_key)}", flush=True)
    if not gm_api_key:
        print("ERROR: API key not found. Ensure 'GM_API_KEY' is set in Railway Variables.")
        # This error is now for logic only, not deployment crash
        return jsonify({"error": "API key not found in environment variables."}), 500

    # Input validation
    if not request.json:
        print("ERROR: Request body was not JSON.", flush=True)
        return jsonify({"error": "Request body must be JSON."}), 400

    user_prompt = request.json.get('prompt')
    if not user_prompt:
        print("ERROR: Prompt missing from request.", flush=True)
        return jsonify({"error": "Missing 'prompt' in request body."}), 400

    # Use the reliable Gemini 2.5 Flash model
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key="
           f"{gm_api_key}")
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
        print("🌐 BACKEND: Sending request to Gemini API...", flush=True)
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        print(f"✅ BACKEND: Gemini API response status: {response.status_code}", flush=True)

        gemini_response_data = response.json()
        print("📄 BACKEND: Got response from Gemini API", flush=True)

        if 'candidates' in gemini_response_data and len(gemini_response_data['candidates']) > 0:
            generated_content = gemini_response_data['candidates'][0]['content']['parts'][0]['text']

            # 3. LOG: Print the raw JSON output from the Gemini API.
            print(f"GEMINI RAW JSON RESPONSE (Start): {generated_content[:500]}...", flush=True)

            # Parse the generated JSON string
            parsed_data = json.loads(generated_content)
            print("🔄 BACKEND: Successfully parsed JSON, sending response to frontend")
            return jsonify(parsed_data)
        else:
            print(f"ERROR: Gemini API returned no candidates or an error: {gemini_response_data}", flush=True)
            return jsonify({"error": "Gemini API did not return content. Check the key and try a simpler word."}), 500

    except requests.exceptions.RequestException as e:

        print(f"ERROR: Request to Gemini API failed: {e}", flush=True)
        return jsonify({"error": "Failed to connect to the Gemini API due to a network or rate limit error."}), 500
    except (KeyError, json.JSONDecodeError) as e:

        print(f"ERROR: Error parsing Gemini response JSON: {e}", flush=True)
        return jsonify({"error": "The Gemini API returned malformed JSON. Retrying may fix the issue."}), 500


debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

if __name__ == '__main__':
    # Use the PORT environment variable provided by Railway, defaulting to 5000
    port = int(os.environ.get('PORT', 10000))

    print(f"🚀 Starting Flask app on port {port}", flush=True)
    print(f"🔑 API Key present: {bool(os.environ.get('GM_API_KEY'))}", flush=True)
    app.run(host='0.0.0.0', port=port, debug=True)

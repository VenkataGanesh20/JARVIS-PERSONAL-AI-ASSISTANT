from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from datetime import datetime
import pyttsx3
import threading
import requests

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)


OLLAMA_API_BASE_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL_NAME = "llama2"
EXECUTOR_API_URL = "http://127.0.0.1:5000/run-command"  # OS control endpoint

def speak_in_background(text_to_speak):
    """Initializes pyttsx3 and speaks the given text in a background thread."""
    try:
        engine = pyttsx3.init()
        engine.say(text_to_speak)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"Error in pyttsx3: {e}")

def handle_os_command(command_payload):
    """Sends commands to the OS Executor API."""
    try:
        # command_payload can be a string (for simple commands) or a dict (for structured commands)
        if isinstance(command_payload, str):
            payload = {"command": command_payload}
        else: # Assume it's already a dictionary
            payload = command_payload

        res = requests.post(EXECUTOR_API_URL, json=payload, timeout=10) # Increased timeout
        res.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return res.json().get("message", f"Executed: {payload.get('command', command_payload)}")
    except requests.exceptions.ConnectionError:
        return "OS Executor API is offline. Please start it."
    except requests.exceptions.Timeout:
        return "OS Executor API timed out. It might be busy or unresponsive."
    except requests.exceptions.RequestException as e:
        return f"Error communicating with OS Executor API: {e}"
    except Exception as e:
        return f"Unexpected error handling OS command: {e}"

def extract_target(message, keywords):
    """
    Extracts a target (like app name or website name) from a user message
    following a set of keywords.
    """
    for keyword in keywords:
        if keyword in message:
            start_index = message.find(keyword) + len(keyword)
            target = message[start_index:].strip()
            # Clean up common trailing words that indicate type
            target = target.replace(" app", "").replace(" application", "").replace(" website", "").strip()
            return target
    return None

@app.route('/chat', methods=['POST'])
def chat():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.json
    user_message = data.get("message", "").lower().strip()

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    ai_text_reply = ""

    try:
        # --- Time Query ---
        if any(phrase in user_message for phrase in ["what's the time", "current time", "show time", "tell me the time", "time now"]):
            current_time = datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")
            ai_text_reply = f"The current time is {current_time}."
        # --- Screenshot ---
        elif "screenshot" in user_message or "capture screen" in user_message or "take a picture" in user_message:
            ai_text_reply = handle_os_command("screenshot")
        # --- Volume Control ---
        elif ("mute" in user_message or "silence" in user_message) and ("volume" in user_message or "sound" in user_message):
            ai_text_reply = handle_os_command("mute")
        elif ("unmute" in user_message or "restore" in user_message) and ("volume" in user_message or "sound" in user_message):
            ai_text_reply = handle_os_command("unmute")
        # --- System Power ---
        elif "shutdown" in user_message or "shut down computer" in user_message or "power off" in user_message:
            ai_text_reply = handle_os_command("shutdown")
        elif "restart" in user_message or "reboot computer" in user_message:
            ai_text_reply = handle_os_command("restart")
        # --- Play Music on YouTube ---
        elif ("play music" in user_message or "play song" in user_message) and "youtube" in user_message:
            song_query = extract_target(user_message, ["play music ", "play song ", "on youtube "])
            if song_query and song_query != "youtube": # Ensure we extracted a specific song name, not just 'youtube'
                ai_text_reply = handle_os_command({"command": "open youtube", "query": song_query})
            else:
                ai_text_reply = handle_os_command("open youtube")
                ai_text_reply += " What music would you like me to search for?"
        # --- Open/Launch Commands ---
        elif any(kw in user_message for kw in ["open ", "launch ", "run ", "start "]):
            target = extract_target(user_message, ["open ", "launch ", "run ", "start "])
            if target:
                ai_text_reply = handle_os_command(f"open {target}") # Pass "open target" to app.py
            else:
                ai_text_reply = "Please specify what you want me to open."
        # --- Close App/Tab (Placeholder for now) ---
        elif "close app" in user_message or "close application" in user_message:
            ai_text_reply = "I'm sorry, I cannot directly close specific applications yet. This feature is still under development."
        elif "close tab" in user_message or "close current tab" in user_message:
            ai_text_reply = "I cannot directly close browser tabs yet. You might need to do that manually for now."
        elif "open tab" in user_message or "new tab" in user_message:
             ai_text_reply = "I cannot directly open new browser tabs, but I can open browsers or websites for you."
        # --- Fallback to Ollama if no specific command is recognized ---
        else:
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": OLLAMA_MODEL_NAME,
                "prompt": user_message,
                "stream": False
            }
            response = requests.post(OLLAMA_API_BASE_URL, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            ai_text_reply = response_data.get("response", "No response from Ollama.")

        if ai_text_reply:
            threading.Thread(target=speak_in_background, args=(ai_text_reply,), daemon=True).start()

        return jsonify({"reply": ai_text_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    # This serves the jarvis_frontend.html file from frontend folder
    return send_from_directory("templates", "jarvis_frontend.html")

if __name__ == "__main__":
    app.run(debug=True, port=5100)
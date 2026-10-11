import os
import subprocess
import datetime
import webbrowser
import pyautogui # For screenshot, potentially for window/tab control
from plyer import notification # For notifications
from flask import Flask, request, jsonify

app = Flask(__name__)

# Predefined app paths (change for your system if needed)
APP_PATHS = {
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe", # Default Chrome path
    # Add more apps here as needed, e.g., "word": "winword.exe"
}

# Predefined websites
WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "linkedin": "https://www.linkedin.com",
    # Add more websites here
}

def show_notification(title, message):
    """Show a pop-up notification."""
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=3
        )
    except Exception as e:
        print(f"Error showing notification: {e}") # Fallback print if plyer fails

@app.route('/run-command', methods=['POST'])
def run_command():
    # Expects a JSON payload like {"command": "open chrome"} or {"command": "open youtube", "query": "jazz music"}
    data = request.json
    command = data.get("command", "").lower().strip()
    query = data.get("query", "") # For commands like "open youtube" with a search query

    try:
        # --- Time ---
        if "time" in command:
            now = datetime.datetime.now().strftime("%I:%M %p")
            show_notification("Current Time", now)
            return jsonify({"status": "success", "message": f"The current time is {now}."})

        # --- Screenshot ---
        if "screenshot" in command:
            filename = "screenshot.png"
            pyautogui.screenshot().save(filename)
            show_notification("Screenshot Taken", f"Saved as {filename}")
            return jsonify({"status": "success", "message": f"Screenshot saved as {filename}."})

        # --- Volume control (Requires nircmd.exe in your PATH or specified path) ---
        if "mute" in command:
            os.system("nircmd.exe mutesysvolume 1") # Make sure nircmd.exe is accessible
            show_notification("Volume", "Muted")
            return jsonify({"status": "success", "message": "Volume muted."})
        if "unmute" in command:
            os.system("nircmd.exe mutesysvolume 0") # Make sure nircmd.exe is accessible
            show_notification("Volume", "Unmuted")
            return jsonify({"status": "success", "message": "Volume unmuted."})

        # --- Shutdown / Restart ---
        if "shutdown" in command:
            os.system("shutdown /s /t 1")
            return jsonify({"status": "success", "message": "Shutting down..."})
        if "restart" in command:
            os.system("shutdown /r /t 1")
            return jsonify({"status": "success", "message": "Restarting..."})

        # --- Open Websites/Applications (More flexible parsing) ---
        if command.startswith("open "):
            target = command[len("open "):].strip()

            # Handle YouTube with a specific search query
            if target == "youtube" and query:
                search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                webbrowser.open(search_url)
                show_notification("Youtube", f"Searching for {query}")
                return jsonify({"status": "success", "message": f"Searching YouTube for {query}."})

            # Check if target is a predefined website
            for site_key, url in WEBSITES.items():
                if site_key in target: # Allow for "open google", "open youtube"
                    chrome_path = APP_PATHS.get("chrome")
                    if os.path.exists(chrome_path):
                        subprocess.Popen([chrome_path, url])
                        show_notification("Website Opened", f"{site_key.capitalize()} in Chrome")
                    else:
                        webbrowser.open(url) # Fallback to default browser
                        show_notification("Website Opened", f"{site_key.capitalize()} in Default Browser")
                    return jsonify({"status": "success", "message": f"Opening {site_key.capitalize()}."})

            # Check if target is a predefined application
            for app_name, path in APP_PATHS.items():
                if app_name in target: # Allow for "open notepad", "launch calculator"
                    try:
                        subprocess.Popen(path)
                        show_notification("Application Opened", app_name.capitalize())
                        return jsonify({"status": "success", "message": f"{app_name.capitalize()} opened."})
                    except FileNotFoundError:
                        return jsonify({"status": "error", "message": f"Application '{app_name}' not found at '{path}'."})
                    except Exception as e:
                        return jsonify({"status": "error", "message": f"Error opening '{app_name}': {str(e)}"})

            # If "open" command but target not found
            return jsonify({"status": "error", "message": f"Sorry, I don't know how to open '{target}'. Please specify a known app or website."})

        # --- Generic run command (for direct system commands) ---
        if command.startswith("run "):
            actual_command = command[len("run "):].strip()
            try:
                subprocess.Popen(actual_command, shell=True) # Use shell=True for simple commands like "calc", "notepad"
                show_notification("Command Executed", actual_command)
                return jsonify({"status": "success", "message": f"Ran command: {actual_command}"})
            except FileNotFoundError:
                return jsonify({"status": "error", "message": f"Command not found: {actual_command}"})
            except Exception as e:
                return jsonify({"status": "error", "message": f"Error executing command '{actual_command}': {str(e)}"})

        return jsonify({"status": "error", "message": f"Unknown command: {command}"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
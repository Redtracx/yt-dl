import os
import sys
import threading
import webview
import json
import subprocess
import re
from pathlib import Path


class YoutubeDLApi:
    def __init__(self):
        self.download_thread = None
        self.download_path = str(Path.home() / "Downloads" / "YT-Videos")
        # Sicherstellen, dass der Download-Ordner existiert
        os.makedirs(self.download_path, exist_ok=True)

    def download_video(self, youtube_url, quality="best"):
        """
        Startet den Download eines YouTube-Videos im Hintergrund
        """
        if not youtube_url or not youtube_url.strip():
            return {"status": "error", "message": "Bitte geben Sie eine URL ein"}

        if not self._is_valid_youtube_url(youtube_url):
            return {"status": "error", "message": "Ungültige YouTube-URL"}

        # Wenn bereits ein Download läuft
        if self.download_thread and self.download_thread.is_alive():
            return {"status": "error", "message": "Es läuft bereits ein Download"}

        # Download im Hintergrund starten
        self.download_thread = threading.Thread(
            target=self._execute_download,
            args=(youtube_url, quality)
        )
        self.download_thread.daemon = True
        self.download_thread.start()

        return {"status": "success", "message": "Download gestartet"}

    def _is_valid_youtube_url(self, url):
        """Überprüft, ob es sich um eine gültige YouTube-URL handelt"""
        youtube_regex = (
            r'(https?://)?(www\.)?'
            r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        match = re.match(youtube_regex, url)
        return match is not None

    def _execute_download(self, youtube_url, quality):
        """Führt den tatsächlichen Download mit yt-dlp aus"""
        try:
            # Format je nach Qualitätseinstellung wählen
            format_opt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" if quality == "best" else "worst[ext=mp4]/worst"

            # yt-dlp Kommando vorbereiten
            cmd = [
                "yt-dlp",
                youtube_url,
                "--format", format_opt,
                "--output", os.path.join(self.download_path, "%(title)s.%(ext)s"),
                "--progress-template", "%(progress._percent_str)s %(progress._speed_str)s"
            ]

            # Prozess starten und Ausgabe erfassen
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Status in Echtzeit aktualisieren
            for line in process.stdout:
                self.log_status(line.strip())

            # Prozess beenden
            process.wait()

            if process.returncode == 0:
                self.log_status("Download abgeschlossen")
            else:
                self.log_status(f"Fehler beim Download, Exit-Code: {process.returncode}")

        except Exception as e:
            self.log_status(f"Fehler: {str(e)}")

    def log_status(self, message):
        """Sendet Statusnachrichten an das Webview-Fenster"""
        if webview.windows:
            webview.windows[0].evaluate_js(
                f"updateStatus('{message.replace('\'', '\\\'')}')"
            )

    def open_download_folder(self):
        """Öffnet den Download-Ordner im Dateiexplorer"""
        if sys.platform == 'win32':
            os.startfile(self.download_path)
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', self.download_path])
        else:  # Linux
            subprocess.call(['xdg-open', self.download_path])

        return {"status": "success", "message": "Download-Ordner geöffnet"}


# HTML für die Benutzeroberfläche
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>YouTube Video Downloader</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #c00;
            text-align: center;
        }
        .container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"] {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        select {
            width: 100%;
            padding: 8px;
            box-sizing: border-box;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            background-color: #c00;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #a00;
        }
        #downloadBtn {
            margin-right: 10px;
        }
        #status {
            margin-top: 20px;
            padding: 10px;
            border-radius: 4px;
            background-color: #f0f0f0;
            min-height: 100px;
            max-height: 200px;
            overflow-y: auto;
        }
        .status-line {
            margin: 5px 0;
            font-family: monospace;
        }
        .buttons {
            display: flex;
            gap: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>YouTube Video Downloader</h1>

        <div class="form-group">
            <label for="youtube_url">YouTube URL:</label>
            <input type="text" id="youtube_url" placeholder="https://www.youtube.com/watch?v=...">
        </div>

        <div class="form-group">
            <label for="quality">Qualität:</label>
            <select id="quality">
                <option value="best">Beste Qualität</option>
                <option value="worst">Niedrige Qualität (schneller)</option>
            </select>
        </div>

        <div class="buttons">
            <button id="downloadBtn">Download starten</button>
            <button id="openFolderBtn">Download-Ordner öffnen</button>
        </div>

        <div id="status">
            <div class="status-line">Bereit zum Download...</div>
        </div>
    </div>

    <script>
        // Status-Anzeige aktualisieren
        function updateStatus(message) {
            const statusDiv = document.getElementById('status');
            const newLine = document.createElement('div');
            newLine.className = 'status-line';
            newLine.textContent = message;
            statusDiv.appendChild(newLine);
            statusDiv.scrollTop = statusDiv.scrollHeight;
        }

        // Warten bis das Fenster geladen ist
        window.addEventListener('pywebviewready', () => {
            // Download-Button-Handler
            const downloadBtn = document.getElementById('downloadBtn');
            downloadBtn.addEventListener('click', () => {
                const url = document.getElementById('youtube_url').value;
                const quality = document.getElementById('quality').value;

                if (!url) {
                    updateStatus('Bitte geben Sie eine YouTube-URL ein');
                    return;
                }

                updateStatus('Starte Download...');

                // API-Aufruf
                pywebview.api.download_video(url, quality)
                    .then(response => {
                        if (response.status === 'error') {
                            updateStatus(`Fehler: ${response.message}`);
                        }
                    })
                    .catch(error => {
                        updateStatus(`Ein Fehler ist aufgetreten: ${error}`);
                    });
            });

            // Ordner-Öffnen-Button
            const openFolderBtn = document.getElementById('openFolderBtn');
            openFolderBtn.addEventListener('click', () => {
                pywebview.api.open_download_folder();
            });
        });
    </script>
</body>
</html>
"""


def main():
    api_instance = YoutubeDLApi()
    window = webview.create_window('YouTube Video Downloader', html=html_content, js_api=api_instance)
    webview.start(debug=True)


if __name__ == '__main__':
    main()

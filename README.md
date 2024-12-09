# Funlight Converter

Ein moderner YouTube-Downloader und Converter mit einer schönen Dark Mode Benutzeroberfläche.

## Features

- Download von YouTube-Videos
- Konvertierung in verschiedene Formate (MP3, WAV, MP4, MOV)
- Elegantes Dark Mode Interface
- Fortschrittsanzeige
- Einfache Auswahl des Ausgabeordners
- Fehlerbehandlung und Benutzerbenachrichtigungen

## Installation

1. Stellen Sie sicher, dass Python 3.9 oder höher installiert ist
2. Installieren Sie die erforderlichen Pakete:
   ```
   pip install -r requirements.txt
   ```
3. Starten Sie die Anwendung:
   ```
   python funlight_converter.py
   ```

## Verwendung

1. Fügen Sie die YouTube-URL ein
2. Wählen Sie das gewünschte Ausgabeformat
3. Wählen Sie den Zielordner
4. Klicken Sie auf "Download"

## Anforderungen

- Python 3.9+
- PyQt6
- yt-dlp
- pydub
- FFmpeg (muss separat installiert werden)

## FFmpeg Installation

### Windows
1. Laden Sie FFmpeg von [ffmpeg.org](https://ffmpeg.org/download.html) herunter
2. Extrahieren Sie die Dateien
3. Fügen Sie den Pfad zu den FFmpeg-Binärdateien zur System-PATH-Variable hinzu

## Hinweise

- Stellen Sie sicher, dass Sie eine stabile Internetverbindung haben
- Die Downloadgeschwindigkeit hängt von Ihrer Internetverbindung ab
- Einige Formate benötigen möglicherweise mehr Zeit zur Konvertierung

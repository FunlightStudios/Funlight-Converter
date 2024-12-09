import os
import sys
import yt_dlp
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QComboBox, QProgressBar, QFileDialog, QMessageBox,
                           QSpinBox, QCheckBox, QGroupBox, QSlider)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QDragEnterEvent, QDropEvent

# Suppress deprecation warnings
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

class DownloadThread(QThread):
    progress = pyqtSignal(float)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, url, output_path, format_option, quality, start_time=None, end_time=None):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.format_option = format_option
        self.quality = quality
        self.start_time = start_time
        self.end_time = end_time

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    progress = (downloaded / total) * 100
                    self.progress.emit(int(progress))
                    self.status.emit(f'Downloading: {progress:.1f}%')
            except Exception as e:
                self.status.emit('Downloading...')
        elif d['status'] == 'finished':
            self.status.emit('Download finished, starting conversion...')
            self.progress.emit(0)  # Reset progress for conversion phase
        elif d['status'] == 'error':
            self.error.emit(f"Error during download: {d.get('error', 'Unknown error')}")

    def postprocessor_hook(self, d):
        if d['status'] == 'started':
            self.status.emit(f'Converting: {d.get("postprocessor", "unknown")}')
        elif d['status'] == 'finished':
            self.status.emit('Conversion step completed')

    def run(self):
        try:
            # Check if ffmpeg is available
            try:
                import subprocess
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except:
                self.error.emit("FFmpeg is not found in system PATH. Please make sure FFmpeg is installed correctly.")
                return

            # Basic options for all formats
            ydl_opts = {
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'postprocessor_hooks': [self.postprocessor_hook],
                'quiet': False,  # Enable output for debugging
                'verbose': True,  # Enable verbose output
                'no_warnings': False,  # Show warnings
                'ignoreerrors': False,  # Don't ignore errors
                'no_color': True,
                'prefer_ffmpeg': True,
                'keepvideo': True,
            }

            # Format specific options
            if self.format_option == 'MP3':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': self.quality,
                    }],
                })
            elif self.format_option == 'WAV':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'wav',
                    }],
                })
            elif self.format_option == 'AAC':
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'aac',
                    }],
                })
            elif self.format_option == 'MP4':
                # For videos, first download best quality and then convert
                ext = self.format_option.lower()
                
                # Quality settings for video
                if self.quality:
                    height = int(self.quality.replace('p', ''))
                    format_str = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
                else:
                    format_str = 'bestvideo+bestaudio/best'

                ydl_opts.update({
                    'format': format_str,
                    'merge_output_format': ext,
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': ext,
                    }],
                    'postprocessor_args': [
                        '-c:v', 'copy',           # Kopieren des Video-Streams ohne Neukodierung
                        '-c:a', 'aac',            # Audio-Codec
                        '-b:a', '192k',           # Audio-Bitrate
                        '-ar', '48000',           # Audio Sample Rate
                        '-movflags', '+faststart',
                        '-threads', 'auto',
                        '-r', '30',               # Set frame rate to 30 fps
                    ]
                })

                # Ensure we keep the temporary files for debugging
                ydl_opts['keepvideo'] = True
                ydl_opts['keep_fragments'] = True

            # Try to find ffmpeg in common locations
            ffmpeg_paths = [
                r'C:\ffmpeg\bin',
                r'C:\Program Files\ffmpeg\bin',
                os.path.expanduser('~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-7.1-full_build\\bin'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'bin'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'Scripts')
            ]

            ffmpeg_found = False
            for path in ffmpeg_paths:
                if os.path.exists(os.path.join(path, 'ffmpeg.exe')):
                    ydl_opts['ffmpeg_location'] = path
                    ffmpeg_found = True
                    self.status.emit(f'Using FFmpeg from: {path}')
                    break

            if not ffmpeg_found:
                self.error.emit("FFmpeg not found. Please run setup_ffmpeg.py as administrator to install FFmpeg.")
                return

            self.status.emit('Starting download...')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # First, try to extract video information
                    self.status.emit('Retrieving video information...')
                    info = ydl.extract_info(self.url, download=False)
                    if info is None:
                        self.error.emit("Could not retrieve video information. Please check the URL.")
                        return
                    
                    # Calculate estimated file size
                    if 'filesize' in info:
                        size_mb = info['filesize'] / (1024 * 1024)
                        self.status.emit(f'Estimated file size: {size_mb:.1f} MB')
                    
                    # Then proceed with download
                    self.status.emit('Starting download and conversion...')
                    ydl.download([self.url])
                    
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    if "requested format not available" in error_msg.lower():
                        self.error.emit("The requested video quality is not available. Try a lower quality setting.")
                    elif "private video" in error_msg.lower():
                        self.error.emit("This video is private and cannot be downloaded.")
                    elif "copyright" in error_msg.lower():
                        self.error.emit("This video is not available due to copyright restrictions.")
                    else:
                        self.error.emit(f"Download error: {error_msg}")
                    return
                except Exception as e:
                    self.error.emit(f"An error occurred: {str(e)}")
                    return

            # Get the output file name
            output_file = os.path.join(self.output_path, f"{info['title']}.{ext}")

            # Clean up temporary files after conversion
            files_to_delete = [os.path.join(self.output_path, f) for f in os.listdir(self.output_path) if f.endswith('.tmp') or f.endswith('.part') or f.endswith('.frag')]
            for file in files_to_delete:
                self.status.emit(f'Attempting to delete: {file}')  # Debugging output
                if os.path.exists(file):
                    os.remove(file)
                    self.status.emit(f'Deleted temporary file: {file}')
                else:
                    self.status.emit(f'File not found for deletion: {file}')  # Additional debugging output

            # Set the modification time of the output file to the current time
            if os.path.exists(output_file):
                os.utime(output_file, None)  # Set to current time

            self.status.emit('Conversion completed successfully!')
            self.finished.emit()
            
        except Exception as e:
            error_msg = str(e)
            if "ffmpeg" in error_msg.lower():
                error_msg = "FFmpeg error. Please make sure FFmpeg is installed correctly and try again."
            elif "unavailable" in error_msg.lower():
                error_msg = "Video is unavailable. Please check if the video exists and is not private."
            self.error.emit(error_msg)

class FunlightConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setAcceptDrops(True)

    def initUI(self):
        self.setWindowTitle('Funlight Converter')
        self.setMinimumSize(900, 600)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLineEdit, QSpinBox {
                padding: 8px;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #ffffff;
                min-height: 20px;
            }
            QPushButton {
                padding: 8px 16px;
                background-color: #0078d4;
                border: none;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
            QComboBox {
                padding: 8px;
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #ffffff;
                min-height: 20px;
            }
            QProgressBar {
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 2px;
            }
            QGroupBox {
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3d3d3d;
                height: 8px;
                background: #2d2d2d;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                border: 1px solid #0078d4;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
        """)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title_layout = QHBoxLayout()
        title_label = QLabel('Funlight Converter')
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label)
        layout.addLayout(title_layout)

        # URL input with paste button
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('Enter YouTube URL here or drag & drop a video link...')
        paste_button = QPushButton('Paste')
        paste_button.clicked.connect(self.paste_url)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(paste_button)
        layout.addLayout(url_layout)

        # Format and Quality Settings
        settings_layout = QHBoxLayout()
        
        # Format selection
        format_group = QGroupBox('Output Format')
        format_layout = QVBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(['MP3', 'WAV', 'AAC', 'MP4'])
        self.format_combo.currentTextChanged.connect(self.update_quality_options)
        format_layout.addWidget(self.format_combo)
        format_group.setLayout(format_layout)
        settings_layout.addWidget(format_group)

        # Quality settings
        quality_group = QGroupBox('Quality Settings')
        quality_layout = QVBoxLayout()
        self.quality_combo = QComboBox()
        self.update_quality_options()
        quality_layout.addWidget(self.quality_combo)
        quality_group.setLayout(quality_layout)
        settings_layout.addWidget(quality_group)

        # Time range settings
        time_group = QGroupBox('Time Range (Optional)')
        time_layout = QVBoxLayout()
        time_range_layout = QHBoxLayout()
        
        self.start_time = QSpinBox()
        self.start_time.setRange(0, 86400)
        self.start_time.setSuffix(' sec')
        self.end_time = QSpinBox()
        self.end_time.setRange(0, 86400)
        self.end_time.setSuffix(' sec')
        
        time_range_layout.addWidget(QLabel('Start:'))
        time_range_layout.addWidget(self.start_time)
        time_range_layout.addWidget(QLabel('End:'))
        time_range_layout.addWidget(self.end_time)
        
        time_layout.addLayout(time_range_layout)
        time_group.setLayout(time_layout)
        settings_layout.addWidget(time_group)

        layout.addLayout(settings_layout)

        # Output directory selection
        dir_group = QGroupBox('Output Directory')
        dir_layout = QVBoxLayout()
        dir_input_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        dir_button = QPushButton('Browse')
        dir_button.clicked.connect(self.select_directory)
        dir_input_layout.addWidget(self.dir_input)
        dir_input_layout.addWidget(dir_button)
        dir_layout.addLayout(dir_input_layout)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        # Status and Progress
        status_group = QGroupBox('Status')
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel('Ready')
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Download button
        self.download_button = QPushButton('Start Download')
        self.download_button.setMinimumHeight(40)
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button)

        # Set default output directory
        default_output = os.path.join(os.path.expanduser('~'), 'Downloads', 'Funlight Converter')
        os.makedirs(default_output, exist_ok=True)
        self.dir_input.setText(default_output)

        self.download_thread = None

    def update_quality_options(self):
        self.quality_combo.clear()
        if self.format_combo.currentText() in ['MP3']:
            self.quality_combo.addItems(['64', '128', '192', '256', '320'])
            self.quality_combo.setCurrentText('192')
        elif self.format_combo.currentText() in ['MP4']:
            self.quality_combo.addItems(['144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '2160p'])
            self.quality_combo.setCurrentText('720p')

    def paste_url(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        url = event.mimeData().text()
        self.url_input.setText(url)

    def select_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.dir_input.setText(dir_path)

    def start_download(self):
        url = self.url_input.text().strip()
        output_path = self.dir_input.text()
        format_option = self.format_combo.currentText()
        
        # Convert quality string to number
        quality = self.quality_combo.currentText()
        if format_option in ['MP4']:
            quality = quality.replace('p', '')  # Remove 'p' from resolution
        
        start_time = self.start_time.value() if self.start_time.value() > 0 else None
        end_time = self.end_time.value() if self.end_time.value() > 0 else None

        if not url:
            QMessageBox.warning(self, 'Error', 'Please enter a YouTube URL')
            return
        if not output_path:
            QMessageBox.warning(self, 'Error', 'Please select an output directory')
            return

        self.download_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText('Initializing...')

        self.download_thread = DownloadThread(url, output_path, format_option, quality, start_time, end_time)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.status.connect(self.update_status)
        self.download_thread.start()

    def update_progress(self, percentage):
        self.progress_bar.setValue(int(percentage))

    def update_status(self, status):
        self.status_label.setText(status)

    def download_finished(self):
        self.download_button.setEnabled(True)
        self.status_label.setText('Download completed successfully!')
        self.progress_bar.setValue(100)
        QMessageBox.information(self, 'Success', 'Download completed successfully!')

    def download_error(self, error_message):
        self.download_button.setEnabled(True)
        self.status_label.setText('Error: ' + error_message)
        QMessageBox.critical(self, 'Error', f'Download failed: {error_message}')

def main():
    app = QApplication(sys.argv)
    converter = FunlightConverter()
    converter.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

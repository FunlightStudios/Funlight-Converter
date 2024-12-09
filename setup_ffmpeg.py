import os
import subprocess
import sys
import winreg
import ctypes

def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def add_to_path(new_path):
    # Get the current PATH
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_ALL_ACCESS) as key:
            path_value, _ = winreg.QueryValueEx(key, 'Path')
            
            # Check if path already exists
            paths = path_value.split(';')
            if new_path.lower() not in [p.lower() for p in paths]:
                # Add the new path
                new_path_value = path_value + ';' + new_path
                winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path_value)
                
                # Notify the system about the change
                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x1A
                SMTO_ABORTIFHUNG = 0x0002
                result = ctypes.c_long()
                SendMessageTimeoutW = ctypes.windll.user32.SendMessageTimeoutW
                SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment', SMTO_ABORTIFHUNG, 5000, ctypes.byref(result))
                return True
    except Exception as e:
        print(f"Error updating PATH: {e}")
    return False

def main():
    # Check if ffmpeg is already in PATH
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("FFmpeg is already installed and in PATH!")
        return
    except:
        print("FFmpeg not found in PATH. Setting up...")

    # Find FFmpeg installation
    possible_paths = [
        r'C:\Program Files\ffmpeg\bin',
        r'C:\ffmpeg\bin',
        os.path.expanduser('~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-7.1-full_build\\bin')
    ]

    ffmpeg_path = None
    for path in possible_paths:
        if os.path.exists(os.path.join(path, 'ffmpeg.exe')):
            ffmpeg_path = path
            break

    if not ffmpeg_path:
        print("FFmpeg installation not found. Installing via winget...")
        try:
            subprocess.run(['winget', 'install', 'Gyan.FFmpeg'], check=True)
            print("FFmpeg installed successfully!")
            
            # Try to find the new installation
            ffmpeg_path = os.path.expanduser('~\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-7.1-full_build\\bin')
        except Exception as e:
            print(f"Error installing FFmpeg: {e}")
            return

    # Add FFmpeg to PATH
    if add_to_path(ffmpeg_path):
        print(f"Added FFmpeg to PATH: {ffmpeg_path}")
        print("Please restart your application for the changes to take effect.")
    else:
        print("Failed to add FFmpeg to PATH. Please add it manually.")

if __name__ == '__main__':
    if not is_admin():
        print("This script requires administrative privileges.")
        if sys.platform == 'win32':
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    else:
        main()

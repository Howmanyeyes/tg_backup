import os
import shutil
import ctypes
from pathlib import Path

def add_to_user_path_windows(dir_to_add: str) -> bool:
    """
    Permanently add a directory to the current user's PATH environment variable in the registry on Windows.
    Broadcasts a message so new processes will see the change.
    """
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ)
        try:
            current_path, reg_type = winreg.QueryValueEx(key, "PATH")
        except FileNotFoundError:
            current_path = ""
            reg_type = winreg.REG_EXPAND_SZ
        winreg.CloseKey(key)
    except Exception as e:
        print("Error reading user PATH from registry:", e)
        return False

    # Check if the directory is already in PATH (case-insensitive)
    if current_path and any(p.strip().lower() == dir_to_add.lower() for p in current_path.split(os.pathsep)):
        print(f"{dir_to_add} is already in the user PATH.")
        return True

    new_path = current_path + os.pathsep + dir_to_add if current_path else dir_to_add

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "PATH", 0, reg_type, new_path)
        winreg.CloseKey(key)
        print(f"Successfully added {dir_to_add} to the user PATH (Windows).")
    except Exception as e:
        print("Error writing user PATH to registry:", e)
        return False

    # Broadcast the change
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    SMTO_ABORTIFHUNG = 0x0002
    result = ctypes.c_long()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 5000, ctypes.byref(result)
    )
    return True

def add_to_user_path_unix(dir_to_add: str) -> bool:
    """
    Permanently add a directory to the user's PATH by appending an export statement to the appropriate shell config file.
    This function attempts to determine the default shell and update its config file (e.g. ~/.bashrc or ~/.zshrc).
    """
    # Determine the shell from the SHELL environment variable.
    shell = os.environ.get("SHELL", "")
    config_file = None
    if "bash" in shell:
        config_file = Path.home() / ".bashrc"
    elif "zsh" in shell:
        config_file = Path.home() / ".zshrc"
    else:
        # Fallback: try .profile
        config_file = Path.home() / ".profile"

    export_line = f'\n# Added by add_7z_to_path script\nexport PATH="$PATH:{dir_to_add}"\n'
    # Check if the directory is already mentioned in the config file.
    if config_file.exists():
        content = config_file.read_text()
        if dir_to_add in content:
            print(f"{dir_to_add} already exists in {config_file}")
            return True
    else:
        # Create the file if it doesn't exist.
        config_file.touch()

    try:
        with config_file.open("a", encoding="utf-8") as f:
            f.write(export_line)
        print(f"Successfully added {dir_to_add} to {config_file}. Please restart your terminal or source the file to update PATH.")
        return True
    except Exception as e:
        print("Error updating shell configuration file:", e)
        return False

def check_and_add_7z():
    if shutil.which("7z"):
        print("7z is already in PATH.")
        return
    else:
        print("7z not found in PATH.")
        # Define candidate directories based on OS
        if os.name == "nt":
            # Windows: check common installation directory
            potential_dir = r"C:\Program Files\7-Zip"
            seven_zip_exe = os.path.join(potential_dir, "7z.exe")
            if os.path.exists(seven_zip_exe):
                print(f"Found 7z at {seven_zip_exe}. Adding {potential_dir} to PATH permanently...")
                added = add_to_user_path_windows(potential_dir)
                if added:
                    print("7z has been added to the PATH. Restart your terminal or log off/log on for changes to take effect.")
                else:
                    print("Failed to add 7z to PATH on Windows.")
            else:
                print("7z was not found in the default location on Windows. Please install 7-Zip.")
        else:
            # macOS / Linux: common locations might be /usr/local/bin or /opt/homebrew/bin (for macOS on Apple Silicon)
            candidate_dirs = ["/usr/local/bin", "/opt/homebrew/bin"]
            found = False
            for d in candidate_dirs:
                seven_zip_exe = os.path.join(d, "7z")
                if os.path.exists(seven_zip_exe):
                    print(f"Found 7z at {seven_zip_exe}. Adding {d} to PATH permanently...")
                    if add_to_user_path_unix(d):
                        print("7z has been added to the PATH. Restart your terminal or source your config file for changes to take effect.")
                        found = True
                        break
            if not found:
                print("7z was not found in the common directories on macOS/Linux. Please install 7-Zip (e.g. via Homebrew on macOS or your package manager on Linux).")

if __name__ == "__main__":
    check_and_add_7z()

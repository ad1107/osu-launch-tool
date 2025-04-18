import ctypes
import sys
import os
import subprocess
import time
# Windows-specific imports
import win32api
import win32con
import pywintypes

# --- Constants for commands ---
CMD_TASKKILL = "taskkill"
CMD_NET = "net"
CMD_TIMEOUT = "timeout"
ERROR_CANCELLED = 1223 # Error code when user cancels UAC prompt

# --- Admin Check and Elevation ---

def is_admin():
    """Checks if the script is running with administrator privileges on Windows."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        print("Warning: Could not determine admin status via ctypes.")
        return False # Assume not admin if check fails

def request_admin_elevation():
    """
    If not admin, attempts to relaunch itself with admin privileges using UAC.
    Returns True if already admin or elevation succeeded (new process started).
    Returns False if elevation was required but failed/cancelled.
    Original non-admin process exits if elevation is attempted.
    """
    if is_admin():
        print("Already running with administrator privileges.")
        return True
    else:
        print("Administrator privileges required. Attempting to elevate...")
        try:
            script = os.path.abspath(sys.argv[0])
            params = " ".join([script] + sys.argv[1:])
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)

            if ret > 32:
                print("Elevation successful, launching new process...")
                sys.exit(0) # Exit original non-admin process
            else:
                error_code = ctypes.get_last_error()
                if error_code == ERROR_CANCELLED:
                    print("Elevation cancelled by user.")
                else:
                    print(f"Elevation failed with error code: {error_code}")
                return False # Elevation failed or cancelled
        except Exception as e:
            print(f"An error occurred during elevation attempt: {e}")
            return False

# --- Driver Control Functions (using subprocess) ---

def run_command(command_parts, capture_output=False, check=False, timeout=None):
    """Helper function to run a command using subprocess."""
    try:
        # Use CREATE_NO_WINDOW to prevent console window flashes
        creationflags = subprocess.CREATE_NO_WINDOW
        print(f"Executing: {' '.join(command_parts)}") # Debugging
        result = subprocess.run(
            command_parts,
            shell=True,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout,
            creationflags=creationflags
        )
        print(f"Command finished: {' '.join(command_parts)}")
        if capture_output:
            if result.stdout: print(f"Output: {result.stdout.strip()}")
            if result.stderr: print(f"Error Output: {result.stderr.strip()}")
        return result
    except FileNotFoundError:
        print(f"Error: Command not found - {command_parts[0]}. Is it in your PATH?")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(command_parts)} (Code: {e.returncode})")
        if e.stdout: print(f"Output: {e.stdout.strip()}")
        if e.stderr: print(f"Error Output: {e.stderr.strip()}")
        return None
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {' '.join(command_parts)}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred running command: {' '.join(command_parts)} - {e}")
        return None

def disable_wacom_drivers():
    """Stops Wacom services and processes."""
    if not is_admin():
        print("Error: Cannot disable Wacom drivers without administrator privileges.")
        return False
    print("Attempting to disable Wacom drivers...")
    commands = [
        [CMD_TASKKILL, "/F", "/IM", "Wacom_Tablet.exe"], [CMD_TASKKILL, "/F", "/IM", "Pen_Tablet.exe"],
        [CMD_NET, "stop", "WTabletServicePro"], [CMD_TIMEOUT, "/t", "1", "/nobreak"],
        [CMD_NET, "start", "WTabletServicePro"], [CMD_NET, "stop", "WTabletServiceCon"],
        [CMD_TIMEOUT, "/t", "1", "/nobreak"], [CMD_NET, "start", "WTabletServiceCon"],
        [CMD_TASKKILL, "/F", "/IM", "WacomDesktopCenter.exe"], [CMD_TIMEOUT, "/t", "2", "/nobreak"],
        [CMD_TASKKILL, "/F", "/IM", "Wacom_Tablet.exe"], [CMD_TASKKILL, "/F", "/IM", "Pen_Tablet.exe"]
    ]
    success = True
    for cmd in commands:
        result = run_command(cmd)
        if result is None: success = False; break
        # Be lenient with non-zero return codes for taskkill/net stop/start unless critical
        if cmd[0] == CMD_NET and result.returncode not in [0, 2]:
            print(f"Warning: Command '{' '.join(cmd)}' may have failed with return code {result.returncode}")
        elif cmd[0] == CMD_TASKKILL and result.returncode != 0 and result.returncode != 128:
             print(f"Warning: Command '{' '.join(cmd)}' failed with return code {result.returncode}")
    print(f"Wacom driver disable sequence {'completed' if success else 'encountered errors'}.")
    return success

def enable_wacom_drivers():
    """Stops OTD and restarts Wacom services."""
    if not is_admin():
        print("Error: Cannot enable Wacom drivers without administrator privileges.")
        return False
    print("Attempting to enable Wacom drivers and stop OTD...")
    # Use OTD process names from constants
    for process_name in constants.OTD_PROCESSES:
        print(f"Attempting to stop process: {process_name}")
        run_command([CMD_TASKKILL, "/F", "/IM", process_name]) # Ignore result, might not be running

    commands = [
        [CMD_NET, "stop", "WTabletServicePro"], [CMD_TIMEOUT, "/t", "1", "/nobreak"],
        [CMD_NET, "start", "WTabletServicePro"], [CMD_NET, "stop", "WTabletServiceCon"],
        [CMD_TIMEOUT, "/t", "1", "/nobreak"], [CMD_NET, "start", "WTabletServiceCon"],
    ]
    success = True
    for cmd in commands:
        result = run_command(cmd)
        if result is None: success = False; break
        if cmd[0] == CMD_NET and result.returncode not in [0, 2]:
            print(f"Warning: Command '{' '.join(cmd)}' may have failed with return code {result.returncode}")
    print(f"Wacom driver enable sequence {'completed' if success else 'encountered errors'}.")
    return success

def launch_process(executable_path, working_directory=None):
    """Launches an executable asynchronously."""
    if not executable_path or not os.path.exists(executable_path):
        print(f"Error: Executable path invalid/missing: '{executable_path}'")
        return None
    try:
        effective_wd = working_directory or os.path.dirname(executable_path)
        print(f"Launching: '{executable_path}' in WD '{effective_wd}'")
        # CREATE_NO_WINDOW prevents console flash for GUI apps too
        process = subprocess.Popen(f'"{executable_path}"', cwd=effective_wd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        print(f"Process launched (PID: {process.pid})")
        return process
    except (FileNotFoundError, OSError, Exception) as e:
        print(f"Error launching '{executable_path}': {e}. Check path, permissions, and valid executable.")
        return None

def launch_process_standard(executable_path, working_directory=None):
    """
    Attempts to launch an executable as the standard (non-elevated) user,
    even if the current script is elevated. Uses 'runas /trustlevel'.
    Returns True on successful launch command execution, False otherwise.
    Note: This returns immediately after requesting launch.
    """
    if not executable_path or not os.path.exists(executable_path):
        print(f"Error: Executable path invalid/missing for standard user launch: '{executable_path}'")
        return False

    if working_directory:
        print(f"Warning: Working directory '{working_directory}' specified but cannot be set via 'runas'. Process CWD might differ.")

    try:
        quoted_path = f'"{executable_path}"'

        # Command using runas to launch as a standard user (0x20000 = Basic User)
        command = [
            'runas',
            '/trustlevel:0x20000',
            quoted_path
        ]

        print(f"[Standard User Launch via runas] Executing: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW,\
        )
        print(f"Successfully executed 'runas' command (PID: {process.pid}). OTD should launch as standard user.")
        return True

    except FileNotFoundError:
        print(f"CRITICAL ERROR: 'runas' command not found. Cannot launch as standard user.")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Exception during standard user launch attempt via runas for '{executable_path}': {e}")
        traceback.print_exc() 
        return False


# --- Path Validation ---
def get_desktop_path():
    return os.path.join(os.path.expanduser('~'), 'Desktop')

def is_valid_osu_path(folder_path):
    if not folder_path or not os.path.isdir(folder_path): return False
    return os.path.exists(os.path.join(folder_path, constants.OSU_EXECUTABLE))

def get_primary_executable(folder_path, executable_list):
    if not folder_path or not os.path.isdir(folder_path): return None
    for name in executable_list:
        full_path = os.path.join(folder_path, name)
        if os.path.exists(full_path):
            return full_path
    return None

def is_valid_otd_path(folder_path):
    return get_primary_executable(folder_path, constants.OTD_EXECUTABLES) is not None

def get_otd_executable_path(folder_path):
    """Gets the path to the preferred OTD executable."""
    # Return the path to the GUI first if found, else any other known one
    return get_primary_executable(folder_path, constants.OTD_EXECUTABLES)


# --- Display Resolution Functions (Windows Only) ---
def _get_devmode(setting_index_or_type):
    """Helper to get DEVMODE object by index or type (like ENUM_CURRENT_SETTINGS)."""
    try:
        # None gets settings for the primary display adapter
        return win32api.EnumDisplaySettings(None, setting_index_or_type)
    except pywintypes.error as e:
        # This might happen if index is out of bounds or type is invalid
        print(f"Error enumerating display settings (index/type: {setting_index_or_type}): {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in _get_devmode: {e}")
        return None

def get_current_resolution():
    """Gets the current screen resolution for the primary display."""
    devmode = _get_devmode(win32con.ENUM_CURRENT_SETTINGS)
    return (devmode.PelsWidth, devmode.PelsHeight) if devmode else (None, None)

def get_native_resolution():
    """
    Gets the 'native' resolution by finding the highest resolution
    reported as supported by the primary display adapter.
    """
    max_w, max_h = 0, 0
    modes_found = False
    i = 0
    print("Attempting to find highest supported resolution by iterating modes...")
    try:
        while True:
            devmode = _get_devmode(i) # Get mode by index 'i'
            if not devmode:
                # print(f"No more modes found at index {i}.")
                break # No more modes available for this display

            modes_found = True
            current_w = devmode.PelsWidth
            current_h = devmode.PelsHeight
            # Optional: Log found modes for debugging
            # print(f" Mode {i}: {current_w}x{current_h} @ {devmode.DisplayFrequency}Hz, {devmode.BitsPerPel}bpp")

            # Update max resolution based on pixel count (area) or simple dimensions
            # Using simple dimensions comparison:
            if current_w >= max_w and current_h >= max_h:
                 # Could add a check for aspect ratio proximity if needed, but usually not required
                 max_w = current_w
                 max_h = current_h

            # Using area comparison (might be slightly better if odd resolutions exist):
            # current_area = current_w * current_h
            # max_area = max_w * max_h
            # if current_area >= max_area:
            #     max_w = current_w
            #     max_h = current_h

            i += 1
    except Exception as e:
        print(f"Error during native resolution detection loop at index {i}: {e}")
        traceback.print_exc()
        # Fallback if loop fails unexpectedly
        print("Falling back to current resolution due to error during mode iteration.")
        return get_current_resolution()

    if modes_found and max_w > 0 and max_h > 0:
        print(f"Determined highest supported resolution (native candidate): {max_w}x{max_h}")
        return max_w, max_h
    else:
        # Fallback if loop completes but finds nothing useful (very unlikely)
        print("Warning: Could not determine highest resolution by iterating modes. Falling back to current resolution.")
        return get_current_resolution()


def set_resolution(width, height):
    """Sets the screen resolution for the primary display."""
    # ... (Keep the existing set_resolution function as it was) ...
    if not is_admin():
        print("Error: Admin privileges required to change screen resolution.")
        return False

    devmode = _get_devmode(win32con.ENUM_CURRENT_SETTINGS)
    if not devmode:
        print("Error: Could not get current display settings.")
        return False

    if devmode.PelsWidth == width and devmode.PelsHeight == height:
        print(f"Resolution already {width}x{height}. No change needed.")
        return "UNCHANGED"

    print(f"Attempting to change resolution to {width}x{height}")
    devmode.PelsWidth = width
    devmode.PelsHeight = height
    devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT

    try:
        result = win32api.ChangeDisplaySettings(devmode, 0)
        if result == win32con.DISP_CHANGE_SUCCESSFUL:
            print("Resolution changed successfully.")
            return True
        else:
            error_map = { # Simplified error map
                win32con.DISP_CHANGE_BADMODE: "Mode not supported.",
                win32con.DISP_CHANGE_FAILED: "Driver failed the mode.",
                win32con.DISP_CHANGE_RESTART: "Restart required.",
            }
            error_msg = error_map.get(result, f"Unknown error code: {result}")
            print(f"Failed to change resolution. Result: {error_msg}")
            return False
    except (pywintypes.error, Exception) as e:
        print(f"Error calling ChangeDisplaySettings: {e}")
        traceback.print_exc() # Add traceback for set_resolution errors too
        return False

# Import constants at the end to avoid circular import issues if utils needs constants early
from . import constants
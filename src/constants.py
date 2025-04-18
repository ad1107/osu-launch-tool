import os

# --- Application Info ---
APP_NAME = "osu! Launch Tool"
APP_VERSION = "1.0.0"

# --- Configuration File ---
CONFIG_DIR = os.path.join(os.getenv('APPDATA', ''), APP_NAME) # Store config in %APPDATA%
CONFIG_FILE_NAME = "config.ini"
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

# --- Config Sections and Keys ---
CONFIG_SECTION_PATHS = "Paths"
CONFIG_KEY_OSU_PATH = "OsuPath"
CONFIG_KEY_OTD_PATH = "OtdPath"

# --- Executable Names (for validation and execution) ---
OSU_EXECUTABLE = "osu!.exe"
# List potential OTD executables (GUI preferred)
OTD_EXECUTABLES = ["OpenTabletDriver.UX.Wpf.exe", "OpenTabletDriver.Daemon.exe"]
OTD_GUI_EXECUTABLE = "OpenTabletDriver.UX.Wpf.exe" # The one we ideally launch

# --- Driver Process/Service Names (for killing/controlling) ---
WACOM_PROCESSES = ["Wacom_Tablet.exe", "Pen_Tablet.exe", "WacomDesktopCenter.exe"]
WACOM_SERVICES = ["WTabletServicePro", "WTabletServiceCon"]
OTD_PROCESSES = ["OpenTabletDriver.UX.Wpf.exe", "OpenTabletDriver.Daemon.exe"] # Add others if needed

# --- UI Texts ---
TITLE_SELECT_OSU_FOLDER = "Select osu! Installation Folder"
TITLE_SELECT_OTD_FOLDER = "Select OpenTabletDriver Folder"
LABEL_OSU_PATH = "osu! Path:"
LABEL_OTD_PATH = "OTD Path:"
BUTTON_BROWSE = "Browse..."
BUTTON_RUN_OSU_OTD = "Run osu! with OpenTabletDriver"
BUTTON_RUN_OSU_ONLY = "Run osu! Only (Update)"
BUTTON_RUN_OTD_ONLY = "Disable Wacom & Run OTD"
BUTTON_ENABLE_WACOM = "Disable OTD & Enable Wacom"

# --- Status Messages ---
STATUS_READY = "Ready."
STATUS_CONFIG_MISSING = "Configuration missing. Please select paths."
STATUS_OSU_INVALID = "Invalid osu! path selected."
STATUS_OTD_INVALID = "Invalid OpenTabletDriver path selected."
STATUS_VALIDATING = "Validating paths..."
STATUS_RUNNING = "Running..."
STATUS_DISABLING_WACOM = "Disabling Wacom drivers..."
STATUS_ENABLING_WACOM = "Enabling Wacom drivers..."
STATUS_LAUNCHING_OSU = "Launching osu!..."
STATUS_LAUNCHING_OTD = "Launching OpenTabletDriver..."
STATUS_COMPLETE = "Operation completed."
STATUS_ERROR = "An error occurred. Check logs."

# --- Configuration Resolution Section ---
CONFIG_SECTION_RESOLUTION = "Resolution"
CONFIG_KEY_RES_X = "DownscaleX"
CONFIG_KEY_RES_Y = "DownscaleY"

# --- UI Texts (Resolution) ---
LABEL_RESOLUTION_SECTION = "Display Resolution Control"
BUTTON_DOWNSCALE = "Downscale Resolution"
BUTTON_RESTORE_NATIVE = "Restore Native Resolution"
LABEL_RES_X = "X:"
LABEL_RES_Y = "Y:"

# --- Status Messages (Resolution) ---
STATUS_GETTING_NATIVE_RES = "Getting native resolution..."
STATUS_SETTING_RES = "Setting resolution to {}x{}..."
STATUS_RESTORING_RES = "Restoring native resolution..."
STATUS_INVALID_RES_INPUT = "Invalid resolution input. Please enter numbers only."
STATUS_SET_RES_FAIL = "Failed to set resolution. Mode might not be supported."
STATUS_GET_NATIVE_FAIL = "Failed to determine native resolution."
STATUS_RES_UNCHANGED = "Resolution unchanged."

# --- UI Texts (Utility) ---
BUTTON_GO_TO_OSU_FOLDER = "Go to osu! Folder"
BUTTON_EXPORT_CONFIG = "Export Safe osu! Config"
TITLE_EXPORT_CONFIG_DIALOG = "Export osu! Configuration"
LABEL_SELECT_CONFIGS = "Select config(s) to export:"
LABEL_EXPORT_PATH = "Export to:"
BUTTON_BROWSE_EXPORT_PATH = "Browse..."
BUTTON_EXPORT_OK = "Export Selected"
BUTTON_EXPORT_CANCEL = "Cancel"
TITLE_SELECT_EXPORT_FOLDER = "Select Export Destination Folder"

# --- Status/Messages (Utility) ---
STATUS_EXPORTING_CONFIG = "Exporting configuration..."
STATUS_EXPORT_NO_CONFIGS = "No user-specific osu! config files (*.cfg) found in the osu! folder."
STATUS_EXPORT_COMPLETE = "Configuration export complete."
STATUS_EXPORT_FAILED = "Configuration export failed."
MSG_CONFIRM_EXPORT_TITLE = "Export Successful"
MSG_CONFIRM_EXPORT_BODY = "Selected configuration(s) exported successfully to:\n{}" # Placeholder for path
BUTTON_OPEN_EXPORT_FOLDER = "Open Folder"

# --- Config Export ---
OSU_CONFIG_EXCLUDE = "osu!.cfg" # Default config file to ignore
SAFE_CONFIG_PREFIX = "SAFE_"
SAFE_CONFIG_HEADER = """
# osu! configuration exported by osu! Launch Tool
# Original username associated with this config: {original_username}
# Exported on: {export_time}
# IMPORTANT: The user's password/token has been REMOVED from this file.
# This file should be safe to share for troubleshooting or comparison purposes.
# Original sensitive header comments may have been removed or replaced.
#----------------------------------------------------------

"""
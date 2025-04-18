import customtkinter as ctk
from tkinter import filedialog, Text, END, Scrollbar, messagebox
import os
import threading
import time
import traceback
import re # For parsing config
from datetime import datetime

# Import modules from our package
from . import config_manager
from . import utils
from . import constants

# --- Custom Export Dialog ---
class ExportConfigDialog(ctk.CTkToplevel):
    """Modal dialog for selecting osu! configs and export destination."""
    def __init__(self, parent, config_files):
        super().__init__(parent)

        self.parent = parent
        self.config_files = config_files
        self.selected_configs = []
        self.export_path = ctk.StringVar(value=utils.get_desktop_path())
        self.result = None # Stores (selected_files, export_path) or None

        self.title(constants.TITLE_EXPORT_CONFIG_DIALOG)
        self.lift() # Bring window to front
        self.attributes("-topmost", True) # Keep on top
        self.geometry("500x400") # Adjust size as needed
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel) # Handle window close

        # Make modal
        self.transient(parent) # Associate with parent
        self.grab_set()

        # --- Widgets ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Allow scrollable frame to expand

        # Info Label
        ctk.CTkLabel(self, text=constants.LABEL_SELECT_CONFIGS, anchor="w").grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        scroll_frame = ctk.CTkScrollableFrame(self, label_text="")
        scroll_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        self.checkbox_vars = {}
        for i, cfg_file in enumerate(config_files):
            var = ctk.StringVar(value="off")
            # Pre-check the first one if it's the only config file
            if len(config_files) == 1:
                var.set(cfg_file) # Use filename as the 'on' value
            cb = ctk.CTkCheckBox(scroll_frame, text=cfg_file, variable=var, onvalue=cfg_file, offvalue="off")
            cb.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.checkbox_vars[cfg_file] = var

        # Export Path Frame
        path_frame = ctk.CTkFrame(self)
        path_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(path_frame, text=constants.LABEL_EXPORT_PATH).grid(row=0, column=0, padx=(5,0), pady=5, sticky="w")
        ctk.CTkEntry(path_frame, textvariable=self.export_path).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(path_frame, text=constants.BUTTON_BROWSE_EXPORT_PATH, width=80, command=self._browse_export_path).grid(
            row=0, column=2, padx=5, pady=5)

        # Action Buttons Frame
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="e")

        ctk.CTkButton(action_frame, text=constants.BUTTON_EXPORT_CANCEL, width=100, command=self._on_cancel).grid(
            row=0, column=0, padx=5)
        ctk.CTkButton(action_frame, text=constants.BUTTON_EXPORT_OK, width=100, command=self._on_ok).grid(
            row=0, column=1, padx=5)

        # Center the dialog relative to the parent after widgets are created
        self.update_idletasks()
        parent_geo = self.parent.geometry()
        parent_info = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", parent_geo)
        if parent_info:
             parent_w, parent_h, parent_x, parent_y = map(int, parent_info.groups())
             dialog_w = self.winfo_width()
             dialog_h = self.winfo_height()
             x = parent_x + (parent_w // 2) - (dialog_w // 2)
             y = parent_y + (parent_h // 2) - (dialog_h // 2)
             self.geometry(f"+{x}+{y}") # Position relative to parent
        else:
             print("Warning: Could not parse parent geometry to center dialog.")


    def _browse_export_path(self):
        directory = filedialog.askdirectory(initialdir=self.export_path.get() or "/", title=constants.TITLE_SELECT_EXPORT_FOLDER)
        if directory:
            self.export_path.set(directory)

    def _on_ok(self):
        """Handles OK button click, validates selection, and closes."""
        self.selected_configs = [var.get() for var in self.checkbox_vars.values() if var.get() != "off"]
        export_dest = self.export_path.get()

        if not self.selected_configs:
            messagebox.showwarning("No Selection", "Please select at least one configuration file to export.", parent=self)
            return
        if not export_dest or not os.path.isdir(export_dest):
            messagebox.showwarning("Invalid Path", "Please select a valid export destination folder.", parent=self)
            return

        self.result = (self.selected_configs, export_dest)
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()

    def get_result(self):
        """Waits for the dialog to close and returns the result."""
        self.master.wait_window(self)
        return self.result


# --- Main App Class ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{constants.APP_NAME} v{constants.APP_VERSION}")
        self.resizable(False, False)
        self.center_window(650, 610)

        # --- Path Variables ---
        self.osu_path = ctk.StringVar(value=config_manager.get_osu_path() or "")
        self.otd_path = ctk.StringVar(value=config_manager.get_otd_path() or "")
        self.is_osu_valid = False
        self.is_otd_valid = False

        # --- Resolution Variables ---
        saved_res_x, saved_res_y = config_manager.get_resolution_config()
        self.res_x_var = ctk.StringVar(value=str(saved_res_x) if saved_res_x else "")
        self.res_y_var = ctk.StringVar(value=str(saved_res_y) if saved_res_y else "")
        self.native_res_x = None
        self.native_res_y = None

        # --- GUI Elements ---
        self.create_widgets()

        # --- Initial State ---
        self.validate_paths_on_startup()
        self.fetch_native_resolution_async() 
        self.update_button_states() 
        self.res_x_var.trace_add("write", self._on_res_entry_change)
        self.res_y_var.trace_add("write", self._on_res_entry_change)

        config_manager.ensure_config_exists() # Ensure config dir exists

    def center_window(self, width=600, height=400):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.geometry(f'{width}x{height}+{int(x)}+{int(y)}')

    def create_widgets(self):
        """Creates and places all the GUI widgets."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1) # Log area row index is now 4

        # --- Path Selection Frame (Row 0) ---
        path_frame = ctk.CTkFrame(self)
        path_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        path_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(path_frame, text=constants.LABEL_OSU_PATH).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.osu_entry = ctk.CTkEntry(path_frame, textvariable=self.osu_path, state="readonly", width=350)
        self.osu_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.osu_browse_btn = ctk.CTkButton(path_frame, text=constants.BUTTON_BROWSE, width=80, command=self.browse_osu_path)
        self.osu_browse_btn.grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkLabel(path_frame, text=constants.LABEL_OTD_PATH).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.otd_entry = ctk.CTkEntry(path_frame, textvariable=self.otd_path, state="readonly", width=350)
        self.otd_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.otd_browse_btn = ctk.CTkButton(path_frame, text=constants.BUTTON_BROWSE, width=80, command=self.browse_otd_path)
        self.otd_browse_btn.grid(row=1, column=2, padx=5, pady=5)

        # --- Action Buttons Frame (Row 1) ---
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)
        self.run_osu_otd_btn = ctk.CTkButton(button_frame, text=constants.BUTTON_RUN_OSU_OTD, command=lambda: self.run_task(self.action_run_osu_with_otd))
        self.run_osu_otd_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.run_osu_only_btn = ctk.CTkButton(button_frame, text=constants.BUTTON_RUN_OSU_ONLY, command=lambda: self.run_task(self.action_run_osu_only))
        self.run_osu_only_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.run_otd_only_btn = ctk.CTkButton(button_frame, text=constants.BUTTON_RUN_OTD_ONLY, command=lambda: self.run_task(self.action_run_otd_only))
        self.run_otd_only_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.enable_wacom_btn = ctk.CTkButton(button_frame, text=constants.BUTTON_ENABLE_WACOM, command=lambda: self.run_task(self.action_enable_wacom))
        self.enable_wacom_btn.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # --- Resolution Control Frame (Row 2) ---
        res_frame = ctk.CTkFrame(self)
        res_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        res_frame.grid_columnconfigure(0, weight=1) # Downscale button space
        res_frame.grid_columnconfigure(5, weight=1) # Restore button space
        self.downscale_btn = ctk.CTkButton(res_frame, text=constants.BUTTON_DOWNSCALE, command=lambda: self.run_task(self.action_downscale_resolution))
        self.downscale_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(res_frame, text=constants.LABEL_RES_X, width=20).grid(row=0, column=1, padx=(5,0), pady=5, sticky="e")
        self.res_x_entry = ctk.CTkEntry(res_frame, textvariable=self.res_x_var, width=60)
        self.res_x_entry.grid(row=0, column=2, padx=(0,5), pady=5)
        ctk.CTkLabel(res_frame, text=constants.LABEL_RES_Y, width=20).grid(row=0, column=3, padx=(5,0), pady=5, sticky="e")
        self.res_y_entry = ctk.CTkEntry(res_frame, textvariable=self.res_y_var, width=60)
        self.res_y_entry.grid(row=0, column=4, padx=(0,5), pady=5)
        self.restore_res_btn = ctk.CTkButton(res_frame, text=constants.BUTTON_RESTORE_NATIVE, command=lambda: self.run_task(self.action_restore_resolution))
        self.restore_res_btn.grid(row=0, column=5, padx=5, pady=5, sticky="ew")

        # --- Utility Frame (Row 3) 
        utility_frame = ctk.CTkFrame(self)
        utility_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        utility_frame.grid_columnconfigure((0, 1), weight=1) # Give buttons equal space
        self.go_to_osu_btn = ctk.CTkButton(utility_frame, text=constants.BUTTON_GO_TO_OSU_FOLDER, command=self.action_go_to_osu_folder)
        self.go_to_osu_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.export_config_btn = ctk.CTkButton(utility_frame, text=constants.BUTTON_EXPORT_CONFIG, command=self.trigger_export_config) # Doesn't use run_task directly
        self.export_config_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # --- Logging Frame (Row 4) 
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        self.log_textbox = Text(log_frame, height=10, wrap="word", state="disabled",
                        bg=self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1]),
                        fg=self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"]),
                        relief="flat", bd=0, font=("Consolas", 20))
        scrollbar = Scrollbar(log_frame, command=self.log_textbox.yview)
        self.log_textbox['yscrollcommand'] = scrollbar.set
        self.log_textbox.grid(row=0, column=0, padx=(5,0), pady=5, sticky="nsew")
        scrollbar.grid(row=0, column=1, padx=(0,5), pady=5, sticky="ns")

        # --- Status Bar (Row 5) 
        self.status_label = ctk.CTkLabel(self, text=constants.STATUS_READY, anchor="w")
        self.status_label.grid(row=5, column=0, padx=10, pady=(0, 5), sticky="ew")

        # --- Initial Log/Status ---
        self.log_message(f"{constants.APP_NAME} initialized. Waiting for input.")
        if not self.osu_path.get() or not self.otd_path.get():
            self.log_message(constants.STATUS_CONFIG_MISSING, level="WARN")
            self.update_status(constants.STATUS_CONFIG_MISSING)

    def log_message(self, message, level="INFO"):
        """Appends a message to the log text box."""
        try:
            timestamp = time.strftime("%H:%M:%S")
            formatted_message = f"[{timestamp} {level}] {message}\n"
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert(END, formatted_message)
            self.log_textbox.configure(state="disabled")
            self.log_textbox.see(END) # Scroll to the bottom

    def update_status(self, message):
        """Updates the bottom status bar label."""
        self.status_label.configure(text=message)
        self.update_idletasks() # Force GUI update

    def _on_res_entry_change(self, *args):
        """Callback when resolution entry text changes."""
        self.update_button_states()

    def update_button_states(self):
        """Enables or disables action buttons based on validity and state."""
        # Assume admin rights were obtained if app is running
        is_admin_ok = utils.is_admin()

        # Path-based buttons
        main_state = "normal" if (self.is_osu_valid and self.is_otd_valid and is_admin_ok) else "disabled"
        osu_only_state = "normal" if self.is_osu_valid else "disabled" # Doesn't need admin technically
        otd_only_state = "normal" if self.is_otd_valid and is_admin_ok else "disabled"
        wacom_enable_state = "normal" if is_admin_ok else "disabled"

        self.run_osu_otd_btn.configure(state=main_state)
        self.run_osu_only_btn.configure(state=osu_only_state)
        self.run_otd_only_btn.configure(state=otd_only_state)
        self.enable_wacom_btn.configure(state=wacom_enable_state)

        # Resolution buttons
        try: int(self.res_x_var.get()); int(self.res_y_var.get()); num_valid = True
        except ValueError: num_valid = False
        downscale_state = "normal" if is_admin_ok and num_valid else "disabled"
        restore_state = "normal" if is_admin_ok and self.native_res_x is not None else "disabled"
        self.downscale_btn.configure(state=downscale_state)
        self.restore_res_btn.configure(state=restore_state)

        # Utility buttons (don't require admin)
        utility_state = "normal" if self.is_osu_valid else "disabled"
        self.go_to_osu_btn.configure(state=utility_state)
        self.export_config_btn.configure(state=utility_state)

    def validate_paths_on_startup(self):
        """Validates paths loaded from config on startup."""
        osu_p = self.osu_path.get()
        otd_p = self.otd_path.get()
        self.is_osu_valid = utils.is_valid_osu_path(osu_p) if osu_p else False
        self.is_otd_valid = utils.is_valid_otd_path(otd_p) if otd_p else False
        if osu_p: self.log_message(f"Loaded osu! path valid: {self.is_osu_valid} ({osu_p})")
        if otd_p: self.log_message(f"Loaded OTD path valid: {self.is_otd_valid} ({otd_p})")

    def browse_path(self, target_variable, title, validation_func, config_setter, validation_flag_name, default_suggestion=None):
        current_val = target_variable.get()
        # Determine initial directory: Current value -> Default suggestion -> User's home -> Root
        initial_dir = current_val or default_suggestion or os.path.expanduser("~") or "/"

        directory = filedialog.askdirectory(initialdir=initial_dir, title=title, parent=self) # Set parent
        if not directory:
            self.log_message("Path selection cancelled.")
            self.update_status(constants.STATUS_READY)
            return

        self.update_status(constants.STATUS_VALIDATING)
        self.log_message(f"Validating selected path: {directory}")
        is_valid = validation_func(directory)
        setattr(self, validation_flag_name, is_valid)

        if is_valid:
            target_variable.set(directory)
            config_setter(directory)
            self.log_message(f"Path set and saved: {directory}")
            self.update_status(constants.STATUS_READY)
        else:
            error_title = "Invalid Folder Selected"
            expected_file_info = ""
            if validation_flag_name == 'is_osu_valid':
                expected_file_info = f"Required file: '{constants.OSU_EXECUTABLE}'"
            elif validation_flag_name == 'is_otd_valid':
                expected_files = "' or '".join(constants.OTD_EXECUTABLES)
                expected_file_info = f"Required file (e.g.): '{expected_files}'"

            error_msg = f"The selected folder:\n{directory}\n\ndoes not contain the required file(s).\n({expected_file_info})"
            self.log_message(f"Invalid path selected: {directory}. {expected_file_info} not found.", level="ERROR")
            messagebox.showerror(error_title, error_msg, parent=self) # Set parent for messagebox
            self.update_status(f"Invalid path selected for {title}.")

        self.update_button_states() 

    def browse_osu_path(self):
        default_osu = os.path.join(os.getenv('LOCALAPPDATA', ''), 'osu!')
        self.browse_path(self.osu_path, constants.TITLE_SELECT_OSU_FOLDER,
                         utils.is_valid_osu_path, config_manager.set_osu_path, 'is_osu_valid',
                         default_suggestion=default_osu)

    def browse_otd_path(self):
        default_otd = os.path.join(os.path.expanduser('~'), 'Downloads') 
        self.browse_path(self.otd_path, constants.TITLE_SELECT_OTD_FOLDER,
                         utils.is_valid_otd_path, config_manager.set_otd_path, 'is_otd_valid',
                         default_suggestion=default_otd)

    # --- Native Resolution Fetching ---
    def fetch_native_resolution_async(self):
        self.log_message("Fetching native screen resolution...")
        self.update_status(constants.STATUS_GETTING_NATIVE_RES)
        thread = threading.Thread(target=self._fetch_native_res_task, daemon=True)
        thread.start()

    def _fetch_native_res_task(self):
        """Task to get native resolution."""
        native_x, native_y = utils.get_native_resolution()
        if native_x and native_y:
            self.native_res_x = native_x
            self.native_res_y = native_y
            self.after(0, lambda: self.log_message(f"Native resolution detected: {self.native_res_x}x{self.native_res_y}"))
            self.after(0, lambda: self.update_status(constants.STATUS_READY))
        else:
            self.after(0, lambda: self.log_message(constants.STATUS_GET_NATIVE_FAIL, level="ERROR"))
            self.after(0, lambda: self.update_status(constants.STATUS_GET_NATIVE_FAIL))
        self.after(100, self.update_button_states)

    # --- Task Running Wrapper ---
    def run_task(self, target_function, args=()):
        """Runs a target function in a separate thread to avoid freezing the GUI."""
        # Disable all action buttons immediately
        self._set_action_buttons_state("disabled")
        self.update_status(constants.STATUS_RUNNING)
        # Pass arguments to the wrapper correctly
        thread = threading.Thread(target=self._task_wrapper, args=(target_function, args), daemon=True)
        thread.start()

    def _task_wrapper(self, target_function, args):
        """Internal wrapper for threaded tasks."""
        try:
            target_function(*args)
            if self.status_label.cget("text") == constants.STATUS_RUNNING:
                 self.after(0, lambda: self.update_status(constants.STATUS_READY))
            self.after(0, lambda: self.log_message("Task completed.", level="INFO"))
        except Exception as e:
            error_message = f"Error during task execution: {e}"
            traceback_info = traceback.format_exc()
            self.after(0, lambda: self.log_message(error_message, level="ERROR"))
            self.after(0, lambda: self.log_message(traceback_info, level="DEBUG"))
            self.after(0, lambda: self.update_status(constants.STATUS_ERROR))
        finally:
            self.after(100, self.update_button_states)

    def _set_action_buttons_state(self, state):
        """Sets the state of *most* action buttons (excludes browse/utility)."""
        buttons = [
            self.run_osu_otd_btn, self.run_osu_only_btn, self.run_otd_only_btn,
            self.enable_wacom_btn, self.downscale_btn, self.restore_res_btn
        ]
        for btn in buttons:
            btn.configure(state=state)
        self.update_idletasks() # Ensure visual update

    # --- Button Actions ---
    def _validate_paths_for_action(self, require_osu=False, require_otd=False):
        """Helper to check needed paths before an action. Returns True if valid."""
        if require_osu and not self.is_osu_valid:
            self.log_message("Action failed: Invalid osu! path.", level="ERROR")
            messagebox.showerror("Error", "Cannot perform action: osu! path is not valid.", parent=self)
            return False
        if require_otd and not self.is_otd_valid:
            self.log_message("Action failed: Invalid OpenTabletDriver path.", level="ERROR")
            messagebox.showerror("Error", "Cannot perform action: OpenTabletDriver path is not valid.", parent=self)
            return False
        return True

    def action_run_osu_with_otd(self):
        self.log_message("Action: Run osu! with OpenTabletDriver")
        if not self._validate_paths_for_action(require_osu=True, require_otd=True): return

        osu_exe = os.path.join(self.osu_path.get(), constants.OSU_EXECUTABLE)
        otd_folder = self.otd_path.get()
        otd_exe = utils.get_otd_executable_path(otd_folder)

        self.update_status(constants.STATUS_DISABLING_WACOM)
        if not utils.disable_wacom_drivers(): raise Exception("Wacom driver disable failed.")

        self.update_status(constants.STATUS_LAUNCHING_OTD)
        otd_launched = utils.launch_process_standard(otd_exe, working_directory=otd_folder)
        if not otd_launched:
             self.log_message("Failed to request OpenTabletDriver launch as standard user (continuing...).", level="WARN")
        time.sleep(1)

        self.update_status(constants.STATUS_LAUNCHING_OSU)
        osu_process = utils.launch_process(osu_exe, working_directory=self.osu_path.get())
        if not osu_process: raise Exception("osu! launch failed.")

        self.log_message("osu! and OTD launch sequence initiated.")


    def action_run_osu_only(self):
        self.log_message("Action: Run osu! Only")
        if not self._validate_paths_for_action(require_osu=True): return

        osu_exe = os.path.join(self.osu_path.get(), constants.OSU_EXECUTABLE)
        self.update_status(constants.STATUS_LAUNCHING_OSU)
        if not utils.launch_process(osu_exe, working_directory=self.osu_path.get()):
            raise Exception("osu! launch failed.")
        self.log_message("osu! launch initiated.")

    def action_run_otd_only(self):
        self.log_message("Action: Disable Wacom & Run OTD")
        if not self._validate_paths_for_action(require_otd=True): return

        otd_folder = self.otd_path.get()
        otd_exe = utils.get_otd_executable_path(otd_folder)
        if not otd_exe: raise Exception("Could not find OTD executable.")

        self.update_status(constants.STATUS_DISABLING_WACOM)
        if not utils.disable_wacom_drivers(): raise Exception("Wacom driver disable failed.")

        self.update_status(constants.STATUS_LAUNCHING_OTD)
        otd_launched = utils.launch_process_standard(otd_exe, working_directory=otd_folder)
        if not otd_launched:
            self.log_message("Failed to request OpenTabletDriver launch as standard user.", level="WARN")
        self.log_message("OTD launch sequence initiated.")

    def action_enable_wacom(self):
        self.log_message("Action: Disable OTD & Enable Wacom")
        self.update_status(constants.STATUS_ENABLING_WACOM)
        if not utils.enable_wacom_drivers():
            raise Exception("Wacom driver enable sequence failed.")
        self.log_message("Wacom enable sequence initiated.")

    def action_downscale_resolution(self):
        self.log_message("Action: Downscale Resolution")
        try:
            res_x = int(self.res_x_var.get())
            res_y = int(self.res_y_var.get())
            if res_x <= 0 or res_y <= 0: raise ValueError("Dimensions must be positive.")
        except ValueError as e:
            err_msg = f"{constants.STATUS_INVALID_RES_INPUT}: {e}"
            self.log_message(err_msg, level="ERROR")
            self.update_status(constants.STATUS_INVALID_RES_INPUT)
            messagebox.showerror("Invalid Input", f"{err_msg}\nPlease enter positive numbers only.", parent=self)
            # Use self.after to re-enable buttons correctly after this immediate failure
            self.after(100, self.update_button_states)
            return # Stop task processing

        self.update_status(constants.STATUS_SETTING_RES.format(res_x, res_y))
        result = utils.set_resolution(res_x, res_y)

        if result is True:
            self.log_message(f"Successfully set resolution to {res_x}x{res_y}")
            config_manager.set_resolution_config(res_x, res_y) # Save on success
            self.update_status(f"Resolution set to {res_x}x{res_y}")
        elif result == "UNCHANGED":
            self.log_message(constants.STATUS_RES_UNCHANGED)
            self.update_status(constants.STATUS_RES_UNCHANGED)
        else: # False
            self.log_message(constants.STATUS_SET_RES_FAIL, level="ERROR")
            self.update_status(constants.STATUS_SET_RES_FAIL)
            messagebox.showerror("Resolution Error", f"{constants.STATUS_SET_RES_FAIL}\nMode {res_x}x{res_y} might not be supported.", parent=self)

    def action_restore_resolution(self):
        self.log_message("Action: Restore Native Resolution")
        if self.native_res_x is None or self.native_res_y is None:
            msg = "Cannot restore: Native resolution not determined."
            self.log_message(msg, level="ERROR")
            self.update_status(constants.STATUS_GET_NATIVE_FAIL)
            messagebox.showerror("Resolution Error", msg, parent=self)
            # Use self.after to re-enable buttons correctly after this immediate failure
            self.after(100, self.update_button_states)
            return # Stop task processing

        native_x, native_y = self.native_res_x, self.native_res_y
        self.update_status(constants.STATUS_RESTORING_RES)
        result = utils.set_resolution(native_x, native_y)

        if result is True:
            self.log_message(f"Successfully restored native resolution {native_x}x{native_y}")
            self.update_status(f"Native resolution ({native_x}x{native_y}) restored.")
        elif result == "UNCHANGED":
            self.log_message("Native resolution is already active.")
            self.update_status(constants.STATUS_RES_UNCHANGED)
        else: # False
            self.log_message("Failed to restore native resolution.", level="ERROR")
            self.update_status(constants.STATUS_SET_RES_FAIL)
            messagebox.showerror("Resolution Error", "Failed to restore native resolution.", parent=self)

    # --- Utility Button Actions ---

    def action_go_to_osu_folder(self):
        self.log_message(f"Opening osu! folder: {self.osu_path.get()}")
        if not self._validate_paths_for_action(require_osu=True):
            self.update_status("Cannot open folder: Invalid osu! path.")
            return # Stop if path invalid

        try:
            folder_path = self.osu_path.get()
            if not os.path.isdir(folder_path):
                 raise FileNotFoundError(f"Path is not a valid directory: {folder_path}")
            os.startfile(folder_path) # Opens folder in explorer
            self.update_status("osu! folder opened.")
        except FileNotFoundError as fnf_err:
            self.log_message(f"Error: Folder not found at {self.osu_path.get()}", level="ERROR")
            messagebox.showerror("Error", f"Folder not found:\n{fnf_err}", parent=self)
            self.update_status("Error opening osu! folder.")
        except Exception as e:
            self.log_message(f"Error opening osu! folder: {e}", level="ERROR")
            messagebox.showerror("Error", f"Could not open folder:\n{e}", parent=self)
            self.update_status("Error opening osu! folder.")


    # --- Config Export Logic ---

    def trigger_export_config(self):
        """Starts the config export process (runs on main thread initially)."""
        self.log_message("Initiating osu! config export...")
        if not self._validate_paths_for_action(require_osu=True):
            self.update_status("Cannot export: Invalid osu! path.")
            return

        osu_dir = self.osu_path.get()
        try:
            all_files = os.listdir(osu_dir)
            # Regex to find files like osu!.COMPUTERNAME.cfg (case-insensitive)
            config_pattern = re.compile(r"^osu!\.(.+)\.cfg$", re.IGNORECASE)
            user_configs = [f for f in all_files if config_pattern.match(f) and f.lower() != constants.OSU_CONFIG_EXCLUDE.lower()]

            if not user_configs:
                self.log_message(constants.STATUS_EXPORT_NO_CONFIGS, level="WARN")
                messagebox.showinfo("No Configs Found", constants.STATUS_EXPORT_NO_CONFIGS, parent=self)
                self.update_status("Ready.")
                return

            self.log_message(f"Found config files: {user_configs}")

            # Show the custom dialog (this runs modally on the main thread)
            dialog = ExportConfigDialog(self, user_configs)
            result = dialog.get_result() # This waits until the dialog is closed

            if result:
                selected_files, export_path = result
                self.log_message(f"User selected files: {selected_files} for export to {export_path}")
                # Now run the actual file processing in a background thread
                # Pass arguments via the args tuple in run_task
                self.run_task(self.process_config_export, args=(selected_files, export_path))
            else:
                self.log_message("Config export cancelled by user.")
                self.update_status("Ready.")

        except FileNotFoundError:
             self.log_message(f"Error finding osu! folder: {osu_dir}", level="ERROR")
             messagebox.showerror("Error", f"Could not find osu! directory:\n{osu_dir}", parent=self)
             self.update_status("Error during export setup.")
        except Exception as e:
            self.log_message(f"Error finding/listing config files: {e}", level="ERROR")
            messagebox.showerror("Error", f"Could not list or process osu! folder contents:\n{e}", parent=self)
            self.update_status("Error during export setup.")


    def process_config_export(self, selected_files, export_path):
        """Processes and exports the selected config files (runs in background thread)."""
        self.update_status(constants.STATUS_EXPORTING_CONFIG)
        osu_dir = self.osu_path.get() # Get osu! path again within the thread
        success_count = 0
        export_errors = []

        for filename in selected_files:
            source_path = os.path.join(osu_dir, filename)
            # Add "SAFE_" prefix for the output filename
            safe_filename = f"{constants.SAFE_CONFIG_PREFIX}{filename}"
            dest_path = os.path.join(export_path, safe_filename)

            self.log_message(f"Processing '{filename}' -> '{safe_filename}'...")

            try:
                with open(source_path, 'r', encoding='utf-8', errors='ignore') as infile: # Ignore potential encoding errors
                    lines = infile.readlines()

                # Filter out the password line and potentially sensitive comments
                processed_lines = []
                password_found = False
                in_sensitive_header = True # Assume start might be sensitive
                for line in lines:
                    line_strip = line.strip()
                    # Remove password line (case-insensitive check)
                    if line_strip.lower().startswith("password ="):
                        password_found = True
                        continue
                    # Skip default sensitive comments at the very beginning if they contain keywords
                    if in_sensitive_header and line_strip.startswith('#'):
                        if "IMPORTANT: DO NOT SHARE" in line_strip.upper() or \
                           "LOGIN CREDENTIALS" in line_strip.upper():
                            continue # Skip this sensitive comment
                    else:
                        # Once we hit a non-comment or non-sensitive comment, stop header skipping
                        in_sensitive_header = False

                    processed_lines.append(line) # Keep other lines

                if password_found:
                    self.log_message(f"Password line removed from '{filename}'.")
                else:
                    self.log_message(f"No password line found in '{filename}'.", level="WARN")

                # Extract original username from filename (osu!.USERNAME.cfg)
                match = re.match(r"^osu!\.(.+)\.cfg$", filename, re.IGNORECASE)
                original_username = match.group(1) if match else "Unknown"

                # Prepare the safe header using constants
                header = constants.SAFE_CONFIG_HEADER.format(
                    original_username=original_username,
                    export_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )

                # Write the processed file
                with open(dest_path, 'w', encoding='utf-8') as outfile:
                    outfile.write(header)
                    outfile.writelines(processed_lines)

                self.log_message(f"Successfully exported '{safe_filename}'")
                success_count += 1

            except Exception as e:
                error_msg = f"Failed to process/export '{filename}': {e}"
                self.log_message(error_msg, level="ERROR")
                export_errors.append(error_msg)
                # Also log traceback for detailed debugging
                self.log_message(traceback.format_exc(), level="DEBUG")


        # --- Final Status Update (Scheduled for main thread) ---
        if success_count == len(selected_files) and not export_errors:
            final_msg = constants.MSG_CONFIRM_EXPORT_BODY.format(export_path)
            self.after(0, lambda: self.show_export_success_dialog(final_msg, export_path))
            self.after(0, lambda: self.update_status(constants.STATUS_EXPORT_COMPLETE))
        elif success_count > 0 and export_errors:
             error_summary = "\n".join(export_errors)
             self.after(0, lambda: messagebox.showwarning("Export Warning", f"Export completed with {len(export_errors)} error(s):\n\n{error_summary}", parent=self))
             self.after(0, lambda: self.update_status("Export completed with errors."))
        else: # No successes, all errors
            error_summary = "\n".join(export_errors)
            self.after(0, lambda: messagebox.showerror("Export Error", f"Export failed for all selected files:\n\n{error_summary}", parent=self))
            self.after(0, lambda: self.update_status(constants.STATUS_EXPORT_FAILED))


    def show_export_success_dialog(self, message, export_path):
        """Shows a custom success dialog with an 'Open Folder' button."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(constants.MSG_CONFIRM_EXPORT_TITLE)
        dialog.geometry("400x150") # Adjust size
        dialog.resizable(False, False)
        dialog.lift()
        dialog.attributes("-topmost", True)
        dialog.transient(self)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy) # Allow closing

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        msg_label = ctk.CTkLabel(dialog, text=message, wraplength=380, justify="left")
        msg_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        def _open_and_close():
            try:
                if not os.path.isdir(export_path):
                     raise FileNotFoundError(f"Export path no longer exists: {export_path}")
                os.startfile(export_path)
            except Exception as e:
                 messagebox.showerror("Error", f"Could not open folder:\n{e}", parent=dialog)
            dialog.grab_release()
            dialog.destroy()

        def _close():
            dialog.grab_release()
            dialog.destroy()

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ok_button = ctk.CTkButton(button_frame, text="OK", width=100, command=_close)
        ok_button.grid(row=0, column=0, padx=10)

        open_button = ctk.CTkButton(button_frame, text=constants.BUTTON_OPEN_EXPORT_FOLDER, width=120, command=_open_and_close)
        open_button.grid(row=0, column=1, padx=10)

        # Center dialog again after adding widgets
        dialog.update_idletasks()
        parent_geo = self.geometry()
        parent_info = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", parent_geo)
        if parent_info:
             parent_w, parent_h, parent_x, parent_y = map(int, parent_info.groups())
             dialog_w = dialog.winfo_width()
             dialog_h = dialog.winfo_height()
             x = parent_x + (parent_w // 2) - (dialog_w // 2)
             y = parent_y + (parent_h // 2) - (dialog_h // 2)
             dialog.geometry(f"+{x}+{y}")

        dialog.wait_window() # Make it blocking
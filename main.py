import customtkinter as ctk
import sys
import os
from src import app, utils, config_manager
from tkinter import messagebox

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def main():
    if not utils.request_admin_elevation():
        try:
            root_tk = ctk.CTk()
            root_tk.withdraw()
            messagebox.showerror("Admin Privileges Required",
                                 "This application requires administrator privileges.\nPlease restart as administrator.")
            root_tk.destroy()
        except Exception as e:
            print(f"Could not show error message box: {e}")
            print("ADMIN PRIVILEGES REQUIRED. EXITING.")
        sys.exit(1)

    print("Running with sufficient privileges.")

    config_file = config_manager.get_config_path()
    if not os.path.exists(config_file):
        print(f"Config file not found at {config_file}. Will be created/used by app.")

    main_app = app.App()
    main_app.mainloop()

if __name__ == "__main__":
    main()
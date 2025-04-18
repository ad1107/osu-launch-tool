import configparser
import os
from . import constants 

# --- Configuration Handling ---

def get_config_path():
    return constants.CONFIG_FILE_PATH

def load_config():
    config = configparser.ConfigParser()
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            config.read(config_path)
            print(f"Configuration loaded from: {config_path}")
        except configparser.Error as e:
            print(f"Error reading config file {config_path}: {e}")
            return configparser.ConfigParser() # Return empty on error
    else:
        print(f"Configuration file not found at: {config_path}")
    return config

def save_config(config):
    config_path = get_config_path()
    config_dir = os.path.dirname(config_path)
    try:
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        print(f"Configuration saved to: {config_path}")
        return True
    except IOError as e:
        print(f"Error saving config file {config_path}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred saving config: {e}")
        return False

def get_path(key):
    config = load_config()
    return config.get(constants.CONFIG_SECTION_PATHS, key, fallback=None)

def set_path(key, value):
    """Sets a specific path in the config and saves it."""
    config = load_config()
    if not config.has_section(constants.CONFIG_SECTION_PATHS):
        config.add_section(constants.CONFIG_SECTION_PATHS)
    config.set(constants.CONFIG_SECTION_PATHS, key, value)
    return save_config(config)

def get_osu_path():
    return get_path(constants.CONFIG_KEY_OSU_PATH)

def set_osu_path(path):
    return set_path(constants.CONFIG_KEY_OSU_PATH, path)

def get_otd_path():
    return get_path(constants.CONFIG_KEY_OTD_PATH)

def set_otd_path(path):
    return set_path(constants.CONFIG_KEY_OTD_PATH, path)

def ensure_config_exists():
    config_dir = os.path.dirname(get_config_path())
    os.makedirs(config_dir, exist_ok=True)

# --- Resolution Config Functions ---

def get_resolution_config():
    config = load_config()
    res_x = config.get(constants.CONFIG_SECTION_RESOLUTION, constants.CONFIG_KEY_RES_X, fallback=None)
    res_y = config.get(constants.CONFIG_SECTION_RESOLUTION, constants.CONFIG_KEY_RES_Y, fallback=None)
    try:
        res_x = int(res_x) if res_x else None
        res_y = int(res_y) if res_y else None
    except ValueError:
        print("Warning: Invalid resolution value found in config. Ignoring.")
        return None, None
    return res_x, res_y

def set_resolution_config(res_x, res_y):
    config = load_config()
    if not config.has_section(constants.CONFIG_SECTION_RESOLUTION):
        config.add_section(constants.CONFIG_SECTION_RESOLUTION)
    config.set(constants.CONFIG_SECTION_RESOLUTION, constants.CONFIG_KEY_RES_X, str(res_x))
    config.set(constants.CONFIG_SECTION_RESOLUTION, constants.CONFIG_KEY_RES_Y, str(res_y))
    return save_config(config)
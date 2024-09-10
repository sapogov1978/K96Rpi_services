import logging
import os
import json
import time
from ping3 import ping, verbose_ping

os.chdir("/home/pi/K96Rpi")

#------------------------------------------------------------------------------
def check_server_response(host):
    """
    This function sends a ping request to the specified host and waits for a response.
    It uses the `ping` function with a timeout of 10 milliseconds.

    Args:
        host (str): The IP address or hostname of the server to ping.

    Returns:
        bool: True if the server responds within the timeout, False otherwise.
    """
    try:
        response_time = ping(host, unit='ms', size=32, timeout=10)
        if response_time is None or response_time is False:
            return False
        return True
    except Exception as e:
        return False
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def save_settings(settings):
    """
    Save program settings to a JSON file.
    
    Args:
        settings (dict): A dictionary containing program settings.
    
    Return:
        N/A
    
    Raises:
        FileNotFoundError: If the settings file path is not found.
        Exception: If an error occurs while saving the settings.
    """
    
    try:
        acquire_lock("settings")
        with open('settings.json', 'w') as settings_file:
            json.dump(settings, settings_file, indent=4)
        release_lock("settings")
        return 0
        
    except FileNotFoundError as e:
        return 1
    except Exception as e:
        return e
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def setup_logger(log_file):
    logger = logging.getLogger(log_file)
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        file_handler = logging.FileHandler(f"{log_dir}/{log_file}")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def load_settings():
    """
    Load application settings from a JSON file.

    This function reads and parses settings from a JSON file named 'settings.json'
    located in the current working directory. It is used to initialize and configure
    the application with predefined settings.
    
    Args:
        None

    Returns:
        settings (dict) or None: A dictionary containing the loaded settings if successful, or
        None if the settings file is not found or if there's an error decoding the JSON data.

    Raises:
        File Not Found and Decoding error
    """
    try:
        with open('settings.json', 'r') as file:
            settings = json.load(file)
        if settings is None:
            return None
        return settings
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        return None
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def acquire_lock(res_lock_file):
    while os.path.exists(f"locks/{res_lock_file}.lock"):
        time.sleep(0.1)
    open(f"locks/{res_lock_file}.lock", 'w').close()
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def release_lock(res_lock_file):
    if os.path.exists(f"locks/{res_lock_file}.lock"):
        os.remove(f"locks/{res_lock_file}.lock")
#------------------------------------------------------------------------------

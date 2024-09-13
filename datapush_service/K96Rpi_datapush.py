import time
import os
import sys
import signal
import subprocess
from datetime import datetime

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

def sigterm_handler(signum, frame):
    logger.critical(f'DATAPUSH: Sigterm recieved:\n {signum}\n {frame}')

signal.signal(signal.SIGTERM, sigterm_handler)

current_date = datetime.now().strftime("%Y%m%d")
logger = ll.setup_logger(f"{current_date}-datapush.log")
#------------------------------------------------------------------------------

files = [f for f in os.listdir('locks') if f.endswith('-datapush.lock')]
for file in files:
    file_path = os.path.join('locks', file)
    os.remove(file_path)

#------------------------------------------------------------------------------
def check_required_settings(settings):
    """
    This function verifies the presence of specific keys ('server' and 'local_directories')
    in the provided settings dictionary. If any of these required settings are missing,
    it logs an error message and returns False.

    Args:
        settings (dict): A dictionary containing application settings.

    Returns:
        bool: True if all required settings are present, False otherwise.
    """
    required_settings = ['server', 'local_directories']
    for setting in required_settings:
        if setting not in settings:
            logger.error(f"DATAPUSH: Required setting '{setting}' is missing in settings.json.")
            return False
    return True
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def push_files(local_dir, remote_dir, settings):
    try:
        # Get SSH server details from settings
        server_settings = settings.get('server')
        host = server_settings.get('host')
        port = server_settings.get('port')
        username = server_settings.get('username')
        password = server_settings.get('password')

        if not host or not port or not username or not password:
            logger.error("DATAPUSH: Server settings cannot be empty. Please check settings.json.")
            return False

        logger.info(f"DATAPUSH: Pushing files from {local_dir} to {remote_dir}")
        # Form the SCP command - IMPORTANT! sshpass required - install with "sudo apt-get install -y sshpass"
        scp_command = [
                        'sshpass',
                        '-p', password,
                        'scp',
                        '-o',
                        'StrictHostKeyChecking=no',
                        '-r',
                        local_dir,
                        f"{username}@{host}:{remote_dir}"
                        ]
        
        # Run the SCP command with subprocess
        subprocess.run(scp_command, check=True, timeout=30)
        
        return True

    except IOError:
        pass
    except subprocess.TimeoutExpired:
        logger.error("DATAPUSH: SCP operation timed out.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"DATAPUSH: Error occurred while pushing files: {str(e)}")
        logger.error("DATAPUSH: Server may not be reachable or the credentials are incorrect.")
        return False
    except Exception as e:
        logger.error(f"DATAPUSH: An error occurred: {str(e)}")
        return False
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def push_data(settings):
    """
    Push files from local directories to remote directories based on the settings.

    This function transfers files from local directories to corresponding remote directories
    specified in the settings. It checks for the presence of required settings, validates
    that both local and remote directories are defined, and then performs the file transfer
    operation.

    Args:
        settings (dict): A dictionary containing application settings.

    Returns:
        bool: True if the file transfer operation is successful for all directories,
              False otherwise.
    """
    has_errors = False

    try:
        # Check if all required settings are present
        if not check_required_settings(settings):
            return False

        # Get local and remote directories from settings
        local_directories = settings.get('local_directories')
        remote_directories = settings.get('server').get('remote_directories')

        if settings['server']['upload_all_data'] == 1: 
            for local_dir, remote_dir in zip(local_directories.values(), remote_directories.values()):
                if not push_files(local_dir, remote_dir, settings):
                    has_errors = True
        else:
            user_data_local = local_directories.get('user_data')
            user_data_local = {"user_data": user_data_local}
            user_data_remote = remote_directories.get('remote_user_data')
            user_data_remote = {"remote_user_data": user_data_remote}
            for local_dir, remote_dir in zip(user_data_local.values(), user_data_remote.values()):
                if not push_files(local_dir, remote_dir, settings):
                    has_errors = True
    
    except (OSError):
        pass
    except Exception:
        logger.error("DATAPUSH: failed to transfer")
        has_errors = True
    finally:
        if has_errors:
            return False
        # Return True only if all operations were successful
        return True
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def main():
    try:
        settings = ll.load_settings()
        if settings is None:
            logger.critical('DATAPUSH: Settings file corrupted.')
            sys.exit(1)
        
        host = settings.get('server').get('host')
        data_push_step = settings.get('server').get('data_push_step')
        start_time = time.time()
        
        while (1):
            current_time = time.time()
            elapsed_time = current_time - start_time
                    
            if elapsed_time >= (data_push_step * 60):
                serverIsAlive = ll.check_server_response(host)
                if serverIsAlive:
                    if not (push_data(settings)):
                        logger.warning("DATAPUSH: Cannot transfer files")
                    start_time = current_time
                else:
                    logger.warning("DATAPUSH: Server not answering")
            time.sleep(1)
            
    except Exception as e:
        logger.critical(f'DATAPUSH: Unknown error. {e}')
#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

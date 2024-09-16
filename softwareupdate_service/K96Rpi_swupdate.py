import sys
import zipfile
import os
import subprocess
import shutil
import paramiko
from datetime import datetime
import argparse
import signal

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

#------------------------------------------------------------------------------
def sigterm_handler(signum, frame):
    logger.critical(f'SOFTWARE UPDATE: Sigterm recieved:\n {signum}\n {frame}')

signal.signal(signal.SIGTERM, sigterm_handler)
#------------------------------------------------------------------------------

files = [f for f in os.listdir('locks') if f.endswith('-swupdate.lock')]
for file in files:
    file_path = os.path.join('locks', file)
    os.remove(file_path)

current_date = datetime.now().strftime("%Y%m%d")
logger = ll.setup_logger(f"{current_date}-swupdate.log")

#------------------------------------------------------------------------------
def list_local_files(settings):
    try:
        stdout = subprocess.run(['ls', settings['update_local_folder']], capture_output=True, text=True)
        
        if stdout.returncode != 0:
            return None
        
        file_list = stdout.read().decode('latin-1').splitlines()

        return file_list

    except Exception as e:
        logger.error(f"Error in list_files: {e}")
        raise
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def list_files(settings):
    try:
        transport = paramiko.Transport((settings["update_server_ip"], 22))
        transport.connect(username=settings["username"], password=settings["password"])

        ssh = paramiko.SSHClient()
        ssh._transport = transport

        command = f"dir {settings['update_remote_folder']}"
        stdin, stdout, stderr = ssh.exec_command(command)

        file_list = stdout.read().decode('latin-1').splitlines()

        ssh.close()
        transport.close()

        return file_list

    except Exception as e:
        logger.error(f"Error in list_files: {e}")
        raise
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def download_file(settings, filename):
    try:
        transport = paramiko.Transport((settings['update_server_ip'], 22))
        transport.connect(username=settings['username'], password=settings['password'])

        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_file_path = os.path.join(settings['update_remote_folder'], filename)
        local_file_path = os.path.join(settings['update_local_folder'], filename)

        if not os.path.exists(settings['update_local_folder']):
            os.makedirs(settings['update_local_folder'])

        sftp.get(remote_file_path, local_file_path)

        sftp.close()
        transport.close()

        logger.info(f"Downloaded: {local_file_path}")
    except Exception as e:
        logger.error(f"Error downloading {remote_file_path}: {e}")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def extract_zip(zip_file, destination):
    try:
        if not os.path.exists(destination):
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(destination)
            logger.info(f"Extracted {zip_file} to {destination}")
        else:
            logger.info(f"Folder already exists: {destination}")
    except Exception as e:
        logger.error(f"Error extracting {zip_file}: {e}")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def change_permissions(file_path, permissions):
    try:
        os.chmod(file_path, permissions)
        logger.info(f"Changed permissions of {file_path} to {permissions}")
        return 0
    except Exception as e:
        logger.error(f"Error changing permissions of {file_path}: {e}")
        return None
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def remove_update_files(*file_paths):
    try:
        for file_path in file_paths:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                logger.info(f"Removed: {file_path}")
            else:
                logger.info(f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error removing files: {e}")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def main():
    
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--sa_update', action='store_true', help='Standalone updates')
    args = parser.parse_args()
    
    settings = ll.load_settings()
    if settings is not None:
        update_settings = settings.get("update")
        
        service_stoped = False
    
        #Stop working services
        while not service_stoped:
            try:
                logger.info("SW UPDATE: Stoping services for update")
                subprocess.run(['bash', '-c', "sudo systemctl stop $(systemctl list-units --type=service --no-pager --all | grep 'K96Rpi*.service' | awk '{print $1}')"], check=True)
                logger.info("SW UPDATE: K96Rpi Services stopped")
                subprocess.run(['bash', '-c', "sudo systemctl stop $(systemctl list-units --type=timer --no-pager --all | grep 'K96Rpi.*.timer' | awk '{print $1}')"], check=True)
                logger.info("SW UPDATE: K96Rpi Timers stopped")
                service_stoped = True
            except subprocess.CalledProcessError as e:
                logger.error(f"SW UPDATE: Failed to stop services or timers: {e}, still trying")
                continue
    
        if args.sa_update:
            files = list_local_files(update_settings)
            if files is None:
                logger.critical("SW UPDATE: No updates. Exiting.")
                sys.exit(1)
        else:
            files = list_files(update_settings)
            if files is None:
                logger.critical("SW UPDATE: No updates. Exiting.")
                sys.exit(1)

        try:
            last_installed_update = datetime.strptime(update_settings["last_installed_update"], '%Y%m%d')

            filtered_files = []

            for file_info in files:
                if file_info.endswith('.zip'):
                    parts = file_info.split()
                    update_file_name = parts[-1]
                    check_file_name = parts[-1].split('.')
                    if check_file_name[0].isdigit():
                        file_date_obj = datetime.strptime(check_file_name[0], '%Y%m%d').date()
                        if file_date_obj > last_installed_update.date():
                            filtered_files.append(update_file_name)

            if not filtered_files:
                logger.info("SW UPDATE: No updates available")
            else:
                filtered_files.sort(key=lambda x: int(x.split('.')[0]))
                logger.info("SW UPDATE: Installing available updates")
                for file_info in filtered_files:
                    if not args.sa_update:
                        # download update
                        download_file(update_settings, file_info)

                    # extracting file
                    filename = file_info[:-4]
                    extraction_destination = f"{update_settings['update_local_folder']}{filename}_update"
                    extract_zip(f'{update_settings["update_local_folder"]}{file_info}', extraction_destination)

                    # changing right update.sh
                    update_script_path = os.path.join(extraction_destination, 'update.sh')
                    result = change_permissions(update_script_path, 0o777)
                    if result is None:
                        raise

                    # run update.sh
                    result = subprocess.run(['bash', update_script_path, extraction_destination], capture_output=True, text=True)

                    # check returncode of update.sh 
                    if result.returncode != 0:
                        logger.error(f"SW UPDATE: Error running {update_script_path}: {result.stderr}")
                        remove_update_files(os.path.join(update_settings['update_local_folder'], file_info), extraction_destination)
                        #subprocess.run(['sudo', 'reboot'])
                        sys.exit(1)

                    # change last_installed_update record in setting file
                    update_settings["last_installed_update"] = filename
                    ll.save_settings(settings)

                    # Delete update files
                    remove_update_files(os.path.join(update_settings['update_local_folder'], file_info), extraction_destination)

        except Exception as e:
            logger.error(f"SW UPDATE: Error in updates: {e}")

    else:
        logger.critical("SW UPDATE: Unable to load update_settings file. Exiting.")

    subprocess.run(['sudo', 'reboot'])

#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

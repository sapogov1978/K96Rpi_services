import os
import shutil
import statistics
import csv
import pytz
import platform
import signal
from datetime import datetime
import sys

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

current_date = datetime.now().strftime("%Y%m%d")
logger = ll.setup_logger(f"{current_date}-fsm.log")

#------------------------------------------------------------------------------
def clean_locks():
    files = [f for f in os.listdir('locks') if f.endswith('-fsm.lock')]
    for file in files:
        file_path = os.path.join('locks', file)
        os.remove(file_path)
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def sigterm_handler(signum, frame):
    logger.critical(f'FSM SERVICE: Sigterm recieved:\n {signum}\n {frame}')
    clean_locks()
#------------------------------------------------------------------------------

signal.signal(signal.SIGTERM, sigterm_handler)

clean_locks()

#------------------------------------------------------------------------------
def check_disk_space(directory):
    """
    Check the available free disk space based on contant of a directory.
    
    Args:
        directory (str): The path to the directory.
    
    Returns:
        free(int): The amount of free disk space in bytes or 0 in case of exception

    Raises:
        OSError: If an error occurs while checking the disk space.
    """
    
    try:
        total, used, free = shutil.disk_usage(directory)
        return free
    
    except OSError as e:
        logger.error(f"FSM: Error occurred while checking disk space: {str(e)}")
        return 0
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def delete_oldest_files(directory, num_files_to_delete):
    """
    This function deletes the specified number of oldest files in the given
    directory to free up space when the available disk space is low.
    
    Args:
        directory (str): The path to the directory containing the files to delete.
        num_files_to_delete (int): The number of oldest files to delete.
    
    Return:
        N/A
    
    Raises:
        OSError: If an error occurs while deleting files.
    """
    
    try:
        files = [(os.path.join(directory, filename), os.path.getmtime(os.path.join(directory, filename))) \
                for filename in os.listdir(directory) if os.path.isfile(os.path.join(directory, filename))]
        sorted_files = sorted(files, key=lambda x: x[1])
        for i in range(num_files_to_delete):
            if not sorted_files:
                break
            file_to_delete = sorted_files.pop(0)[0]
            os.remove(file_to_delete)
            logger.info(f"{file_to_delete} deleted by FSM due to lack of free space")
    
    except OSError as e:
        logger.error(f"FSM: Error occurred while deleting the oldest files: {str(e)}")
        pass
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def get_median_file_size(directory):
    """
    Get the median file size of files in a directory.

    This function calculates the median file size (in bytes) of the files in the specified
    directory. If the directory is empty or an error occurs, it returns 0.

    Args:
        directory (str): The path to the directory containing the files.

    Returns:
        int: The median file size in bytes or 0 in case of exception or empty folder
    """
    
    try:
        file_sizes = [os.path.getsize(os.path.join(directory, filename)) \
                    for filename in os.listdir(directory) if os.path.isfile(os.path.join(directory, filename))]
        return statistics.median(file_sizes) if file_sizes else 0

    except OSError as e:
        logger.error(f"FSM: Error occurred while getting median file size: {str(e)}")
        return 0
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def monitor_folders(folder_settings):
    """
    Monitor specified folders for free space and delete files as needed.
    
    This function monitors the specified folders for free space and ensures that the
    available free space is greater than or equal to the maximum median file size among
    the monitored folders. If the available space is less than the maximum median file size,
    the function deletes the oldest files in the folders until enough free space is available.
    
    Args:
        folder_settings (dict): A dictionary mapping folder names to their paths.
    
    Returns:
        N/A
    """
    
    max_median_size = 0
    for folder_path in folder_settings.values():
        median_size = get_median_file_size(folder_path)
        max_median_size += median_size
        logger.info(f"Monitoring folder: {folder_path}, Median file size: {median_size:.2f} bytes")

    for folder_path in folder_settings.values():
        free_space = check_disk_space(folder_path)
        while free_space < max_median_size:
            num_files_to_delete = 1
            delete_oldest_files(folder_path, num_files_to_delete)
            free_space = check_disk_space(folder_path)

    logger.info(f"Total target free space: {max_median_size:.2f} bytes")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def write_header_to_raw_data_csv(csv_filename, registers, arduino_registers):
    """
    Writes the header row to a Raw Data CSV file based on the provided registers.
    
    This function constructs a header row for a Raw Data CSV file based on the 
    provided registers. It includes "Timestamp" and "Location" columns along 
    with columns for each register's measurement names.
    If the CSV file does not exist or is empty, it creates a file and adds 
    the header row.
    
    Args:
        csv_filename (str): The name of the CSV file to write the header to.
        registers (dict): A dictionary containing information about registers.
    
    Returns:
        None
    
    Raises:
        Exception: If an error occurs while writing the header.
    """
    
    header = ["Timestamp", "Location"]
    for register_name, register_data in registers.items(): 
        measurement_name = register_data.get("measurement")
        header.append(measurement_name)
    for register_name, register_data in arduino_registers.items(): 
        measurement_name = register_data.get("measurement")
        header.append(measurement_name)
    
    ll.acquire_lock("rawdata", "fsm")
    try:
        # Check if the file exists and if it is empty
        file_exists = os.path.exists(csv_filename)
        if file_exists:
            with open(csv_filename, 'r') as f:
                file_exists = f.readline().strip() != ""
        if not file_exists:
            with open(csv_filename, 'a', newline='') as csvfile:
                csv_writer = csv.writer(csvfile, quoting=csv.QUOTE_NONE)
                csv_writer.writerow(header)
        ll.release_lock("rawdata", "fsm")
    
    except Exception as e:
        logger.error(f"FSM(write_header_to_csv): Error writing Raw Data CSV header: {str(e)}")
        pass
    finally:
        ll.release_lock("rawdata", "fsm")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def get_utc_offset(settings):
    """
    Get the current UTC offset in the format 'UTC+/-X' where X is the offset in hours.
    
    Args:
        settings (dict): A dictionary containing timezone information.
    
    Returns:
        str: The UTC offset string.
    """
    
    timezone_name = settings.get("timezone")

    timezone = pytz.timezone(timezone_name)
    
    current_time = datetime.now(timezone)
    
    offset_minutes = current_time.utcoffset().total_seconds() / 60
    
    if offset_minutes == 0:
        utc_offset = 'UTC'
    elif offset_minutes > 0:
        utc_offset = f'UTC+{int(offset_minutes / 60)}'
    else:
        utc_offset = f'UTC-{int(offset_minutes / 60)}'

    return utc_offset
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def write_header_to_user_data_csv(settings, csv_filename, registers):
    """
    Write the header to a User Data CSV file based on settings and registers.
    
    This function writes the header to a User Data CSV file based on the provided settings
    and registers information. It includes the box ID, datetime, location, UTC offset,
    human-readable names, units, and an "Alarme" column.
    
    Args:
        settings (dict): A dictionary containing configuration settings.
        csv_filename (str): The CSV file name.
        registers (dict): A dictionary of registers with their data.
    
    Returns:
        N/A
    """

    sensor_id = settings.get('box').get('sensor_id')
    utc_offset = get_utc_offset(settings)
    
    header1 = [f'BOX{sensor_id}']
    header2 = ["Datetime", "Location"]
    header3 = [utc_offset, "N/A"]

    filtered_registers = {name: data for name, data in registers.items() if data.get("type") == "meas"}

    for register_name, register_data in filtered_registers.items():
        human_readable_name = register_data.get("human_readable_name")
        units = register_data.get("units")
        header2.append(human_readable_name)
        header3.append(units)
    
    header2.append("Alarme")
    header3.append("Num")

    ll.acquire_lock("userdata", "fsm")
    try:
        # Check if the file exists and if it is empty
        file_exists = os.path.exists(csv_filename)
        if file_exists:
            with open(csv_filename, 'r') as f:
                file_exists = f.readline().strip() != ""

        if not file_exists:
            with open(csv_filename, 'a', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(header1)
                csv_writer.writerow(header2)
                csv_writer.writerow(header3)
    except Exception as e:
        logger.error(f"FSM(write_header_to_csv): Error writing User Data CSV header: {str(e)}")
        pass
    finally:
        ll.release_lock("userdata", "fsm")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def run_fsm(settings):
    """
    Run the File System Management (FSM) for data processing.
    
    This function runs the FSM for file system management related to data processing. 
    It creates necessary directories, files, and headers for raw data and user data. 
    It also monitors folders for disk space, and handles exceptions and manual interruptions.
    
    Args:
        settings (dict): A dictionary containing configuration settings.
    
    Returns:
        N/A
    """
    
    folder_settings = settings.get('local_directories')
    
    logs_dir = folder_settings.get('logs')
    raw_data_dir = folder_settings.get('raw_data')
    user_data_dir = folder_settings.get('user_data')
    
    box_settings = settings.get('box')
    # sensor_address = box_settings.get('sensor_address')
    # sensor_id_address = box_settings.get('sensor_id_address')
    # function = box_settings.get('modbus_functions').get('READ_EPROM')
    
    sensor_id = box_settings.get('sensor_id')
    # ll.acquire_lock("port", "fsm")
    # comm_port = sde.open_port(settings)
    # if comm_port is not None:
    #     sensor_id_raw = sde.data_exchange(settings, comm_port, sensor_address, function, sensor_id_address, 4)
    #     if sensor_id_raw is not None:
    #         sensor_id = sensor_id_raw[3:-2]
    #         if sensor_id is not None:
    #             sensor_id = int.from_bytes(sensor_id, byteorder='big', signed=False)
    #             settings['box']['sensor_id'] = sensor_id
    #     comm_port.close()
    # else:
    #     logger.critical("FSM: Cannot get sensor ID, comm port not opened")
    #     settings['box']['sensor_id'] = sensor_id
    # ll.release_lock("port", "fsm")
    

    loc_string = platform.node()
    if loc_string is None:
            loc_string = "00000000"
    
    user_data_data_step = box_settings.get('user_data_data_step')
    last_user_data_file_id = box_settings.get('last_user_data_file_id')

    # Ensure directories exist or create them
    for directory in [logs_dir, raw_data_dir, user_data_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    current_date = datetime.now().strftime("%Y%m%d")
    current_time = datetime.now().strftime("%H%M%S")
    new_user_data_file_id = int(last_user_data_file_id) + 1
    settings['box']['last_user_data_file_id'] = new_user_data_file_id
    
    log_file = os.path.join(logs_dir, f"{current_date}_{loc_string}_{sensor_id}_event.log")
    raw_data_file = os.path.join(raw_data_dir, f"{current_date}_{loc_string}_{sensor_id}_raw_data.csv")
    user_data_file = os.path.join(user_data_dir, f"NPC_{loc_string}_BOX{sensor_id}_{user_data_data_step}_{current_date}{current_time}_{new_user_data_file_id}.csv")
    sensor_data_file = os.path.join(raw_data_dir, f"{current_date}_{loc_string}_{sensor_id}_sensor_data.txt")

    try:
        monitor_folders(folder_settings)

        for file_path in [log_file, raw_data_file, user_data_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'a'):
                    pass

        settings['local_files']['logs'] = log_file
        settings['local_files']['raw_data'] = raw_data_file
        settings['local_files']['user_data'] = user_data_file
        settings['local_files']['sensor_data'] = sensor_data_file

        registers = settings.get('raw_data').get('registers')
        arduino_registers = settings.get('raw_data').get('arduino_registers')
        if not registers or not arduino_registers:
            logger.critical("FSM: No raw data registers specified in the settings")

        write_header_to_raw_data_csv(raw_data_file, registers, arduino_registers)
        write_header_to_user_data_csv(settings, user_data_file, registers)
        
    except Exception as e:
        logger.critical(f"FSM: An error occurred in run_fsm: {str(e)}")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def main():
    """
    Execute the File System Management (FSM) routine.
    
    This function performs the File System Management (FSM) routine, which includes running FSM tasks,
    setting up logging, retrieving sensor information, and updating settings.
    
    Returns:
        N/A
    """
    try:
        settings = ll.load_settings()
        if settings is not None:
            run_fsm(settings)
            settings['last_known_date'] = int(datetime.now().strftime('%Y%m%d'))
            #settings['daily_routeen_complete'] = 1
            save_settings = ll.save_settings(settings)
            if save_settings != 0:
                if save_settings != 1:
                    logger.critical(f"Error while saving settings. {save_settings}")
                else:
                    logger.critical("Error while saving settings, settings file not found")
            else:
                logger.info("Settings updated with new pathes")       
        else:
            logger.critical(f"FSM: Settings file corrupted")
    
    except Exception as e:
            logger.critical(f"FSM(fsm_routeen): Error occurred in fsm.py: {str(e)}")
    finally:
        ll.release_lock("port", "fsm")
#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

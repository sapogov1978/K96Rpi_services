import datetime
import platform
import subprocess
import os
import sys
import signal

from datetime import datetime

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

#------------------------------------------------------------------------------
def sigterm_handler(signum, frame):
    logger.critical(f'SENSOR INFO SERVICE: Sigterm recieved:\n {signum}\n {frame}')

signal.signal(signal.SIGTERM, sigterm_handler)
#------------------------------------------------------------------------------

files = [f for f in os.listdir('locks') if f.endswith('-sensorinfo.lock')]
for file in files:
    file_path = os.path.join('locks', file)
    os.remove(file_path)

current_date = datetime.now().strftime("%Y%m%d")
logger = ll.setup_logger(f"{current_date}-sensor_info.log")

#------------------------------------------------------------------------------
def get_sensor_info(settings, comm_port):
    
    """
    Retrieve sensor information and save it to a file.
    
    This function retrieves various sensor-related information and saves it to a file. 
    The information includes sensor box, arduino and Raspberry Pi details, 
    EPROM and RAM statuses, and more.
    
    Args:
        settings (dict): A dictionary containing configuration settings.
        comm_port (str): The communication port used for sensor data retrieval.
    
    Returns:
        N/A
    """

    current_date = datetime.datetime.now().date()
    current_time = datetime.datetime.now().time()
    
    sensor_info_file = settings.get('local_files').get('sensor_data')
    arduino_address = settings.get('box').get('arduino_address')
    sensor_address = settings.get('box').get('sensor_address')

    Integrated_Box_Type_ID = None
    
    Integrated_Box_ID = settings.get('box').get('id')
    settings['sensor_info']['Integrated_Box_ID'] = Integrated_Box_ID
    
    Raspberry_Pi_serial_number = subprocess.check_output("cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2", shell=True).strip()
    if Raspberry_Pi_serial_number is not None:
        serial_num = Raspberry_Pi_serial_number.decode("utf-8")
        settings['sensor_info']['Raspberry_Pi_CPU_SN'] = serial_num
    else:
        settings['sensor_info']['Raspberry_Pi_CPU_SN'] = None
    
    Raspberry_Pi_OS_version = None
    Raspberry_Pi_OS_version = platform.platform()
    settings['sensor_info']['Raspberry_Pi_OS_version'] = Raspberry_Pi_OS_version

    Raspberry_Pi_software_version = settings.get("sensor_info").get('Raspberry_Pi_software_version')

    Location_string_of_the_Integrated_box = platform.node()
    if Location_string_of_the_Integrated_box is None:
        Location_string_of_the_Integrated_box = "00000000"
    
    data_dict = {}
        
    settings_EPROM = settings.get('sensor_info').get('EPROM_statuses')
    function = settings.get('box').get('modbus_functions').get('READ_EPROM')

    for EPROM_status_name in settings_EPROM.keys():
        address = settings_EPROM[EPROM_status_name].get('address')
        bytes_qty = settings_EPROM[EPROM_status_name].get('data_length_bytes')
        keep_in = settings_EPROM[EPROM_status_name].get('keep_in')
        data_type = settings_EPROM[EPROM_status_name].get('data_type')
        
        if comm_port is not None:
            raw_response = sde.data_exchange(settings, comm_port, sensor_address, function, address, bytes_qty)
        else:
            raw_response = None
        
        if raw_response is not None:
            trunc_response = raw_response[3:-2]
            if not trunc_response:
                data_dict[EPROM_status_name] = 'Incorrect Answer'
            else:
                if keep_in == "hex":
                    hex_response = ''.join(format(byte, "02X") for byte in trunc_response)
                    data_dict[EPROM_status_name] = f"0x{hex_response}"
                elif keep_in == "decimal":
                    if data_type == "unsigned":
                        data_dict[EPROM_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=False)
                    else:
                        data_dict[EPROM_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=True)
        else:
            data_dict[EPROM_status_name] = 'No Answer'

    settings_RAM = settings.get('sensor_info').get('RAM_statuses')
    function = settings.get('box').get('modbus_functions').get('READ_RAM')
    
    for RAM_status_name in settings_RAM.keys():
        address = settings_RAM[RAM_status_name].get('address')
        bytes_qty = settings_RAM[RAM_status_name].get('data_length_bytes')
        keep_in = settings_RAM[RAM_status_name].get('keep_in')
        data_type = settings_RAM[RAM_status_name].get('data_type')

        if comm_port is not None:
            raw_response = sde.data_exchange(settings, comm_port, sensor_address, function, address, bytes_qty)
        else:
            raw_response = None
                
        if raw_response is not None:
            trunc_response = raw_response[3:-2]
            if not trunc_response:
                data_dict[RAM_status_name] = 'Incorrect Answer'
            else:
                if keep_in == "hex":
                    hex_response = ''.join(format(byte, "02X") for byte in trunc_response)
                    data_dict[RAM_status_name] = f"0x{hex_response}" 
                elif keep_in == "decimal":
                    if data_type == "unsigned":
                        data_dict[RAM_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=False)
                    else:
                        data_dict[RAM_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=True)
        else:
            data_dict[RAM_status_name] = 'No Answer'

    settings_ARDUINO = settings.get('sensor_info').get('Arduino_Statuses')
    
    for ARDUINO_status_name in settings_ARDUINO.keys():
        address = settings_ARDUINO[ARDUINO_status_name].get('address')
        bytes_qty = settings_ARDUINO[ARDUINO_status_name].get('data_length_bytes')
        keep_in = settings_ARDUINO[ARDUINO_status_name].get('keep_in')
        data_type = settings_ARDUINO[ARDUINO_status_name].get('data_type')
        register_type = settings_ARDUINO[ARDUINO_status_name].get('register_type', '')
        if register_type == 'IR':
            function = settings.get('box').get('modbus_functions').get('READ_MULTIPLE_IR')
        else:
            function = settings.get('box').get('modbus_functions').get('READ_MULTIPLE_HR')
        
        if comm_port is not None:
            raw_response = sde.data_exchange(settings, comm_port, arduino_address, function, address, bytes_qty)
        else:
            raw_response = None
            
        if raw_response is not None:
            trunc_response = raw_response[3:-2]
            if not trunc_response:
                data_dict[ARDUINO_status_name] = 'Incorrect Answer'
            else:
                if keep_in == "hex":
                    # Convert the bytes to hex string representation
                    hex_response = ''.join(format(byte, "02X") for byte in trunc_response)
                    data_dict[ARDUINO_status_name] = f"0x{hex_response}"  # Store as hex string
                elif keep_in == "decimal":
                    if data_type == "unsigned":
                        data_dict[ARDUINO_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=False)
                    else:
                        data_dict[ARDUINO_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=True)
        else:
            data_dict[ARDUINO_status_name] = 'No Answer'

    # Using data_dict for sensor info file
    record = f"Date: {current_date}, Time: {current_time}\n"
    record += f"Integrated_Box_Type_ID: {Integrated_Box_Type_ID}\n"
    record += f"Integrated_Box_ID: {Integrated_Box_ID}\n"
    record += f"Raspberry_Pi_CPU_SN: {Raspberry_Pi_serial_number}\n"
    record += f"Raspberry_Pi_OS_version: {Raspberry_Pi_OS_version}\n"
    record += f"Raspberry_Pi_software_version: {Raspberry_Pi_software_version}\n"
    record += f"Location_string_of_the_Integrated_box: {Location_string_of_the_Integrated_box}\n"

    for attribute, value in data_dict.items():
        record += f"{attribute}: {value}\n"
    
    # Save info to the file
    try:
        with open(sensor_info_file, 'w') as file:
            file.write(record)
            logger.info('Sensor Data file updated')
    except (OSError, IOError) as e:
        logger.error(f'GET_SENSOR_INFO: Cannot write to {sensor_info_file}')
        pass
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def main():
    comm_port = None
    settings = ll.load_settings()
    if settings is None:
        logger.critical('SENSOR_INFO: Settings file cannot be read.')
        sys.exit(1)
    
    try:
        ll.acquire_lock("port", "sensorinfo")
        comm_port = sde.open_port(settings)
        get_sensor_info(settings, comm_port)
        if comm_port is not None:
            comm_port.close()
            comm_port = None
        ll.release_lock("port", "sensorinfo")

    except Exception as e:
        logger.critical(f"SENSOR_INFO: An error occurred: {str(e)}")

    finally:
        ll.release_lock("port", "sensorinfo")
#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

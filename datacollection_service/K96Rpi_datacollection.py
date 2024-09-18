import sys
import os
import signal
import datetime
import copy
import csv

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

logger_critical = ll.setup_logger("data_collection_fault.log")

#------------------------------------------------------------------------------
def sigterm_handler(signum, frame):
    logger_critical.critical(f'DATACOLLECTION SERVICE: Sigterm recieved:\n {signum}\n {frame}')

signal.signal(signal.SIGTERM, sigterm_handler)
#------------------------------------------------------------------------------

files = [f for f in os.listdir('locks') if f.endswith('-datacollection.lock')]
for file in files:
    file_path = os.path.join('locks', file)
    os.remove(file_path)

#------------------------------------------------------------------------------
def write_calc_data_to_file(settings, calcullation_buffer, logger):
    """
    Write raw data from a data buffer to a CSV file.

    """
    calc_data_filename = settings.get('local_files').get('calc_data')
    try:
        ll.acquire_lock("calcdata", "datacollection")
        with open(calc_data_filename, 'a', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            for data_dict in calcullation_buffer:
                csv_writer.writerow(data_dict.values())
    except Exception as e:
        logger.error(f"RDC: Error writing calc data to file: {str(e)}")
    finally:
        ll.release_lock("calcdata", "datacollection")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def write_data_to_file(settings, data_buffer, logger):
    """
    Write raw data from a data buffer to a CSV file.

    """
    raw_data_filename = settings.get('local_files').get('raw_data')
    try:
        ll.acquire_lock("rawdata", "datacollection")
        with open(raw_data_filename, 'a', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            for data_dict in data_buffer:
                csv_writer.writerow(data_dict.values())
    except Exception as e:
        logger.error(f"RDC: Error writing raw data to file: {str(e)}")
    finally:
        ll.release_lock("rawdata", "datacollection")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def read_raw_data(settings, comm_port, data_buffer, accumulation_complete_flag, calculation_buffer, logger):
    """
    Read and process raw data from a sensor and manage data accumulation.

    """
    timeframe = settings.get('box').get('user_data_data_step')
    if timeframe is None:
        timeframe = 900
    else:
        timeframe = timeframe * 60
    
    registers = settings.get('raw_data').get('registers')
    arduino_registers = settings.get('raw_data').get('arduino_registers')
    sensor_address = settings.get('box').get('sensor_address')
    arduino_address = settings.get('box').get('arduino_address')
    function = settings.get('box').get('modbus_functions').get('READ_RAM')
    last_known_date = settings.get('last_known_date')

    if not registers:
        logger.error("RDC: No registers specified in the settings")
        return

    data_dict = {} 

    data_dict['Timestamp'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    data_dict['Location'] = settings.get('sensor_info').get('Location_string_of_the_Integrated_box')

    for RAM_status_name, value in registers.items():
            address = value.get('address')
            bytes_qty = value.get('data_length_bytes')
            keep_in = value.get('keep_in')
            data_type = value.get('data_type')

            raw_response = sde.data_exchange(settings, comm_port, sensor_address, function, address, bytes_qty)
    
            if raw_response is not None:
                trunc_response = raw_response[3:-2]
                if not trunc_response:
                    data_dict[RAM_status_name] = '-999.99'
                else:
                    if keep_in == "hex":
                        # Convert the bytes to hex string representation
                        hex_response = ''.join(format(byte, "02X") for byte in trunc_response)
                        data_dict[RAM_status_name] = f"0x{hex_response}"  # Store as hex string
                    elif keep_in == "decimal":
                        if data_type == "unsigned":
                            data_dict[RAM_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=False)
                        else:
                            data_dict[RAM_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=True)
            else:
                data_dict[RAM_status_name] = '-999.99'

    for arduino_status_name, ar_value in arduino_registers.items():
            address = ar_value.get('address')
            bytes_qty = ar_value.get('data_length_bytes')
            keep_in = ar_value.get('keep_in')
            data_type = ar_value.get('data_type')
            register_type = ar_value.get('register_type')
            if register_type == 'IR':
                function = settings.get('box').get('modbus_functions').get('READ_MULTIPLE_IR')
            else:
                function = settings.get('box').get('modbus_functions').get('READ_MULTIPLE_HR')

            raw_response = sde.data_exchange(settings, comm_port, arduino_address, function, address, bytes_qty)
    
            if raw_response is not None:
                trunc_response = raw_response[3:-2]
                if not trunc_response:
                    data_dict[arduino_status_name] = '-999.99'
                else:
                    if keep_in == "hex":
                        # Convert the bytes to hex string representation
                        hex_response = ''.join(format(byte, "02X") for byte in trunc_response)
                        data_dict[arduino_status_name] = f"0x{hex_response}"  # Store as hex string
                    elif keep_in == "decimal":
                        if data_type == "unsigned":
                            data_dict[arduino_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=False)
                        else:
                            data_dict[arduino_status_name] = int.from_bytes(trunc_response, byteorder='big', signed=True)
            else:
                data_dict[arduino_status_name] = '-999.99'

    data_buffer.append(data_dict)
        
    timestamp_str = data_buffer[0]['Timestamp']
    timestamp_obj = datetime.datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
    current_time = datetime.datetime.now()
    time_difference = current_time - timestamp_obj
    time_difference_seconds = time_difference.total_seconds()

    if len(data_buffer) > 0 and (time_difference_seconds >= timeframe or int(current_time.strftime('%Y%m%d')) != last_known_date):
        calculation_buffer = copy.deepcopy(data_buffer)
        accumulation_complete_flag = True
        write_data_to_file(settings, data_buffer, logger)
        data_buffer.clear()
        return accumulation_complete_flag, calculation_buffer, data_buffer
    else:
        return 0, 0, data_buffer
    
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def settings_was_modified(settings_path, last_settings_mtime):
    try:
        current_mtime = os.path.getmtime(settings_path)
        if current_mtime > last_settings_mtime:
            return True, current_mtime
        else:
            return False, last_settings_mtime
    except FileNotFoundError:
        return False, last_settings_mtime
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def main():
    comm_port = None
    data_buffer = []
    calculation_buffer = []
    accumulation_complete_flag = False

    try:
        settings = ll.load_settings()
        if settings is not None:
            last_settings_mtime = 0
        
            while (1):
                was_modified, last_settings_mtime = settings_was_modified('settings.json', last_settings_mtime)
                if was_modified:
                    settings = ll.load_settings()
                    log_file = settings.get('local_files').get('logs')
                    log_file = log_file.split('/')[-1]
                    logger = ll.setup_logger(log_file)
                
                ll.acquire_lock("port", "datacollection")
                comm_port = sde.open_port(settings)
                if comm_port is not None:
                    accumulation_complete_flag, calculation_buffer, data_buffer = read_raw_data(settings, comm_port, data_buffer, accumulation_complete_flag, calculation_buffer, logger)
                    comm_port.close()
                    comm_port = None
                    ll.release_lock("port", "datacollection")
                    if accumulation_complete_flag:
                        write_calc_data_to_file(settings, calculation_buffer, logger)
                        accumulation_complete_flag = False
                        calculation_buffer.clear()
                else:
                    logger.critical("RDC: Port is not oppened")
                    ll.release_lock("port", "datacollection")
        else:
            logger.critical('RDC: Settings file corrupted.')
            sys.exit(1)

    except Exception as e:
        print(e)
    finally:
        ll.release_lock("port", "datacollection")

if __name__ == "__main__":
    main()

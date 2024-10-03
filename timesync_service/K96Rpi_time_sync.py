import sys
import os
import pytz
import subprocess
import datetime
import signal

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

current_date = datetime.datetime.now().strftime("%Y%m%d")
logger = ll.setup_logger(f"{current_date}-time_sync.log")

#------------------------------------------------------------------------------
def sigterm_handler(signum, frame):
    logger.critical(f'TIME SYNC SERVICE: Sigterm recieved:\n {signum}\n {frame}')
#------------------------------------------------------------------------------

signal.signal(signal.SIGTERM, sigterm_handler)

files = [f for f in os.listdir('locks') if f.endswith('-timesync.lock')]
for file in files:
    file_path = os.path.join('locks', file)
    os.remove(file_path)

#------------------------------------------------------------------------------
def update_RTC_time(settings, comm_port, server_datetime_24h, arduino_address, time_register_address):
    write_time = settings.get('box').get('modbus_functions').get('WRITE_MULTIPLE_HR')

    unix_time = int(server_datetime_24h.timestamp())
    unix_time_to_RTC = hex(unix_time)
        
    write_to_RTC = sde.data_exchange(settings, comm_port, arduino_address, write_time, time_register_address, 4, unix_time_to_RTC)
    
    if write_to_RTC is not None:
        logger.info("TIMESYNC: RTC time updated to server time")
    else:
        logger.critical("TIMESYNC: Unable to update RTC time")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def sync_with_RTC(settings, comm_port, arduino_address, time_register_address):
    read_time = settings.get('box').get('modbus_functions').get('READ_MULTIPLE_HR')
    values = sde.data_exchange(settings, comm_port, arduino_address, read_time, time_register_address, 2)

    if values is None or len(values[3:-2]) != 2:
        logger.fatal("TIMESYNC: Error reading registers")
        return None

    unixtime = values[3:-2]
    value1 = int.from_bytes(unixtime[:2], 'big')
    value2 = int.from_bytes(unixtime[2:], 'big')
    timestamp = datetime.datetime.fromtimestamp((value1 << 16) | value2, tz=pytz.utc)
    synchronized_time = timestamp#.astimezone(pytz.timezone(t_zone))
    return synchronized_time
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def sync_with_server(settings, host):
    username = settings.get('server').get('username')
    password = settings.get('server').get('password')
        
    powershell_command = '(Get-Date).ToUniversalTime().ToString(\\\"yyyy-MM-dd HH:mm:ss\\\")'
    ssh_command = f"sshpass -p {password} ssh -o StrictHostKeyChecking=no {username}@{host} 'powershell -Command {powershell_command}'"
    result = subprocess.run(ssh_command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        result = result.stdout.strip()
            
        logger.info(f"TIMESYNC: Server UTC time is: {result}")
        server_datetime_24h = datetime.datetime.strptime(result, "%Y-%m-%d %H:%M:%S")
        #utc_time = pytz.utc.localize(server_datetime_24h)
        #synchronized_time = utc_time.astimezone(pytz.timezone(t_zone))
        #synchronized_time = server_datetime_24h #.astimezone(pytz.timezone(t_zone))
        return server_datetime_24h
    else:
        logger.critical("TIMESYNC: server gettime returned an error")
        return None
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def synchronize_time(settings, comm_port):
    """
    Synchronize the system time with an external device's timestamp.
    
    This function reads the timestamp from an external device using Modbus communication and synchronizes the system
    time to match the received timestamp. It takes configuration settings and the communication port as inputs.
    The function returns a status code (999 for success, None for an error).
    
    Args:
        settings (dict): A dictionary containing configuration settings.
        comm_port (str): The communication port for the device.
    
    Returns:
        int: A status code (999 indicates success, None indicates an error).
    """
    
    arduino_address = settings.get('box').get('arduino_address')
    time_register_address = '0x0010'
    host = settings.get('server').get('host')
    #t_zone = settings.get('timezone')

    serverIsAlive = ll.check_server_response(host)

    if serverIsAlive:
        logger.info("TIMESYNC: Timesource - server")
        synchronized_time = sync_with_server(settings, host)
        if synchronized_time is not None:
            update_RTC_time(settings, comm_port, synchronized_time, arduino_address, time_register_address)
            logger.info("TIMESYNC: Arduino RTC time updated")
        else:
            logger.info("TIMESYNC: Timesource - arduino RTC")
            synchronized_time = sync_with_RTC(settings, comm_port, arduino_address, time_register_address)
    else:
        logger.warning("TIMESYNC: Server is not answering")
        logger.info("TIMESYNC: Timesource - arduino RTC")
        synchronized_time = sync_with_RTC(settings, comm_port, arduino_address, time_register_address)
    
    if synchronized_time is not None:
        formatted_time = synchronized_time.strftime('%Y-%m-%d %H:%M:%S')

        try:
            command = ["sudo", "date", "-u", "-s", formatted_time]
            subprocess.run(command, check=True)
            logger.info(f"TIMESYNC: Synchronized UTC system time to: {formatted_time}")
            return True
        except subprocess.CalledProcessError as e:
            logger.critical(f"TIMESYNC: Error setting system time: {str(e)}")
            return None
    else:
        logger.critical("TIMESYNC: No timesource available")
        return None
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def main():
    comm_port = None
    try:
        settings = ll.load_settings()
        if settings is None:
            logger.critical('TIMESYNC: Settings file corrupted.')
            sys.exit(1)
        
        ll.acquire_lock("port", "timesync")
        comm_port = sde.open_port(settings)
        if comm_port is not None:
            time_sync_complete = synchronize_time(settings, comm_port)
            if not time_sync_complete:
                logger.critical('TIMESYNC: Cannot sync the time.')
            else:
                logger.info("TIMESYNC: Time synchronization completed successfully.")
            comm_port.close()
            comm_port = None
        else:
            logger.critical('TIMESYNC: Finised with error. Port not open')
        ll.release_lock("port", "timesync")

    except Exception as e:
        logger.critical(f'TIMESYNC: Unknown error. {e}')
#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

import serial.tools.list_ports
import os
import sys
import signal
import datetime

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

#------------------------------------------------------------------------------
def sigterm_handler(signum, frame):
    logger.critical(f'USB CONNECTION SERVICE: Sigterm recieved:\n {signum}\n {frame}')

signal.signal(signal.SIGTERM, sigterm_handler)
#------------------------------------------------------------------------------

files = [f for f in os.listdir('locks') if f.endswith('-usb.lock')]
for file in files:
    file_path = os.path.join('locks', file)
    os.remove(file_path)

current_date = datetime.datetime.now().strftime("%Y%m%d")
logger = ll.setup_logger(f"{current_date}-usb.log")

#------------------------------------------------------------------------------
def find_usb_port(box_id):
    """
    Find the USB port associated with a specific serial number.

    This function iterates through the available COM ports and checks if the specified box_id
    is present in the serial number of each port. If a match is found, it returns the corresponding
    port device name; otherwise, it returns None.

    Args:
        box_id (str): The serial number of the target device.

    Returns:
        str or None: The device name of the USB port associated with the specified box_id,
        or None if no matching port is found.
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if box_id in port.serial_number:
            return port.device
    return None
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# initial search for device
def main():
    settings = ll.load_settings()
    
    if settings is not None:
        box_settings = settings.get('box') 
        box_id = box_settings.get('id')
        tries = box_settings.get('tries')
        sensor_id_old = box_settings.get('sensor_id')
        sensor_id_new = None
        sensor_id_address = box_settings.get('sensor_id_address')
        sensor_address = box_settings.get('sensor_address')
        function = box_settings.get('modbus_functions').get('READ_EPROM')
        comm_port = None

        while tries:
            port = find_usb_port(box_id)
            if port is not None:
                if settings['box']['port'] != port:
                    settings['box']['port'] = port
                    logger.info(f'USB CONNECTION SERVICE: Device was found on {port}')
                    
                ll.acquire_lock("port", "usb")
                comm_port = sde.open_port(settings)
                if comm_port is not None:
                    sensor_id_raw = sde.data_exchange(settings, comm_port, sensor_address, function, sensor_id_address, 4)
                    if sensor_id_raw is not None:
                        sensor_id_new = sensor_id_raw[3:-2]
                        if sensor_id_new is not None:
                            sensor_id_new = int.from_bytes(sensor_id_new, byteorder='big', signed=False)
                            if sensor_id_new != sensor_id_old:
                                settings['box']['sensor_id'] = sensor_id_new
                                logger.info(f'USB CONNECTION SERVICE: Sensor ID updated: {sensor_id_new}')
                        else:
                            logger.error(f'USB CONNECTION SERVICE: Incorrect answer from sensor {sensor_id_raw}')
                    comm_port.close()
                    comm_port = None
                else:
                    logger.critical("USB CONNECTION SERVICE: Cannot get sensor ID, comm port not opened")
                ll.release_lock("port", "usb")
                    
                ll.save_settings(settings)
                break
            else:
                tries -= 1
        if tries == 0:
            logger.critical('USB CONNECTION SERVICE: Device was not found')
#------------------------------------------------------------------------------


if __name__ == "__main__":
    main()

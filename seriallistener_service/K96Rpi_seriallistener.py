import time
import RPi.GPIO as GPIO
import threading
import subprocess
import serial
import time
from datetime import datetime
import sys
import os
import signal

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

#------------------------------------------------------------------------------
def sigterm_handler(signum, frame):
    logger.critical(f'SERIAL PORT LISTENER: Sigterm recieved:\n {signum}\n {frame}')

signal.signal(signal.SIGTERM, sigterm_handler)
#------------------------------------------------------------------------------

files = [f for f in os.listdir('locks') if f.endswith('-seriallistener.lock')]
for file in files:
    file_path = os.path.join('locks', file)
    os.remove(file_path)

current_date = datetime.now().strftime("%Y%m%d")
logger = ll.setup_logger(f"{current_date}-seriallistener.log")

#------------------------------------------------------------------------------
def calibration():
    """
    Perform calibration using serial communication between Raspberry Pi and a sensor box.

    Returns:
        None
    """
    ser_rpi = None
    ser_sensorbox = None
    
    settings = ll.load_settings()
    if settings is not None:
        rpi_serial_port = settings.get('rpi_serial_port')
        sensorbox_serial_port = settings.get('box').get('port')
        baudrate = settings.get('box').get('baudrate')
        service_stoped = False
    
        #Stop workink services before callibration
        while not service_stoped:
            try:
                logger.info("SERIAL PORT LISTENER: Calibration started")
                subprocess.run(['bash', '-c', "sudo systemctl stop $(systemctl list-units --type=service --no-pager --all | grep 'K96Rpi*.service' | awk '{print $1}')"], check=True)
                logger.info("SERIAL PORT LISTENER: K96Rpi Services stopped")
                subprocess.run(['bash', '-c', "sudo systemctl stop $(systemctl list-units --type=timer --no-pager --all | grep 'K96Rpi.*.timer' | awk '{print $1}')"], check=True)
                logger.info("SERIAL PORT LISTENER: K96Rpi Timers stopped")
                service_stoped = True
            except subprocess.CalledProcessError as e:
                logger.error(f"SERIAL PORT LISTENER: Failed to stop services or timers: {e}, still trying")
                continue
                
        #Open RPi serial port
        try:
            ser_rpi = serial.Serial(
                rpi_serial_port,
                baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=.1
            )
        except serial.SerialException as e:
            logger.critical(f'SERIAL PORT LISTENER: RPI serial port could not be opened: {e}')
            pass
            
        #Open K96 serial port
        try:
            ser_sensorbox = serial.Serial(
                sensorbox_serial_port,
                baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=.1
            )
        except serial.SerialException as e:
            logger.critical(f'SERIAL PORT LISTENER: Sensor serial port could not be opened: {e}')
            pass

        #work while ports are open
        while True and ser_rpi and ser_sensorbox:
            try:
                if ser_rpi.in_waiting > 0:
                    request = ser_rpi.readall()
                    if request:
                        written = ser_sensorbox.write(request)
                        if written != len(request):
                            logger.info('SERIAL PORT LISTENER: error transferring request')
                            continue
                        response = ser_sensorbox.readall()
                        if response:
                            written_back = ser_rpi.write(response)
                            if written_back != len(response):
                                logger.info('SERIAL PORT LISTENER: error transferring response')
                                continue
                                
            #Try to restore communication if lost
            except serial.SerialException as e:
                logger.critical(f'SERIAL PORT LISTENER: Communication error: {e}')
                if ser_rpi:
                    ser_rpi.close()
                if ser_sensorbox:
                    ser_sensorbox.close()
                time.sleep(1)
                try:
                    ser_rpi = serial.Serial(
                    rpi_serial_port,
                    baudrate,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_TWO,
                    timeout=.1
                    )
                except serial.SerialException as e:
                    logger.critical(f'SERIAL PORT LISTENER: RPI serial port could not be opened: {e}')
                    pass
                try:
                    ser_sensorbox = serial.Serial(
                    sensorbox_serial_port,
                    baudrate,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_TWO,
                    timeout=.1
                    )
                except serial.SerialException as e:
                    logger.critical(f'SERIAL PORT LISTENER: Sensor serial port could not be opened: {e}')
                    pass
                    
                continue
        
            except Exception as e:
                logger.exception(f'SERIAL PORT LISTENER: An unexpected error occurred: {e}')
                if ser_rpi:
                    ser_rpi.close()
                if ser_sensorbox:
                    ser_sensorbox.close()
                time.sleep(1)
    else:
        logger.critical('SERIAL PORT LISTENER: Settings file corrupted.')
#------------------------------------------------------------------------------


#------------------------------------------------------------------------------
def main():
    
    """
    Monitor the state of a GPIO pin and perform actions based on state changes.

    This script monitors the state of a specified GPIO pin on a Raspberry Pi.
    Depending on the changes in the GPIO pin state, it performs different actions:

    - If the pin transitions from LOW to HIGH, it triggers a system reboot.
    - If the pin transitions from HIGH to LOW, it stops a specified service and runs a calibration script.

    The script runs indefinitely, periodically checking the GPIO pin state with a short delay between iterations.

    GPIO Pin Configuration:
        The script is configured to use BCM numbering. The specified GPIO pin should be connected to the calibration switch.

    Actions:
        - Reboot the system when the callibration switch returns to "working mode".
        - Stop the 'suez.service' service and run a calibration script when the switch pulled to "calibration mode".

    Returns:
        None
    """
    
    CALIBRATION_SWITCH_PIN_NUMBER = 7
    #FAN_PIN_NUMBER = 24 #REMOVE

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(CALIBRATION_SWITCH_PIN_NUMBER, GPIO.IN, GPIO.PUD_UP)
    #GPIO.setup(FAN_PIN_NUMBER, GPIO.OUT) #REMOVE

    previous_state = 1

    while True:
        state = GPIO.input(CALIBRATION_SWITCH_PIN_NUMBER)

        if state == 1 and previous_state == 0:
            time.sleep(0.1)
            if GPIO.input(CALIBRATION_SWITCH_PIN_NUMBER) == 1:
                time.sleep(0.1)
                if GPIO.input(CALIBRATION_SWITCH_PIN_NUMBER) == 1:
                    #GPIO.output(FAN_PIN_NUMBER, GPIO.LOW) #REMOVE
                    subprocess.run(['sudo', 'reboot'])
                else:
                    previous_state = state
                    continue
            else:
                previous_state = state
                continue

        elif state == 0 and previous_state == 1:
            time.sleep(0.1)
            if GPIO.input(CALIBRATION_SWITCH_PIN_NUMBER) == 0:
                time.sleep(0.1)
                if GPIO.input(CALIBRATION_SWITCH_PIN_NUMBER) == 0:
                    #GPIO.output(FAN_PIN_NUMBER, GPIO.HIGH) #REMOVE
                    threading.Thread(target=calibration).start()
                else:
                    previous_state = state
                    continue
            else:
                previous_state = state
                continue

        previous_state = state
        time.sleep(0.1)
#------------------------------------------------------------------------------

if __name__ == "__main__":
    main()

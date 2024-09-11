import os
import sys
import signal
import RPi.GPIO as GPIO

os.chdir("/home/pi/K96Rpi")
sys.path.append("/home/pi/K96Rpi")

import libs.sensor_data_exchange as sde
import libs.local as ll

def sigterm_handler(signum, frame):
    logger.critical(f'FSM SERVICE: Sigterm recieved:\n {signum}\n {frame}')

signal.signal(signal.SIGTERM, sigterm_handler)

logger = ll.setup_logger("hw_monitor.log")

#------------------------------------------------------------------------------
def turn_fan(state):
    """
    Control the state of the fan connected to a specified GPIO pin.

    This function allows turning a fan on or off based on the specified state.
    It configures the GPIO pin for the fan and sets the output accordingly.
    After turning the fan off, it also cleans up the GPIO configuration.

    Args:
        state (str): The desired state of the fan. Should be either "on" or "off".

    Returns:
        None
    """
    # Define the GPIO pin for the fan
    FAN_PIN_NUMBER = 24

    # Set up GPIO configuration
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(FAN_PIN_NUMBER, GPIO.OUT)

    # Control the fan based on the specified state
    if state == "on":
        GPIO.output(FAN_PIN_NUMBER, GPIO.HIGH)
        logger.info("HW_MONITOR: TURN_FAN: Fan is on")
    elif state == "off":
        GPIO.output(FAN_PIN_NUMBER, GPIO.LOW)
        logger.info("HW_MONITOR: TURN_FAN: Fan is off")
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def check_temperature(settings):
    """
    Check the temperature from the Arduino sensor box and issue a warning if it exceeds a threshold.

    This function reads the raw temperature data from the sensor box, converts it to
    a meaningful temperature value, and checks if it exceeds a predefined threshold. If the
    temperature is above the threshold, a warning log is issued.

    Args:
        settings (dict): Dictionary containing calibration and sensor settings.
        comm_port (serial.Serial): The serial communication port to the sensor box.

    Returns:
        int: 1 if the temperature is above the threshold, 0 otherwise.
    """
    # Get sensor box configurations
    address = settings.get('box').get('arduino_address')
    function = settings.get('box').get('modbus_functions').get('READ_MULTIPLE_IR')
    register = settings.get('raw_data').get('arduino_registers').get('ntc_airambient_temp').get('address')
    
    # Read raw temperature data from the sensor box
    ll.acquire_lock("port")
    comm_port = sde.open_port(settings)
    if comm_port is not None:
        raw_temperature = sde.data_exchange(settings, comm_port, address, function, register, 1)
        ll.release_lock("port")
        # Convert raw temperature data to a meaningful temperature value
        if raw_temperature is not None:
            temp_temperature = raw_temperature[3:-2]
            temperature = int.from_bytes(temp_temperature, byteorder='big', signed=True)
            temperature = temperature / 100
    
        # Check if the temperature exceeds the threshold
        if temperature > 35:
            logger.warning("HW_MONITOR: Sensor overheat detected")
            return 1
        else:
            return 0
    else:
        logger.error("HW_MONITOR: Temperature cannot be measured, comm port not opened")
        ll.release_lock("port")
        return 0
#------------------------------------------------------------------------------



def main():
    settings = ll.load_settings()
    if settings is None:
        logger.critical('HW_MONITOR: Settings file corrupted.')
        sys.exit(1)
    try:
        ll.acquire_lock("port")
        comm_port = sde.open_port(settings)
        if comm_port is not None:
            sde.data_exchange(settings, comm_port, settings['box']['arduino_address'], settings['box']['modbus_functions']['WRITE_SINGLE_HR'], settings['pid1_setpoint_address'], 2, settings['pid1_base_value']) 
            comm_port.close()
            ll.release_lock("port")
            comm_port = None
        else:
            ll.release_lock("port")
            logger.warning("HW_MONITOR: Unable to write base value for PID setpoint. Port not opened")
    
        overheat = check_temperature(settings)
        if (overheat == 1):
            settings['overheat'] = True
            turn_fan("on")
            logger.warning("HW_MONITOR: Overheat detected. Fan is on")
        if ((settings['overheat'] == True) and (overheat == 0)):
            settings['overheat'] = False
            turn_fan("off")
            logger.warning("HW_MONITOR: Managed to stabilize the box temperature. Fan is off")
        
        ll.save_settings(settings)
        
        arduino_address = settings.get('box').get('arduino_address')
        sensor_address = settings.get('box').get('sensor_address')

        #getting heater values from K96-----------------
        heater_ref_address = settings.get("heater_ref_address")
        function = settings.get('box').get('modbus_functions').get('READ_RAM')
        
        ll.acquire_lock("port")
        comm_port = sde.open_port(settings)
        if comm_port is not None:
            raw_response = sde.data_exchange(settings, comm_port, sensor_address, function, heater_ref_address, 2)
            comm_port.close()
            ll.release_lock("port")
            comm_port = None

            if raw_response is not None:
                trunc_response = raw_response[3:-2]
                if not trunc_response:
                    logger.critical("HW_MONITOR: Incorrect data from Heater0")
                else:
                    heater_value  = int.from_bytes(trunc_response, byteorder='big', signed=False)
                    logger.info("HW_MONITOR: Heater0 value: " + str(heater_value))
            else:
                logger.info("HW_MONITOR: Sensor not answering")
        else:
            ll.release_lock("port")
            logger.warning("HW_MONITOR: Unable to read Heater0 values. Port not opened")
            
        #-------------------------------------------------
            
        #getting pid value from Arduino        
        pid1_output_address = settings.get("pid1_output_address")
    
        function = settings.get('box').get('modbus_functions').get('READ_MULTIPLE_IR')

        
        ll.acquire_lock("port")
        comm_port = sde.open_port(settings)
        if comm_port is not None:
            raw_response = sde.data_exchange(settings, comm_port, arduino_address, function, pid1_output_address, 1)
            comm_port.close()
            ll.release_lock("port")
            comm_port = None
        
            if raw_response is not None:
                trunc_response = raw_response[3:-2]
                if not trunc_response:
                    logger.critical("HW_MONITOR: Incorrect data from PID1")
                else:
                    pid1_value  = int.from_bytes(trunc_response, byteorder='big', signed=False)
                    logger.info("HW_MONITOR: PID1 value: " + str(pid1_value))
            else:
                logger.info("HW_MONITOR: Sensor not answering")
        else:
            ll.release_lock("port")
            logger.warning("HW_MONITOR: Unable to read PID values. Port not opened")
                    
                    
        if (pid1_value > 252):
            logger.critical("HW_MONITOR: Pump is overloaded")
            ll.acquire_lock("port")
            comm_port = sde.open_port(settings)
            if comm_port is not None:
                sde.data_exchange(settings, comm_port, settings['box']['sensor_address'], settings['box']['modbus_functions']['WRITE_RAM'], settings['heater_ctl_address'], 2, "0x0")
                sde.data_exchange(settings, comm_port, settings['box']['arduino_address'], settings['box']['modbus_functions']['WRITE_SINGLE_HR'], settings['pid1_setpoint_address'], 2, "0x0FA0")
                comm_port.close()
            else:
                logger.warning("HW_MONITOR: Unable turn off pump and heater. Port not opened")
            ll.release_lock("port")
            comm_port = None
            settings["occlusion_detected"] = True
            ll.save_settings(settings)

            
        
        if (pid1_value == 0):
            logger.critical("HW_MONITOR: Pump is OFF, attempt to restart")
            ll.acquire_lock("port")
            comm_port = sde.open_port(settings)
            if comm_port is not None:
                sde.data_exchange(settings, comm_port, settings['box']['arduino_address'], settings['box']['modbus_functions']['WRITE_SINGLE_HR'], settings['pid1_setpoint_address'], 2, settings['pid1_base_value'])
                sde.data_exchange(settings, comm_port, settings['box']['sensor_address'], settings['box']['modbus_functions']['WRITE_RAM'], settings['heater_ctl_address'], 2, settings['heater_base_value']) 
                sde.data_exchange(settings, comm_port, settings['box']['sensor_address'], settings['box']['modbus_functions']['WRITE_RAM'], "0x60", 1, "0xFF")
                comm_port.close()
            else:
                logger.warning("HW_MONITOR: Unable ыефке pump and heater. Port not opened")
            ll.release_lock("port")
            comm_port = None
            settings["occlusion_detected"] = False
            ll.save_settings(settings)
    
    except Exception as e:
        ll.release_lock("port")


if __name__ == "__main__":
    main()
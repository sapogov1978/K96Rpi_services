import time
import serial
import sys

#------------------------------------------------------------------------------
def send_modbus_request(serial_port, request):
    """
    Send a Modbus request frame to a Modbus slave device through a serial port.

    Args:
        serial_port (serial.Serial): The serial port object for communication.
        request (bytearray): The Modbus request frame to be sent.

    Returns:
        bool: True if the request was sent successfully, False otherwise.
    """
    # Flush input and output buffers, introduce a small delay
    serial_port.flushOutput()
    serial_port.flushInput()
    time.sleep(0.1)

    # Send the Modbus request frame
    check = serial_port.write(request)
    if check != len(request):
        return False
    time.sleep(0.1)

    # Request sent successfully
    return True
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def generate_modbus_request(slave_address, function_code, register_address, registers_qty, data_to_write=None):
    """
    Generate a Modbus request frame for communication with a Modbus slave device.

    Args:
        slave_address (str): The address of the Modbus slave device (hex string).
        function_code (str): The Modbus function code (hex string) specifying the operation.
        register_address (str): The starting address of the registers (hex string).
        registers_qty (int): The quantity of registers to read or write.

    Returns:
        bytearray: The Modbus request frame as a bytearray.
    """
    # Convert input parameters to integers
    slave_address = int(slave_address, 16)
    function_code = int(function_code, 16)
    register_address = int(register_address, 16)
    registers_qty = int(registers_qty)
    if data_to_write is not None:
        data_to_write = int(data_to_write, 16)
    
    # Construct the PDU (Protocol Data Unit)
    if data_to_write is not None:
        if (function_code == 6):
            pdu = bytearray([*function_code.to_bytes(1, byteorder='big'),
                             *register_address.to_bytes(2, byteorder='big'),
                             *data_to_write.to_bytes(registers_qty, byteorder='big')])
        else:
            pdu = bytearray([*function_code.to_bytes(1, byteorder='big'),
                             *register_address.to_bytes(2, byteorder='big'),
                             *registers_qty.to_bytes(1, byteorder='big'),
                             *data_to_write.to_bytes(registers_qty, byteorder='big')])
    else:
        if (function_code == 3 or function_code == 4) and slave_address == 105:
            pdu = bytearray([*function_code.to_bytes(1, byteorder='big'),
                             *register_address.to_bytes(2, byteorder='big'),
                             *registers_qty.to_bytes(2, byteorder='big')])
        else:
            pdu = bytearray([*function_code.to_bytes(1, byteorder='big'),
                             *register_address.to_bytes(2, byteorder='big'),
                             *registers_qty.to_bytes(1, byteorder='big')])
    
    # Calculate CRC for the PDU
    crc = calculate_crc(bytearray([slave_address, *pdu]))
    
    # Construct the complete Modbus request frame
    request = bytearray([slave_address, *pdu, *crc])
    
    return request
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def calculate_crc(data):
    """
    Calculate the CRC (Cyclic Redundancy Check) checksum for the given data sequence.

    Args:
        data (bytes or bytearray): The input data sequence for which to calculate the CRC.

    Returns:
        bytes: The CRC checksum as a 2-byte little-endian binary representation.
    """
    # Precomputed CRC table
    crc_table = [
        0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
        0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
        0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
        0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
        0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
        0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
        0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
        0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
        0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
        0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
        0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
        0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
        0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
        0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
        0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
        0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
        0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
        0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
        0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
        0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
        0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
        0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
        0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
        0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
        0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
        0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
        0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
        0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
        0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
        0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
        0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
        0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040
    ]
    
    # Initialize CRC value
    crc = 0xFFFF
    
    # Update CRC value
    for byte in data:
        crc = (crc >> 8) ^ crc_table[(crc ^ byte) & 0xFF]
    
    # Convert CRC to a 2-byte little-endian binary
    return crc.to_bytes(2, byteorder='little')
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def check_crc(response):
    """
    Check whether the CRC (Cyclic Redundancy Check) checksum in a response matches the calculated CRC checksum.

    Args:
        response (bytes or bytearray): The response data sequence, including the CRC checksum.

    Returns:
        bool: True if the CRC values match, indicating a successful CRC check; False otherwise.
    """
    if response is not None:
        # Extract CRC value from the last two bytes of the response
        crc = int.from_bytes(response[-2:], byteorder='little')

        # Calculate the CRC checksum for the response data (excluding the last two bytes)
        calculated_crc = int.from_bytes(calculate_crc(response[:-2]), byteorder='little')

        # Compare the extracted CRC with the calculated CRC
        return crc == calculated_crc

    # Return False if response is None
    return False
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def data_exchange(settings, comm_port, address, function_code, register_address, registers_qty, data_to_write=None):
    """
    Exchange data with a device over a serial communication port using Modbus protocol.

    This function initiates a Modbus data exchange with a device over a serial communication port.
    It sends a Modbus request, reads the response, and validates the response's integrity.
    It attempts to retrieve valid data by sending the Modbus request multiple times (configurable
    through 'settings') until a valid response is received or the maximum retry count is reached.

    Args:
        settings (dict): A dictionary containing configuration settings.
        comm_port (serial.Serial): The serial communication port object.
        address (str): The address of the device or sensor.
        function_code (str): The Modbus function code (e.g., '03' for read operation).
        register_address (str): The address of the Modbus register to read or write.
        registers_qty (int): The quantity of registers to read or write.

    Returns:
        bytes or None: The response data from the device if successful, or None if unsuccessful.
    """
    response = []
    tries_left = settings.get('box').get('tries')

    while tries_left > 0:
        if not response or response[1] == (int(function_code, 16) | 0x80) or not check_crc(response):
            request = generate_modbus_request(address, function_code, register_address, registers_qty, data_to_write)
    
            if not send_modbus_request(comm_port, request) and tries_left > 0:
                continue

            response = comm_port.readall()

            tries_left -= 1
        else:
            break
    
        if tries_left == 0:
            return None
        else:    
            return response
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
def open_port(settings):
    """
    Open a serial port connection based on the provided settings.

    This function attempts to open the serial port specified in the settings dictionary
    with the given baudrate. It retries opening the port in case of an IOError. If it
    fails to open the port after the specified number of tries, it logs a fatal error
    and exits the program.

    Args:
        settings (dict): The settings dictionary containing configuration information.

    Returns:
        serial.Serial or None: The opened serial port connection or None if opening
        the port failed after retries.
    """
    ser = None
    port = settings.get('box').get('port')
    baudrate = settings.get('box').get('baudrate')
    tries_left = settings.get('box').get('tries')

    while (tries_left > 0):
        try:
            ser = serial.Serial(
                port, 
                baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=.1
            )
            if ser is not None:
                break
        except IOError as e:
            tries_left -= 1
            continue
    
    #if not ser and tries_left == 0:
    #    sys.exit(1)
    return ser
#------------------------------------------------------------------------------

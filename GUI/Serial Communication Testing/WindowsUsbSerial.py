import serial
import time

# Replace 'COM_PORT' with the actual COM Port of the NUCLEO-F303RE USB connection
ser = serial.Serial('COM_PORT', 115200, timeout=1)

try:
    while True:
        if ser.in_waiting:
            data = ser.readline().decode('utf-8').rstrip()
            print(f"Received: {data}")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Program terminated!")
finally:
    ser.close()

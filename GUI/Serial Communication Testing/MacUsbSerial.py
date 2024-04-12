import serial
import time

# Replace '/dev/tty.usbmodemXXXX' with the actual serial port name of your NUCLEO-F303RE
ser = serial.Serial('/dev/tty.usbmodemXXXX', 115200, timeout=1)

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

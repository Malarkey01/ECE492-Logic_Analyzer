# main.py:

import sys
import serial.tools.list_ports
from PyQt6.QtWidgets import QApplication
from LogicDisplay import LogicDisplay  # Import LogicDisplay
from connection import SerialApp
from aesthetic import apply_styles  # Import the apply_styles function

def main():
    app = QApplication(sys.argv)
    apply_styles(app)  # Apply the dark mode and icon

    # Attempt to find the device with vid=1155 and pid=22336
    vid = 1155
    pid = 22336
    ports = serial.tools.list_ports.comports()
    target_port = None
    for port in ports:
        if port.vid == vid and port.pid == pid:
            target_port = port.device
            break

    if target_port:
        # Device found, directly create LogicDisplay
        window = LogicDisplay(port=target_port, baudrate=115200, bufferSize=4096, channels=8)
        window.show()
        print(f"Automatically connected to device on port {target_port}")
    else:
        # Device not found, show SerialApp
        window = SerialApp()
        window.show()
        print("Device not found. Opening connection window.")

    sys.exit(app.exec())

if __name__ == '__main__':
    main()

import sys
import serial.tools.list_ports
from PyQt6.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QComboBox
from aesthetic import get_icon
from LogicDisplay import LogicDisplay  # Make sure this is the correct file name

class SerialApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial Connection Manager")
        self.setWindowIcon(get_icon())
        self.logic_display_window = None  # Reference to LogicDisplay window
        self.initUI()

    def initUI(self):
        # Main widget and layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        layout = QVBoxLayout(self.main_widget)

        # Dropdown for COM ports
        self.combo_ports = QComboBox()
        self.refresh_ports()
        layout.addWidget(self.combo_ports)

        # Refresh button
        self.button_refresh = QPushButton("Refresh")
        self.button_refresh.clicked.connect(self.refresh_ports)
        layout.addWidget(self.button_refresh)

        # Connect button
        self.button_connect = QPushButton("Connect")
        self.button_connect.clicked.connect(self.connect_device)
        layout.addWidget(self.button_connect)

        # Disconnect button
        self.button_disconnect = QPushButton("Disconnect")
        self.button_disconnect.clicked.connect(self.disconnect_device)
        self.button_disconnect.setEnabled(False)
        layout.addWidget(self.button_disconnect)

    def refresh_ports(self):
        self.combo_ports.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.combo_ports.addItem(port.device)

    def connect_device(self):
        port_name = self.combo_ports.currentText()
        try:
            self.button_connect.setEnabled(False)
            self.button_disconnect.setEnabled(True)
            print(f"Connected to {port_name}")

            # Close the previous LogicDisplay window if it exists
            if self.logic_display_window:
                self.logic_display_window.close()

            # Create a new LogicDisplay window
            self.logic_display_window = LogicDisplay(port=port_name, baudrate=115200, channels=8)
            self.logic_display_window.show()

        except Exception as e:
            print(f"Failed to connect to {port_name}: {str(e)}")

    def disconnect_device(self):
        # Close the LogicDisplay window when disconnecting the device
        if self.logic_display_window:
            self.logic_display_window.close()
            self.logic_display_window = None  # Reset the reference

        self.button_connect.setEnabled(True)
        self.button_disconnect.setEnabled(False)
        print("Disconnected")

# LogicDisplay.py:

import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QButtonGroup,
    QPushButton,
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from aesthetic import get_icon
from Signal import SignalDisplay
from I2C import I2CDisplay
from SPI import SPIDisplay
from UART import UARTDisplay

class LogicDisplay(QMainWindow):
    def __init__(self, port, baudrate, bufferSize=4096, channels=8):
        super().__init__()
        self.port = port
        self.default_baudrate = baudrate  # Store default baud rate
        self.baudrate = baudrate
        self.channels = channels
        self.bufferSize = bufferSize

        self.setWindowTitle("Logic Analyzer")
        self.setWindowIcon(get_icon())

        self.current_module = None
        self.init_ui()

        # Load the default module (Signal)
        self.load_module('Signal')

    def init_ui(self):
        # Create a central widget with vertical layout
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        # Create a widget for the buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)

        # Create buttons for each mode
        self.signal_button = QPushButton('Signal')
        self.i2c_button = QPushButton('I2C')
        self.spi_button = QPushButton('SPI')
        self.uart_button = QPushButton('UART')

        # Make buttons checkable
        self.signal_button.setCheckable(True)
        self.i2c_button.setCheckable(True)
        self.spi_button.setCheckable(True)
        self.uart_button.setCheckable(True)

        # Create a button group for exclusive checking
        self.mode_button_group = QButtonGroup()
        self.mode_button_group.setExclusive(True)
        self.mode_button_group.addButton(self.signal_button)
        self.mode_button_group.addButton(self.i2c_button)
        self.mode_button_group.addButton(self.spi_button)
        self.mode_button_group.addButton(self.uart_button)

        # Set the default checked button
        self.signal_button.setChecked(True)

        # Add buttons to the layout
        button_layout.addWidget(self.signal_button)
        button_layout.addWidget(self.i2c_button)
        button_layout.addWidget(self.spi_button)
        button_layout.addWidget(self.uart_button)

        # Connect buttons to the handler
        self.signal_button.clicked.connect(lambda: self.load_module('Signal'))
        self.i2c_button.clicked.connect(lambda: self.load_module('I2C'))
        self.spi_button.clicked.connect(lambda: self.load_module('SPI'))
        self.uart_button.clicked.connect(lambda: self.load_module('UART'))

        # Create a widget to hold the current module
        self.module_widget = QWidget()
        self.module_layout = QVBoxLayout(self.module_widget)
        self.module_layout.setContentsMargins(0, 0, 0, 0)
        self.module_layout.setSpacing(0)

        # Add the button widget and the module widget to the central layout
        central_layout.addWidget(button_widget)
        central_layout.addWidget(self.module_widget)

        # Set the central widget
        self.setCentralWidget(central_widget)

    def load_module(self, module_name):
        # Remove the existing module widget if any
        if self.current_module:
            self.current_module.close()
            self.current_module.deleteLater()
            self.current_module = None

        # Clear the module_layout
        while self.module_layout.count():
            item = self.module_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Reset baud rate to default when switching modes
        if module_name != 'UART':
            self.baudrate = self.default_baudrate

        # Load the selected module
        if module_name == 'Signal':
            self.current_module = SignalDisplay(self.port, self.baudrate, self.bufferSize, self.channels)
            self.signal_button.setChecked(True)
        elif module_name == 'I2C':
            self.current_module = I2CDisplay(self.port, self.baudrate, self.bufferSize)
            self.i2c_button.setChecked(True)
        elif module_name == 'SPI':
            self.current_module = SPIDisplay(self.port, self.baudrate, self.bufferSize)
            self.spi_button.setChecked(True)
        elif module_name == 'UART':
            # Update baud rate if changed in UART mode
            self.current_module = UARTDisplay(self.port, self.baudrate, self.bufferSize)
            self.uart_button.setChecked(True)

        if self.current_module:
            self.module_layout.addWidget(self.current_module)
            self.current_module.show()
        else:
            # Placeholder if the module is not implemented
            placeholder_widget = QWidget()
            self.module_layout.addWidget(placeholder_widget)

    def update_baudrate(self, baudrate):
        self.baudrate = baudrate

    def closeEvent(self, event):
        if self.current_module:
            self.current_module.close()
        event.accept()

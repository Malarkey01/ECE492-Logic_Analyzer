# LogicDisplay.py

import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMenuBar,
    QMenu,
)
from PyQt6.QtGui import QAction  # Import QAction from PyQt6.QtGui
from PyQt6.QtCore import Qt

from aesthetic import get_icon
from Signal import SignalDisplay
from I2C import I2CDisplay
from SPI import SPIDisplay
from UART import UARTDisplay

class LogicDisplay(QMainWindow):
    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.port = port
        self.default_baudrate = baudrate  # Store default baud rate
        self.baudrate = baudrate
        self.channels = channels

        self.setWindowTitle("Logic Analyzer")
        self.setWindowIcon(get_icon())

        self.current_module = None
        self.init_ui()

        # Load the default module (Signal)
        self.load_module('Signal')

    def init_ui(self):
        # Create a menu bar
        menu_bar = self.menuBar()

        # Add a dropdown menu
        mode_menu = menu_bar.addMenu('Mode')

        # Create actions for each mode
        signal_action = QAction('Signal', self)
        i2c_action = QAction('I2C', self)
        spi_action = QAction('SPI', self)
        uart_action = QAction('UART', self)

        # Add actions to the mode menu
        mode_menu.addAction(signal_action)
        mode_menu.addAction(i2c_action)
        mode_menu.addAction(spi_action)
        mode_menu.addAction(uart_action)

        # Connect actions to the handler
        signal_action.triggered.connect(lambda: self.load_module('Signal'))
        i2c_action.triggered.connect(lambda: self.load_module('I2C'))
        spi_action.triggered.connect(lambda: self.load_module('SPI'))
        uart_action.triggered.connect(lambda: self.load_module('UART'))

    def load_module(self, module_name):
        # Remove the existing module widget if any
        if self.current_module:
            self.current_module.close()
            self.current_module.deleteLater()
            self.current_module = None

        # Reset baud rate to default when switching modes
        if module_name != 'UART':
            self.baudrate = self.default_baudrate

        # Load the selected module
        if module_name == 'Signal':
            self.current_module = SignalDisplay(self.port, self.baudrate, self.channels)
        elif module_name == 'I2C':
            self.current_module = I2CDisplay(self.port, self.baudrate)
        elif module_name == 'SPI':
            self.current_module = SPIDisplay(self.port, self.baudrate)
        elif module_name == 'UART':
            # Update baud rate if changed in UART mode
            self.current_module = UARTDisplay(self.port, self.baudrate)
            self.current_module.baudrate_changed.connect(self.update_baudrate)

        if self.current_module:
            self.setCentralWidget(self.current_module)
            self.current_module.show()
        else:
            # Placeholder if the module is not implemented
            placeholder_widget = QWidget()
            placeholder_layout = QVBoxLayout(placeholder_widget)
            placeholder_layout.addWidget(QWidget())
            self.setCentralWidget(placeholder_widget)

    def update_baudrate(self, baudrate):
        self.baudrate = baudrate

    def closeEvent(self, event):
        if self.current_module:
            self.current_module.close()
        event.accept()

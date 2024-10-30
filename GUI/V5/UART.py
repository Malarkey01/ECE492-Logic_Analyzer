# UART.py:

import sys
import serial
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QLineEdit,
)
from PyQt6.QtGui import QIcon, QIntValidator
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from collections import deque
from aesthetic import get_icon
import time

class SerialWorker(QThread):
    data_ready = pyqtSignal(dict)

    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.port = port
        self.baudrate = baudrate

        try:
            self.serial = serial.Serial(self.port, self.baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def run(self):
        while self.is_running:
            if self.serial.in_waiting:
                try:
                    raw_data = self.serial.readline().decode('utf-8').strip()
                    # Assuming data format: "chX:data"
                    if raw_data.startswith('ch'):
                        channel_num = int(raw_data[2]) - 1  # Convert to 0-based index
                        data = raw_data[4:]  # Extract data after 'chX:'
                        self.data_ready.emit({channel_num: data})
                except (ValueError, UnicodeDecodeError) as e:
                    print(f"Error parsing data: {str(e)}")
                    continue

    def stop_worker(self):
        self.is_running = False
        if self.serial.is_open:
            self.serial.close()

class UARTDisplay(QWidget):
    baudrate_changed = pyqtSignal(int)

    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.port = port
        self.default_baudrate = baudrate
        self.channels = channels

        self.text_buffers = [deque(maxlen=1000) for _ in range(self.channels)]  # Limit to last 1000 messages
        self.text_displays = []
        self.channel_enabled = [False] * self.channels

        self.setup_ui()

        self.worker = SerialWorker(self.port, self.default_baudrate, channels=self.channels)
        self.worker.data_ready.connect(self.update_text_displays)
        self.worker.start()


    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Grid layout for channel controls
        control_layout = QGridLayout()
        main_layout.addLayout(control_layout)

        self.channel_buttons = []

        for i in range(self.channels):
            label = f"Channel {i+1}"
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))
            control_layout.addWidget(button, i // 4, i % 4)  # Arrange buttons in a grid
            self.channel_buttons.append(button)

        # Baud Rate input
        baudrate_layout = QHBoxLayout()
        self.baudrate_label = QLabel("Baud Rate:")
        baudrate_layout.addWidget(self.baudrate_label)

        self.baudrate_input = QLineEdit()
        self.baudrate_input.setValidator(QIntValidator(1, 10000000))
        self.baudrate_input.setText(str(self.default_baudrate))
        baudrate_layout.addWidget(self.baudrate_input)
        self.baudrate_input.returnPressed.connect(self.handle_baudrate_input)

        main_layout.addLayout(baudrate_layout)

        # Start/Stop buttons
        control_buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_reading)
        control_buttons_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_reading)
        self.stop_button.setEnabled(False)
        control_buttons_layout.addWidget(self.stop_button)

        main_layout.addLayout(control_buttons_layout)

        # Text displays for each channel
        text_display_layout = QGridLayout()
        main_layout.addLayout(text_display_layout)

        for i in range(self.channels):
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setStyleSheet("background-color: #2e2e2e; color: #ffffff;")
            text_edit.hide()  # Hide until channel is enabled
            self.text_displays.append(text_edit)
            text_display_layout.addWidget(text_edit, i // 4, i % 4)  # Arrange in a grid

    def handle_baudrate_input(self):
        try:
            baudrate = int(self.baudrate_input.text())
            if baudrate <= 0:
                raise ValueError("Baud rate must be positive")
            self.worker.stop_worker()
            self.worker.wait()
            self.worker = SerialWorker(self.port, baudrate, channels=self.channels)
            self.worker.data_ready.connect(self.update_text_displays)
            self.worker.start()
            print(f"Baud rate changed to {baudrate}")
        except ValueError as e:
            print(f"Invalid baud rate: {e}")

    def toggle_channel(self, channel_idx, is_checked):
        self.channel_enabled[channel_idx] = is_checked
        if is_checked:
            self.text_displays[channel_idx].show()
            self.channel_buttons[channel_idx].setStyleSheet(
                "background-color: #00FF77; color: black;"
            )
        else:
            self.text_displays[channel_idx].hide()
            self.channel_buttons[channel_idx].setStyleSheet("")

    def start_reading(self):
        self.worker.is_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_reading(self):
        self.worker.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_text_displays(self, data_dict):
        for channel_idx, data in data_dict.items():
            if self.channel_enabled[channel_idx]:
                self.text_buffers[channel_idx].append(data)
                # Update the QTextEdit with the content of the buffer
                self.text_displays[channel_idx].setPlainText('\n'.join(self.text_buffers[channel_idx]))
                # Scroll to the end
                self.text_displays[channel_idx].verticalScrollBar().setValue(self.text_displays[channel_idx].verticalScrollBar().maximum())


    def closeEvent(self, event):
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()

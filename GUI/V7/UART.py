import sys
import serial
import math
import time
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QInputDialog,
    QMenu,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QDialog,
    QRadioButton,
    QButtonGroup,
    QSizePolicy,
)
from PyQt6.QtGui import QIcon, QIntValidator, QFont
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from collections import deque
from InterfaceCommands import (
    get_trigger_edge_command,
    get_trigger_pins_command,
)
from aesthetic import get_icon


class SerialWorker(QThread):
    data_ready = pyqtSignal(int, int)  # For raw data values and sample indices
    decoded_message_ready = pyqtSignal(dict)  # For decoded messages

    def __init__(self, port, baudrate, channels=8, uart_configs=None):
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.uart_configs = uart_configs if uart_configs else [{} for _ in range(8)]
        self.current_trigger_modes = ['No Trigger'] * self.channels
        self.sample_idx = 0  # Initialize sample index

        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

        # Initialize UART decoding variables for each channel
        self.states = ['IDLE'] * self.channels
        self.data_buffers = [deque(maxlen=16 * 10) for _ in range(self.channels)]
        self.start_bit_samples = [[] for _ in range(self.channels)]
        self.sample_counters = [0] * self.channels
        self.current_bytes = [0] * self.channels
        self.bit_indices = [0] * self.channels

    def set_trigger_mode(self, channel_idx, mode):
        self.current_trigger_modes[channel_idx] = mode

    def run(self):
        data_buffer = deque(maxlen=1000)

        while self.is_running:
            if self.serial.in_waiting:
                raw_data = self.serial.read(self.serial.in_waiting).splitlines()
                for line in raw_data:
                    try:
                        data_value = int(line.strip())
                        data_buffer.append(data_value)
                        self.data_ready.emit(data_value, self.sample_idx)  # Emit data_value and sample_idx
                        self.decode_uart(data_value, self.sample_idx)
                        self.sample_idx += 1  # Increment sample index
                    except ValueError:
                        continue

    def decode_uart(self, data_value, sample_idx):
        for idx, uart_config in enumerate(self.uart_configs):
            if not uart_config.get('enabled', False):
                continue  # Skip if UART channel is not enabled

            channel_idx = uart_config['data_channel'] - 1
            polarity = uart_config.get('polarity', 'Standard')
            stop_bits = uart_config.get('stop_bits', 1)
            data_format = uart_config.get('data_format', 'Hexadecimal')

            # Extract the data bit
            data_bit = (data_value >> channel_idx) & 1
            if polarity == 'Inverted':
                data_bit = 1 - data_bit

            self.data_buffers[idx].append(data_bit)

            # UART decoding state machine
            if self.states[idx] == 'IDLE':
                if data_bit == 0:
                    # Potential start bit detected
                    self.start_bit_samples[idx] = [data_bit]
                    self.states[idx] = 'START_BIT'
                    self.sample_counters[idx] = 1
            elif self.states[idx] == 'START_BIT':
                self.start_bit_samples[idx].append(data_bit)
                self.sample_counters[idx] += 1
                if self.sample_counters[idx] >= 16:
                    # Check if majority of samples indicate a valid start bit
                    if sum(self.start_bit_samples[idx][7:10]) <= 1:
                        # Valid start bit
                        self.states[idx] = 'DATA_BITS'
                        self.sample_counters[idx] = 0
                        self.current_bytes[idx] = 0
                        self.bit_indices[idx] = 0
                    else:
                        # False start bit detected
                        self.states[idx] = 'IDLE'
            elif self.states[idx] == 'DATA_BITS':
                self.sample_counters[idx] += 1
                if self.sample_counters[idx] % 16 == 0:
                    # Sample the data bit
                    bit_samples = list(self.data_buffers[idx])[-16:]
                    bit_value = 1 if sum(bit_samples[7:10]) >= 2 else 0
                    self.current_bytes[idx] |= (bit_value << self.bit_indices[idx])
                    self.bit_indices[idx] += 1
                    if self.bit_indices[idx] >= 8:
                        self.states[idx] = 'STOP_BITS'
                        self.bit_indices[idx] = 0
                        self.sample_counters[idx] = 0
                        # Emit the decoded byte
                        self.emit_decoded_data(idx, self.current_bytes[idx], sample_idx, data_format)
            elif self.states[idx] == 'STOP_BITS':
                self.sample_counters[idx] += 1
                if self.sample_counters[idx] >= 16 * stop_bits:
                    # Check for valid stop bits if needed
                    self.states[idx] = 'IDLE'
                    self.sample_counters[idx] = 0

    def emit_decoded_data(self, uart_idx, byte_value, sample_idx, data_format):
        # Format data according to data_format
        if data_format == 'Binary':
            data_str = bin(byte_value)
        elif data_format == 'Decimal':
            data_str = str(byte_value)
        elif data_format == 'Hexadecimal':
            data_str = hex(byte_value)
        elif data_format == 'ASCII':
            data_str = chr(byte_value)
        else:
            data_str = hex(byte_value)

        # Emit the decoded message
        self.decoded_message_ready.emit({
            'uart_idx': uart_idx,
            'event': 'DATA',
            'data': data_str,
            'sample_idx': sample_idx,
        })

    def reset_decoding_states(self):
        self.states = ['IDLE'] * self.channels
        self.data_buffers = [deque(maxlen=16 * 10) for _ in range(self.channels)]
        self.start_bit_samples = [[] for _ in range(self.channels)]
        self.sample_counters = [0] * self.channels
        self.current_bytes = [0] * self.channels
        self.bit_indices = [0] * self.channels
        self.sample_idx = 0  # Reset sample index

    def stop_worker(self):
        self.is_running = False
        if self.serial.is_open:
            self.serial.close()


class FixedYViewBox(pg.ViewBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def scaleBy(self, s=None, center=None, x=None, y=None):
        y = 1.0  # Fix y-scaling
        if x is None:
            if s is None:
                x = 1.0
            elif isinstance(s, dict):
                x = s.get('x', 1.0)
            elif isinstance(s, (list, tuple)):
                x = s[0] if len(s) > 0 else 1.0
            else:
                x = s
        super().scaleBy(x=x, y=y, center=center)

    def translateBy(self, t=None, x=None, y=None):
        y = 0.0  # Fix y-translation
        if x is None:
            if t is None:
                x = 0.0
            elif isinstance(t, dict):
                x = t.get('x', 0.0)
            elif isinstance(t, (list, tuple)):
                x = t[0] if len(t) > 0 else 0.0
            else:
                x = t
        super().translateBy(x=x, y=y)


class EditableButton(QPushButton):
    configure_requested = pyqtSignal(int)  # Signal to notify when configure is requested
    reset_requested = pyqtSignal(int)      # Signal for reset

    def __init__(self, label, idx, parent=None):
        super().__init__(label, parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.default_label = label
        self.idx = idx  # Index of the UART channel

    def show_context_menu(self, position):
        menu = QMenu()
        rename_action = menu.addAction("Rename")
        reset_action = menu.addAction("Reset to Default")
        configure_action = menu.addAction("Configure")  # Add the Configure option
        action = menu.exec(self.mapToGlobal(position))
        if action == rename_action:
            new_label, ok = QInputDialog.getText(
                self, "Rename Button", "Enter new label:", text=self.text()
            )
            if ok and new_label:
                self.setText(new_label)
        elif action == reset_action:
            self.setText(self.default_label)
            self.reset_requested.emit(self.idx)  # Emit reset signal
        elif action == configure_action:
            self.configure_requested.emit(self.idx)  # Emit signal to open configuration dialog


class UARTConfigDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UART Configuration")
        self.current_config = current_config  # Dictionary to hold current configurations
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Data Channel Selection
        data_layout = QHBoxLayout()
        data_label = QLabel("Data Channel:")
        self.data_combo = QComboBox()
        self.data_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.data_combo.setCurrentIndex(self.current_config.get('data_channel', 1) - 1)
        data_layout.addWidget(data_label)
        data_layout.addWidget(self.data_combo)
        layout.addLayout(data_layout)

        # Polarity Selection
        polarity_layout = QHBoxLayout()
        polarity_label = QLabel("Polarity:")
        self.polarity_group = QButtonGroup(self)
        self.polarity_standard = QRadioButton("Standard")
        self.polarity_inverted = QRadioButton("Inverted")
        self.polarity_group.addButton(self.polarity_standard)
        self.polarity_group.addButton(self.polarity_inverted)
        polarity_layout.addWidget(polarity_label)
        polarity_layout.addWidget(self.polarity_standard)
        polarity_layout.addWidget(self.polarity_inverted)
        layout.addLayout(polarity_layout)

        if self.current_config.get('polarity', 'Standard') == 'Standard':
            self.polarity_standard.setChecked(True)
        else:
            self.polarity_inverted.setChecked(True)

        # Stop Bits Selection
        stop_bits_layout = QHBoxLayout()
        stop_bits_label = QLabel("Stop Bits:")
        self.stop_bits_input = QLineEdit()
        self.stop_bits_input.setValidator(QIntValidator(0, 3))
        self.stop_bits_input.setText(str(self.current_config.get('stop_bits', 1)))
        stop_bits_layout.addWidget(stop_bits_label)
        stop_bits_layout.addWidget(self.stop_bits_input)
        layout.addLayout(stop_bits_layout)

        # Data Format Selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Data Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Binary", "Decimal", "Hexadecimal", "ASCII"])
        self.format_combo.setCurrentText(self.current_config.get('data_format', 'Hexadecimal'))
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_configuration(self):
        return {
            'data_channel': self.data_combo.currentIndex() + 1,
            'polarity': 'Standard' if self.polarity_standard.isChecked() else 'Inverted',
            'stop_bits': int(self.stop_bits_input.text()),
            'data_format': self.format_combo.currentText(),
        }


class UARTDisplay(QWidget):
    def __init__(self, port, baudrate, bufferSize, channels=8):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.channels = channels
        self.bufferSize = bufferSize

        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]
        self.sample_indices = deque(maxlen=self.bufferSize)
        self.total_samples = 0

        self.is_single_capture = False

        self.current_trigger_modes = ['No Trigger'] * self.channels
        self.trigger_mode_options = ['No Trigger', 'Rising Edge', 'Falling Edge']

        # Baud rate options
        self.baud_rates = [300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 74880, 115200]
        self.default_baud_rate = 9600  # Default baud rate
        self.baud_rate = self.default_baud_rate  # Current baud rate

        # Initialize UART configurations with default settings for each channel
        self.uart_configs = []
        for i in range(self.channels):
            self.uart_configs.append({
                'data_channel': i + 1,
                'polarity': 'Standard',
                'stop_bits': 1,
                'data_format': 'Hexadecimal',
                'enabled': False,  # Start with channels disabled
            })

        # Initialize decoded messages per channel
        self.decoded_messages_per_channel = {i: [] for i in range(self.channels)}

        self.cursors_per_channel = [[] for _ in range(self.channels)]  # To store cursors per channel

        self.setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading = False

        self.worker = SerialWorker(self.port, self.baudrate, channels=self.channels, uart_configs=self.uart_configs)
        self.worker.data_ready.connect(self.handle_data_value)
        self.worker.decoded_message_ready.connect(self.display_decoded_message)
        self.worker.start()

        self.colors = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF', '#FFFF33', '#FFA500', '#00F5FF', '#BFFF00']
        self.curves = []
        for i in range(self.channels):
            curve = self.plot.plot(pen=pg.mkPen(color=self.colors[i % len(self.colors)], width=2))
            curve.setVisible(False)
            self.curves.append(curve)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        plot_layout = QHBoxLayout()
        main_layout.addLayout(plot_layout)

        self.graph_layout = pg.GraphicsLayoutWidget()
        plot_layout.addWidget(self.graph_layout, stretch=3)

        self.plot = self.graph_layout.addPlot(viewBox=FixedYViewBox())

        self.sample_rate = self.baud_rate * 16  # Default sample rate

        self.plot.setXRange(0, self.bufferSize / self.sample_rate, padding=0)
        self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.setYRange(-2, 2 * self.channels, padding=0)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)
        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)
        self.plot.setLabel('bottom', 'Time', units='s')

        button_layout = QGridLayout()
        plot_layout.addLayout(button_layout, stretch=1)

        button_widget = QWidget()
        button_layout = QGridLayout(button_widget)
        plot_layout.addWidget(button_widget)

        self.channel_buttons = []
        self.trigger_mode_buttons = []

        for i in range(self.channels):
            row = i
            label = f"UART {i+1}\nCh{self.uart_configs[i]['data_channel']}"
            button = EditableButton(label, idx=i)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            button.setFixedWidth(150)
            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))
            button.configure_requested.connect(self.open_configuration_dialog)
            button.reset_requested.connect(self.reset_channel_to_default)
            button_layout.addWidget(button, row, 0)

            # Trigger Mode Button
            trigger_button = QPushButton(f"Trigger - {self.current_trigger_modes[i]}")
            trigger_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            trigger_button.setFixedWidth(120)
            trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx))
            button_layout.addWidget(trigger_button, row, 1)

            self.channel_buttons.append(button)
            self.trigger_mode_buttons.append(trigger_button)

        # Baud Rate Selection
        self.baud_rate_label = QLabel("Baud Rate:")
        button_layout.addWidget(self.baud_rate_label, self.channels, 0)

        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.addItems([str(br) for br in self.baud_rates])
        self.baud_rate_combo.setCurrentText(str(self.default_baud_rate))
        self.baud_rate_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.baud_rate_combo.setFixedWidth(100)
        button_layout.addWidget(self.baud_rate_combo, self.channels, 1)
        self.baud_rate_combo.currentIndexChanged.connect(self.handle_baud_rate_change)

        # Control buttons layout
        control_buttons_layout = QHBoxLayout()

        self.toggle_button = QPushButton("Start")
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.toggle_button.setFixedWidth(80)
        self.toggle_button.clicked.connect(self.toggle_reading)
        control_buttons_layout.addWidget(self.toggle_button)

        self.single_button = QPushButton("Single")
        self.single_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.single_button.setFixedWidth(80)
        self.single_button.clicked.connect(self.start_single_capture)
        control_buttons_layout.addWidget(self.single_button)

        # Add control buttons layout to the button_layout
        button_layout.addLayout(control_buttons_layout, self.channels + 1, 0, 1, 2)

        # Adjust the stretch factors of the plot_layout
        plot_layout.setStretchFactor(self.graph_layout, 1)
        plot_layout.setStretchFactor(button_widget, 0)

        # Initialize other components
        self.channel_visibility = [False] * self.channels

    def is_light_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5

    def reset_channel_to_default(self, idx):
        # Reset the channel configuration to default settings
        default_config = {
            'data_channel': idx + 1,
            'polarity': 'Standard',
            'stop_bits': 1,
            'data_format': 'Hexadecimal',
            'enabled': False,
        }
        self.uart_configs[idx] = default_config
        print(f"Channel {idx+1} reset to default configuration: {default_config}")

        # Reset the button's label to default
        self.channel_buttons[idx].setText(self.channel_buttons[idx].default_label)

        # Update trigger mode button
        self.current_trigger_modes[idx] = 'No Trigger'
        self.trigger_mode_buttons[idx].setText(f"Trigger - {self.current_trigger_modes[idx]}")

        # Update worker's UART configurations
        self.worker.uart_configs[idx] = self.uart_configs[idx]

        # Update curve visibility and color
        is_checked = self.channel_visibility[idx]
        curve = self.curves[idx]
        curve.setVisible(is_checked)
        curve.setPen(pg.mkPen(color=self.colors[idx % len(self.colors)], width=2))

        # Clear data buffers
        self.clear_data_buffers()

        # Reset button style to default
        self.channel_buttons[idx].setStyleSheet("")

        print(f"Channel {idx+1} has been reset to default settings.")

    def handle_baud_rate_change(self):
        baud_rate_str = self.baud_rate_combo.currentText()
        try:
            self.baud_rate = int(baud_rate_str)
            # Set sampling frequency to baud_rate * 16
            self.sample_rate = self.baud_rate * 16
            print(f"Baud Rate set to {self.baud_rate} bps, Sample Rate set to {self.sample_rate} Hz")
            # Update the sample timer or any other necessary configurations
            period = (72 * 10**6) / self.sample_rate
            self.updateSampleTimer(int(period))
            self.plot.setXRange(0, 200 / self.sample_rate, padding=0)
            self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)
        except ValueError as e:
            print(f"Invalid baud rate: {e}")

    def updateSampleTimer(self, period):
        self.period = period
        try:
            self.worker.serial.write(b'5')
            time.sleep(0.001)
            # Send first byte
            selected_bits = (period >> 24) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.001)
            # Send second byte
            selected_bits = (period >> 16) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.001)
            self.worker.serial.write(b'6')
            time.sleep(0.001)
            # Send third byte
            selected_bits = (period >> 8) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.001)
            # Send fourth byte
            selected_bits = period & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.001)
        except Exception as e:
            print(f"Failed to update sample timer: {e}")

    def toggle_reading(self):
        if self.is_reading:
            self.send_stop_message()
            self.stop_reading()
            self.toggle_button.setText("Start")
            self.single_button.setEnabled(True)
            self.toggle_button.setStyleSheet("")
        else:
            self.is_single_capture = False
            self.send_start_message()
            self.start_reading()
            self.toggle_button.setText("Running")
            self.single_button.setEnabled(True)
            self.toggle_button.setStyleSheet("background-color: #00FF77; color: black;")

    def send_start_message(self):
        if self.worker.serial.is_open:
            try:
                self.worker.serial.write(b'0')
                time.sleep(0.001)
                self.worker.serial.write(b'0')
                time.sleep(0.001)
                self.worker.serial.write(b'0')
                print("Sent 'start' command to device")
            except serial.SerialException as e:
                print(f"Failed to send 'start' command: {str(e)}")
        else:
            print("Serial connection is not open")

    def send_stop_message(self):
        if self.worker.serial.is_open:
            try:
                self.worker.serial.write(b'1')
                time.sleep(0.001)
                self.worker.serial.write(b'1')
                time.sleep(0.001)
                self.worker.serial.write(b'1')
                print("Sent 'stop' command to device")
            except serial.SerialException as e:
                print(f"Failed to send 'stop' command: {str(e)}")
        else:
            print("Serial connection is not open")

    def start_reading(self):
        if not self.is_reading:
            self.is_reading = True
            self.timer.start(1)

    def stop_reading(self):
        if self.is_reading:
            self.is_reading = False
            self.timer.stop()

    def start_single_capture(self):
        if not self.is_reading:
            self.clear_data_buffers()
            self.is_single_capture = True
            self.send_start_message()
            self.start_reading()
            self.single_button.setEnabled(False)
            self.toggle_button.setEnabled(False)
            self.single_button.setStyleSheet("background-color: #00FF77; color: black;")

    def stop_single_capture(self):
        self.is_single_capture = False
        self.stop_reading()
        self.send_stop_message()
        self.single_button.setEnabled(True)
        self.toggle_button.setEnabled(True)
        self.toggle_button.setText("Start")
        self.single_button.setStyleSheet("")

    def clear_data_buffers(self):
        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]
        self.total_samples = 0  # Reset total samples

        # Remove all cursors
        for idx in range(self.channels):
            for cursor_info in self.cursors_per_channel[idx]:
                self.plot.removeItem(cursor_info['line'])
                self.plot.removeItem(cursor_info['label'])
            self.cursors_per_channel[idx] = []

        # Reset worker's decoding states
        self.worker.reset_decoding_states()

    def handle_data_value(self, data_value, sample_idx):
        if self.is_reading:
            # Store raw data for plotting
            for i in range(self.channels):
                bit = (data_value >> i) & 1
                self.data_buffer[i].append(bit)
            self.total_samples += 1  # Increment total samples

            # Check if buffers are full
            if all(len(buf) >= self.bufferSize for buf in self.data_buffer):
                if self.is_single_capture:
                    # In single capture mode, stop acquisition
                    self.stop_single_capture()
                else:
                    # In continuous mode, reset buffers and cursors
                    self.clear_data_buffers()
                    self.clear_decoded_text()

    def clear_decoded_text(self):
        # Clear all decoded messages per channel
        for idx in range(self.channels):
            self.decoded_messages_per_channel[idx] = []
        # Cursors are already cleared in clear_data_buffers

    def display_decoded_message(self, decoded_data):
        uart_idx = decoded_data['uart_idx']
        if not self.channel_visibility[uart_idx]:
            return  # Do not display if the channel is not enabled
        data_format = self.uart_configs[uart_idx].get('data_format', 'Hexadecimal')
        event = decoded_data.get('event', None)
        sample_idx = decoded_data.get('sample_idx', None)

        if event == 'DATA':
            data_str = decoded_data.get('data', '')
            label_text = f"Data: {data_str}"
            self.create_cursor(uart_idx, sample_idx, label_text)

    def create_cursor(self, uart_idx, sample_idx, label_text):
        # Cursor color
        cursor_color = '#00F5FF'

        # Calculate y-position above the data signal
        y_position = uart_idx * 2 + 1  # Adjust as needed

        x = 0  # Initial x position, will be updated in update_plot

        # Create line data
        line = pg.PlotDataItem([x, x], [y_position, y_position + 1], pen=pg.mkPen(color=cursor_color, width=2))
        self.plot.addItem(line)
        # Add a label
        label = pg.TextItem(text=label_text, anchor=(0.5, 1.0), color=cursor_color)
        font = QFont("Arial", 12)
        label.setFont(font)
        self.plot.addItem(label)
        # Store the line, label, and sample index
        self.cursors_per_channel[uart_idx].append({
            'line': line,
            'label': label,
            'sample_idx': sample_idx,
            'y_position': y_position,
        })

    def update_plot(self):
        num_samples = len(self.data_buffer[0])
        if num_samples > 1:
            t = np.arange(num_samples) / self.sample_rate

            for i in range(self.channels):
                if self.channel_visibility[i]:
                    data = list(self.data_buffer[i])
                    # Prepare data for plotting
                    square_wave_time = []
                    square_wave_data = []
                    for j in range(1, num_samples):
                        square_wave_time.extend([t[j - 1], t[j]])
                        level = data[j - 1] + i * 2  # Offset per channel
                        square_wave_data.extend([level, level])
                        if data[j] != data[j - 1]:
                            square_wave_time.append(t[j])
                            level = data[j] + i * 2
                            square_wave_data.append(level)
                    self.curves[i].setData(square_wave_time, square_wave_data)
                else:
                    self.curves[i].setVisible(False)

                # --- Update Cursors ---
                cursors_to_remove = []
                for cursor_info in self.cursors_per_channel[i]:
                    sample_idx = cursor_info['sample_idx']
                    idx_in_buffer = sample_idx - (self.total_samples - num_samples)
                    if 0 <= idx_in_buffer < num_samples:
                        cursor_time = t[int(idx_in_buffer)]
                        # Update the line position
                        x = cursor_time
                        y_position = cursor_info['y_position']
                        cursor_info['line'].setData([x, x], [y_position, y_position + 1])
                        # Update the label position
                        label_offset_x = (t[1] - t[0]) * 5  # Adjust label offset as needed
                        cursor_info['label'].setPos(x + label_offset_x, y_position)
                        cursor_info['x_pos'] = x + label_offset_x  # Store x position for overlap checking
                    else:
                        # Cursor is no longer in the buffer, remove it
                        self.plot.removeItem(cursor_info['line'])
                        self.plot.removeItem(cursor_info['label'])
                        cursors_to_remove.append(cursor_info)
                # Remove cursors that are no longer in buffer
                for cursor_info in cursors_to_remove:
                    self.cursors_per_channel[i].remove(cursor_info)
        else:
            # Clear the curves if no data
            for curve in self.curves:
                curve.setData([], [])

    def closeEvent(self, event):
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()

    def open_configuration_dialog(self, idx):
        current_config = self.uart_configs[idx]
        dialog = UARTConfigDialog(current_config, parent=self)
        if dialog.exec():
            new_config = dialog.get_configuration()
            self.uart_configs[idx].update(new_config)
            self.uart_configs[idx]['enabled'] = self.channel_visibility[idx]
            print(f"UART configuration for channel {idx+1} updated: {new_config}")
            # Update the button label
            self.channel_buttons[idx].setText(f"UART {idx+1}\nCh{self.uart_configs[idx]['data_channel']}")
            # Update worker's UART configuration
            self.worker.uart_configs[idx] = self.uart_configs[idx]
            # Clear data buffers if necessary
            self.clear_data_buffers()

    def toggle_channel(self, idx, is_checked):
        self.channel_visibility[idx] = is_checked  # Update the visibility list
        self.uart_configs[idx]['enabled'] = is_checked  # Update the enabled status in config

        # Update curve visibility
        curve = self.curves[idx]
        curve.setVisible(is_checked)

        button = self.channel_buttons[idx]
        if is_checked:
            color = self.colors[idx % len(self.colors)]
            text_color = 'black' if self.is_light_color(color) else 'white'
            button.setStyleSheet(f"QPushButton {{ background-color: {color}; color: {text_color}; "
                                f"border: 1px solid #555; border-radius: 5px; padding: 5px; "
                                f"text-align: left; }}")
        else:
            button.setStyleSheet("")

    def toggle_trigger_mode(self, idx):
        # Cycle through trigger modes
        current_mode = self.current_trigger_modes[idx]
        current_mode_idx = self.trigger_mode_options.index(current_mode)
        new_mode_idx = (current_mode_idx + 1) % len(self.trigger_mode_options)
        new_mode = self.trigger_mode_options[new_mode_idx]
        self.current_trigger_modes[idx] = new_mode
        self.trigger_mode_buttons[idx].setText(f"Trigger - {new_mode}")
        self.worker.set_trigger_mode(idx, new_mode)
        self.send_trigger_edge_command()
        self.send_trigger_pins_command()

    def send_trigger_edge_command(self):
        command_int = get_trigger_edge_command(self.current_trigger_modes)
        command_str = str(command_int)
        try:
            self.worker.serial.write(b'2')
            time.sleep(0.01)
            self.worker.serial.write(b'0')
            time.sleep(0.01)
            self.worker.serial.write(command_str.encode('utf-8'))
            time.sleep(0.01)
        except serial.SerialException as e:
            print(f"Failed to send trigger edge command: {str(e)}")

    def send_trigger_pins_command(self):
        command_int = get_trigger_pins_command(self.current_trigger_modes)
        command_str = str(command_int)
        try:
            self.worker.serial.write(b'3')
            time.sleep(0.001)
            self.worker.serial.write(b'0')
            time.sleep(0.001)
            self.worker.serial.write(command_str.encode('utf-8'))
        except serial.SerialException as e:
            print(f"Failed to send trigger pins command: {str(e)}")


if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    port = 'COM3'  # Replace with your serial port
    baudrate = 115200  # Replace with your serial port baud rate
    bufferSize = 1024
    uart_display = UARTDisplay(port, baudrate, bufferSize)
    uart_display.show()
    sys.exit(app.exec())

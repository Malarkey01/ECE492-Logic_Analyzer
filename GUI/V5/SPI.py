# SPI.py

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
    QSpinBox,
    QRadioButton,
    QButtonGroup,
    QSizePolicy,
)
from PyQt6.QtGui import QIcon, QIntValidator
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from collections import deque
from InterfaceCommands import (
    get_trigger_edge_command,
    get_trigger_pins_command,
)
from aesthetic import get_icon

bufferSize = 1024    # Default is 1024
preTriggerBufferSize = 1000  # Default is 1000

class SerialWorker(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.trigger_modes = ['No Trigger'] * channels  # One per channel
        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def set_trigger_mode(self, channel_idx, mode):
        self.trigger_modes[channel_idx] = mode

    def run(self):
        pre_trigger_buffer_size = 1000
        data_buffer = deque(maxlen=pre_trigger_buffer_size)
        triggered = [False] * self.channels  # One per channel

        while self.is_running:
            if self.serial.in_waiting:
                raw_data = self.serial.read(self.serial.in_waiting).splitlines()
                for line in raw_data:
                    try:
                        data_value = int(line.strip())
                        data_buffer.append(data_value)

                        for i in range(self.channels):
                            if not triggered[i]:
                                last_value = data_buffer[-2] if len(data_buffer) >= 2 else None
                                if last_value is not None:
                                    current_line = (data_value >> i) & 1
                                    last_line = (last_value >> i) & 1

                                    mode = self.trigger_modes[i]
                                    if mode != 'No Trigger':
                                        if mode == 'Rising Edge' and last_line == 0 and current_line == 1:
                                            triggered[i] = True
                                            print(f"Trigger condition met on channel {i+1}: Rising Edge")
                                        elif mode == 'Falling Edge' and last_line == 1 and current_line == 0:
                                            triggered[i] = True
                                            print(f"Trigger condition met on channel {i+1}: Falling Edge")

                        if any(triggered) or all(mode == 'No Trigger' for mode in self.trigger_modes):
                            self.data_ready.emit([data_value])

                    except ValueError:
                        continue

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
    def __init__(self, label, parent=None):
        super().__init__(label, parent)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.default_label = label

    def show_context_menu(self, position):
        menu = QMenu()
        rename_action = menu.addAction("Rename")
        reset_action = menu.addAction("Reset to Default")
        action = menu.exec(self.mapToGlobal(position))
        if action == rename_action:
            new_label, ok = QInputDialog.getText(
                self, "Rename Button", "Enter new label:", text=self.text()
            )
            if ok and new_label:
                self.setText(new_label)
        elif action == reset_action:
            self.setText(self.default_label)


class SPIChannelButton(EditableButton):
    configure_requested = pyqtSignal(int)  # Signal to notify when configure is requested

    def __init__(self, label, group_idx, parent=None):
        super().__init__(label, parent)
        self.group_idx = group_idx  # Store the index of the SPI group

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
        elif action == configure_action:
            self.configure_requested.emit(self.group_idx)  # Emit signal to open configuration dialog


class SPIConfigDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SPI Configuration")
        self.current_config = current_config  # Dictionary to hold current configurations

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Slave Select Channel Selection
        ss_layout = QHBoxLayout()
        ss_label = QLabel("Slave Select (SS) Channel:")
        self.ss_combo = QComboBox()
        self.ss_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.ss_combo.setCurrentIndex(self.current_config.get('ss_channel', 0))
        ss_layout.addWidget(ss_label)
        ss_layout.addWidget(self.ss_combo)
        layout.addLayout(ss_layout)

        # Data Channel Selection
        data_layout = QHBoxLayout()
        data_label = QLabel("Data Channel:")
        self.data_combo = QComboBox()
        self.data_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.data_combo.setCurrentIndex(self.current_config.get('data_channel', 1))
        data_layout.addWidget(data_label)
        data_layout.addWidget(self.data_combo)
        layout.addLayout(data_layout)

        # Clock Channel Selection
        clock_layout = QHBoxLayout()
        clock_label = QLabel("Clock Channel:")
        self.clock_combo = QComboBox()
        self.clock_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.clock_combo.setCurrentIndex(self.current_config.get('clock_channel', 2))
        clock_layout.addWidget(clock_label)
        clock_layout.addWidget(self.clock_combo)
        layout.addLayout(clock_layout)

        # Number of Bits Selection
        bits_layout = QHBoxLayout()
        bits_label = QLabel("Number of Bits:")
        self.bits_spinbox = QSpinBox()
        self.bits_spinbox.setRange(1, 32)
        self.bits_spinbox.setValue(self.current_config.get('num_bits', 8))
        bits_layout.addWidget(bits_label)
        bits_layout.addWidget(self.bits_spinbox)
        layout.addLayout(bits_layout)

        # Bit Order Selection
        bit_order_layout = QHBoxLayout()
        bit_order_label = QLabel("Bit Order:")
        self.bit_order_group = QButtonGroup(self)
        self.msb_first_radio = QRadioButton("MSB First")
        self.lsb_first_radio = QRadioButton("LSB First")
        self.bit_order_group.addButton(self.msb_first_radio)
        self.bit_order_group.addButton(self.lsb_first_radio)
        if self.current_config.get('bit_order', 'MSB') == 'MSB':
            self.msb_first_radio.setChecked(True)
        else:
            self.lsb_first_radio.setChecked(True)
        bit_order_layout.addWidget(bit_order_label)
        bit_order_layout.addWidget(self.msb_first_radio)
        bit_order_layout.addWidget(self.lsb_first_radio)
        layout.addLayout(bit_order_layout)

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
        bit_order = 'MSB' if self.msb_first_radio.isChecked() else 'LSB'
        return {
            'ss_channel': self.ss_combo.currentIndex(),
            'data_channel': self.data_combo.currentIndex(),
            'clock_channel': self.clock_combo.currentIndex(),
            'num_bits': self.bits_spinbox.value(),
            'bit_order': bit_order,
            'data_format': self.format_combo.currentText(),
        }


class SPIDisplay(QWidget):
    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.period = 65454
        self.num_samples = 0
        self.port = port
        self.baudrate = baudrate
        self.channels = channels

        self.data_buffer = [deque(maxlen=bufferSize) for _ in range(8)]  # 8 channels
        self.channel_visibility = [False] * self.channels  # Visibility for each channel

        self.is_single_capture = False

        self.current_trigger_modes = ['No Trigger'] * self.channels
        self.trigger_mode_options = ['No Trigger', 'Rising Edge', 'Falling Edge']

        self.sample_rate = 1000  # Default sample rate in Hz

        # Initialize group configurations with default values
        self.group_configs = []
        for i in range(2):  # Adjust based on number of SPI groups
            self.group_configs.append({
                'ss_channel': i * 3,
                'data_channel': i * 3 + 1,
                'clock_channel': i * 3 + 2,
                'num_bits': 8,
                'bit_order': 'MSB',
                'data_format': 'Hexadecimal',
            })

        self.setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading = False

        self.worker = SerialWorker(self.port, self.baudrate, channels=self.channels)
        self.worker.data_ready.connect(self.handle_data)
        self.worker.start()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        self.graph_layout = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.graph_layout)

        self.plot = self.graph_layout.addPlot(viewBox=FixedYViewBox())

        self.plot.setXRange(0, 200 / self.sample_rate, padding=0)
        self.plot.setLimits(xMin=0, xMax=bufferSize / self.sample_rate)
        self.plot.setYRange(-2, 2 * self.channels, padding=0)  # 8 channels
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)
        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)
        self.plot.setLabel('bottom', 'Time', units='s')

        self.colors = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF', '#FFFF33', '#FFA500', '#00F5FF', '#BFFF00']
        self.curves = []
        for i in range(self.channels):  # 8 channels
            color = self.colors[i % len(self.colors)]
            curve = self.plot.plot(pen=pg.mkPen(color=color, width=4))
            curve.setVisible(self.channel_visibility[i])
            self.curves.append(curve)

        button_layout = QGridLayout()
        main_layout.addLayout(button_layout)

        self.channel_buttons = []
        self.ss_trigger_mode_buttons = []
        self.data_trigger_mode_buttons = []
        self.clock_trigger_mode_buttons = []

        for i in range(len(self.group_configs)):
            row = i * 3  # Increment by 3 for each group

            group_config = self.group_configs[i]
            ss_channel = group_config['ss_channel']
            data_channel = group_config['data_channel']
            clock_channel = group_config['clock_channel']

            label = f"SPI {i+1}\nCh{ss_channel+1}:SS\nCh{data_channel+1}:Data\nCh{clock_channel+1}:Clk"
            button = SPIChannelButton(label, group_idx=i)

            # Set size policy to expand vertically
            button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel_group(idx, checked))
            button.configure_requested.connect(self.open_configuration_dialog)
            button_layout.addWidget(button, row, 0, 3, 1)  # Span 3 rows, 1 column

            # SS Trigger Mode Button
            ss_trigger_button = QPushButton(f"SS - {self.current_trigger_modes[ss_channel]}")
            ss_trigger_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            ss_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'SS'))
            button_layout.addWidget(ss_trigger_button, row, 1)
            self.ss_trigger_mode_buttons.append(ss_trigger_button)

            # Data Trigger Mode Button
            data_trigger_button = QPushButton(f"Data - {self.current_trigger_modes[data_channel]}")
            data_trigger_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            data_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'Data'))
            button_layout.addWidget(data_trigger_button, row + 1, 1)
            self.data_trigger_mode_buttons.append(data_trigger_button)

            # Clock Trigger Mode Button
            clock_trigger_button = QPushButton(f"Clk - {self.current_trigger_modes[clock_channel]}")
            clock_trigger_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            clock_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'Clk'))
            button_layout.addWidget(clock_trigger_button, row + 2, 1)
            self.clock_trigger_mode_buttons.append(clock_trigger_button)

            # Set row stretches to distribute space equally
            button_layout.setRowStretch(row, 1)
            button_layout.setRowStretch(row + 1, 1)
            button_layout.setRowStretch(row + 2, 1)

            self.channel_buttons.append(button)

        # Calculate the starting row for the next set of widgets
        next_row = len(self.group_configs) * 3  # Number of groups * 3 rows per group

        # Sample Rate input
        self.sample_rate_label = QLabel("Sample Rate (Hz):")
        button_layout.addWidget(self.sample_rate_label, next_row, 0)

        self.sample_rate_input = QLineEdit()
        self.sample_rate_input.setValidator(QIntValidator(1, 5000000))
        self.sample_rate_input.setText("1000")
        button_layout.addWidget(self.sample_rate_input, next_row, 1)
        self.sample_rate_input.returnPressed.connect(self.handle_sample_rate_input)

        # Number of Samples input
        self.num_samples_label = QLabel("Number of Samples:")
        button_layout.addWidget(self.num_samples_label, next_row + 1, 0)

        self.num_samples_input = QLineEdit()
        self.num_samples_input.setValidator(QIntValidator(1, 1023))
        self.num_samples_input.setText("300")
        button_layout.addWidget(self.num_samples_input, next_row + 1, 1)
        self.num_samples_input.returnPressed.connect(self.send_num_samples_command)

        # Control buttons layout
        control_buttons_layout = QHBoxLayout()

        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_reading)
        control_buttons_layout.addWidget(self.toggle_button)

        self.single_button = QPushButton("Single")
        self.single_button.clicked.connect(self.start_single_capture)
        control_buttons_layout.addWidget(self.single_button)

        button_layout.addLayout(control_buttons_layout, next_row + 2, 0, 1, 2)

        # Cursor for measurement
        self.cursor = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen(color='y', width=2))
        self.plot.addItem(self.cursor)

        self.cursor_label = pg.TextItem(anchor=(0, 1), color='y')
        self.plot.addItem(self.cursor_label)
        self.update_cursor_position()
        self.cursor.sigPositionChanged.connect(self.update_cursor_position)

    def handle_sample_rate_input(self):
        try:
            sample_rate = int(self.sample_rate_input.text())
            if sample_rate <= 0:
                raise ValueError("Sample rate must be positive")
            self.sample_rate = sample_rate  # Store sample_rate
            period = (72 * 10**6) / sample_rate
            print(f"Sample Rate set to {sample_rate} Hz, Period: {period} ticks")
            self.updateSampleTimer(int(period))
            self.plot.setXRange(0, 200 / self.sample_rate, padding=0)
            self.plot.setLimits(xMin=0, xMax=bufferSize / self.sample_rate)
        except ValueError as e:
            print(f"Invalid sample rate: {e}")

    def send_num_samples_command(self):
        try:
            num_samples = int(self.num_samples_input.text())
            self.num_samples = num_samples
            self.updateTriggerTimer()
        except ValueError as e:
            print(f"Invalid number of samples: {e}")

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

    def updateTriggerTimer(self):
        sampling_freq = 72e6 / self.period
        trigger_freq = sampling_freq / self.num_samples
        period16 = 72e6 / trigger_freq
        prescaler = 1
        if period16 > 2**16:
            prescaler = math.ceil(period16 / (2**16))
            period16 = int((72e6 / prescaler) / trigger_freq)
        print(f"Period timer 16 set to {period16}, Timer 16 prescalar is {prescaler}")
        try:
            self.worker.serial.write(b'4')
            time.sleep(0.01)
            # Send high byte
            selected_bits = (int(period16) >> 8) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
            # Send low byte
            selected_bits = int(period16) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
            # Update Prescaler
            self.worker.serial.write(b'7')
            time.sleep(0.01)
            # Send high byte
            selected_bits = (prescaler >> 8) & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
            # Send low byte
            selected_bits = prescaler & 0xFF
            self.worker.serial.write(str(selected_bits).encode('utf-8'))
            time.sleep(0.01)
        except Exception as e:
            print(f"Failed to update trigger timer: {e}")

    def toggle_trigger_mode(self, group_idx, line):
        group_config = self.group_configs[group_idx]
        if line == 'SS':
            channel_idx = group_config['ss_channel']
            button = self.ss_trigger_mode_buttons[group_idx]
        elif line == 'Data':
            channel_idx = group_config['data_channel']
            button = self.data_trigger_mode_buttons[group_idx]
        elif line == 'Clk':
            channel_idx = group_config['clock_channel']
            button = self.clock_trigger_mode_buttons[group_idx]
        else:
            return

        # Cycle through trigger modes
        current_mode = self.current_trigger_modes[channel_idx]
        current_mode_idx = self.trigger_mode_options.index(current_mode)
        new_mode_idx = (current_mode_idx + 1) % len(self.trigger_mode_options)
        new_mode = self.trigger_mode_options[new_mode_idx]
        self.current_trigger_modes[channel_idx] = new_mode
        button.setText(f"{line} - {new_mode}")
        self.worker.set_trigger_mode(channel_idx, new_mode)
        self.send_trigger_edge_command()
        self.send_trigger_pins_command()

    def is_light_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5

    def toggle_channel_group(self, group_idx, is_checked):
        group_config = self.group_configs[group_idx]
        ss_idx = group_config['ss_channel']
        data_idx = group_config['data_channel']
        clk_idx = group_config['clock_channel']
        self.channel_visibility[ss_idx] = is_checked
        self.channel_visibility[data_idx] = is_checked
        self.channel_visibility[clk_idx] = is_checked
        self.curves[ss_idx].setVisible(is_checked)
        self.curves[data_idx].setVisible(is_checked)
        self.curves[clk_idx].setVisible(is_checked)

        button = self.channel_buttons[group_idx]
        if is_checked:
            color = self.colors[group_idx % len(self.colors)]
            text_color = 'black' if self.is_light_color(color) else 'white'
            button.setStyleSheet(f"QPushButton {{ background-color: {color}; color: {text_color}; "
                                 f"border: 1px solid #555; border-radius: 5px; padding: 5px; "
                                 f"text-align: left; }}")
        else:
            button.setStyleSheet("")

    def toggle_reading(self):
        if self.is_reading:
            self.send_stop_message()
            self.stop_reading()
            self.toggle_button.setText("Run")
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
        self.data_buffer = [deque(maxlen=bufferSize) for _ in range(8)]  # 8 channels

    def handle_data(self, data_list):
        if self.is_reading:
            for data_value in data_list:
                # Store raw data for plotting
                for i in range(8):
                    bit = (data_value >> i) & 1
                    self.data_buffer[i].append(bit)
            if self.is_single_capture and all(len(buf) >= bufferSize for buf in self.data_buffer):
                self.stop_single_capture()

    def update_plot(self):
        for i in range(8):
            if self.channel_visibility[i]:
                inverted_index = 8 - i - 1
                num_samples = len(self.data_buffer[i])
                if num_samples > 1:
                    t = np.arange(num_samples) / self.sample_rate
                    square_wave_time = []
                    square_wave_data = []
                    for j in range(1, num_samples):
                        square_wave_time.extend([t[j - 1], t[j]])
                        level = self.data_buffer[i][j - 1] + inverted_index * 2
                        square_wave_data.extend([level, level])
                        if self.data_buffer[i][j] != self.data_buffer[i][j - 1]:
                            square_wave_time.append(t[j])
                            level = self.data_buffer[i][j] + inverted_index * 2
                            square_wave_data.append(level)
                    self.curves[i].setData(square_wave_time, square_wave_data)

    def update_cursor_position(self):
        cursor_pos = self.cursor.pos().x()
        self.cursor_label.setText(f"Cursor: {cursor_pos:.6f} s")
        self.cursor_label.setPos(cursor_pos, 8 * 2 - 1)

    def closeEvent(self, event):
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()

    def open_configuration_dialog(self, group_idx):
        current_config = self.group_configs[group_idx]
        dialog = SPIConfigDialog(current_config, parent=self)
        if dialog.exec():
            new_config = dialog.get_configuration()
            self.group_configs[group_idx] = new_config
            print(f"Configuration for group {group_idx+1} updated: {new_config}")
            # Update labels on the button to reflect new channel assignments
            ss_channel = new_config['ss_channel']
            data_channel = new_config['data_channel']
            clock_channel = new_config['clock_channel']
            label = f"SPI {group_idx+1}\nCh{ss_channel+1}:SS\nCh{data_channel+1}:Data\nCh{clock_channel+1}:Clk"
            self.channel_buttons[group_idx].setText(label)
            # Update trigger buttons to reflect new channels
            self.ss_trigger_mode_buttons[group_idx].setText(f"SS - {self.current_trigger_modes[ss_channel]}")
            self.data_trigger_mode_buttons[group_idx].setText(f"Data - {self.current_trigger_modes[data_channel]}")
            self.clock_trigger_mode_buttons[group_idx].setText(f"Clk - {self.current_trigger_modes[clock_channel]}")
            # Clear data buffers
            self.clear_data_buffers()

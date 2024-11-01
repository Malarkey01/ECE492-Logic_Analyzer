# I2C.py

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


class I2CChannelButton(EditableButton):
    configure_requested = pyqtSignal(int)  # Signal to notify when configure is requested

    def __init__(self, label, group_idx, parent=None):
        super().__init__(label, parent)
        self.group_idx = group_idx  # Store the index of the I2C group

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


class I2CConfigDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("I2C Configuration")
        self.current_config = current_config  # Dictionary to hold current configurations

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Clock Channel Selection
        clock_layout = QHBoxLayout()
        clock_label = QLabel("Clock Channel:")
        self.clock_combo = QComboBox()
        self.clock_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.clock_combo.setCurrentIndex(self.current_config.get('clock_channel', 2) - 1)
        clock_layout.addWidget(clock_label)
        clock_layout.addWidget(self.clock_combo)
        layout.addLayout(clock_layout)

        # Data Channel Selection
        data_layout = QHBoxLayout()
        data_label = QLabel("Data Channel:")
        self.data_combo = QComboBox()
        self.data_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.data_combo.setCurrentIndex(self.current_config.get('data_channel', 1) - 1)
        data_layout.addWidget(data_label)
        data_layout.addWidget(self.data_combo)
        layout.addLayout(data_layout)

        # Address Width Selection
        address_layout = QHBoxLayout()
        address_label = QLabel("Address Width:")
        self.address_group = QButtonGroup(self)
        self.address_7bit = QRadioButton("7 bits")
        self.address_8bit = QRadioButton("8 bits")
        self.address_group.addButton(self.address_7bit)
        self.address_group.addButton(self.address_8bit)
        address_layout.addWidget(address_label)
        address_layout.addWidget(self.address_7bit)
        address_layout.addWidget(self.address_8bit)
        layout.addLayout(address_layout)

        if self.current_config.get('address_width', 8) == 7:
            self.address_7bit.setChecked(True)
        else:
            self.address_8bit.setChecked(True)

        # Data Format Selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Data Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Binary", "Decimal", "Hexadecimal", "BCD", "ASCII"])
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
            'clock_channel': self.clock_combo.currentIndex() + 1,
            'data_channel': self.data_combo.currentIndex() + 1,
            'address_width': 7 if self.address_7bit.isChecked() else 8,
            'data_format': self.format_combo.currentText(),
        }


class I2CDisplay(QWidget):
    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.period = 65454
        self.num_samples = 0
        self.port = port
        self.baudrate = baudrate
        self.channels = channels

        self.data_buffer = [deque(maxlen=bufferSize) for _ in range(self.channels)]  # 8 channels
        self.channel_visibility = [False] * self.channels  # Visibility for each channel

        self.is_single_capture = False

        self.current_trigger_modes = ['No Trigger'] * self.channels
        self.trigger_mode_options = ['No Trigger', 'Rising Edge', 'Falling Edge']

        self.sample_rate = 1000  # Default sample rate in Hz

        self.group_configs = [{} for _ in range(4)]  # Store configurations for each group

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
        self.sda_trigger_mode_buttons = []
        self.scl_trigger_mode_buttons = []

        for i in range(4):
            row = i * 2  # Increment by 2 for each group
            sda_channel = 2 * i
            scl_channel = 2 * i + 1
            label = f"I2C {i+1}\nCh{sda_channel+1}:SDA\nCh{scl_channel+1}:SCL"
            button = I2CChannelButton(label, group_idx=i)

            # Set size policy to expand vertically
            button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel_group(idx, checked))
            button.configure_requested.connect(self.open_configuration_dialog)
            button_layout.addWidget(button, row, 0, 2, 1)  # Span 2 rows, 1 column

            # SDA Trigger Mode Button
            sda_trigger_button = QPushButton(f"SDA - {self.current_trigger_modes[sda_channel]}")

            # Set size policy to expand vertically
            sda_trigger_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

            sda_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'SDA'))
            button_layout.addWidget(sda_trigger_button, row, 1)

            # SCL Trigger Mode Button
            scl_trigger_button = QPushButton(f"SCL - {self.current_trigger_modes[scl_channel]}")

            # Set size policy to expand vertically
            scl_trigger_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

            scl_trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx, 'SCL'))
            button_layout.addWidget(scl_trigger_button, row + 1, 1)

            # Set row stretches to distribute space equally
            button_layout.setRowStretch(row, 1)
            button_layout.setRowStretch(row + 1, 1)

            self.channel_buttons.append(button)
            self.sda_trigger_mode_buttons.append(sda_trigger_button)
            self.scl_trigger_mode_buttons.append(scl_trigger_button)

        # Calculate the starting row for the next set of widgets
        next_row = 4 * 2  # 4 groups * 2 rows per group

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
        if line == 'SDA':
            channel_idx = 2 * group_idx
            button = self.sda_trigger_mode_buttons[group_idx]
        elif line == 'SCL':
            channel_idx = 2 * group_idx + 1
            button = self.scl_trigger_mode_buttons[group_idx]
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
        sda_idx = 2 * group_idx
        scl_idx = 2 * group_idx + 1
        self.channel_visibility[sda_idx] = is_checked
        self.channel_visibility[scl_idx] = is_checked
        self.curves[sda_idx].setVisible(is_checked)
        self.curves[scl_idx].setVisible(is_checked)

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
        self.data_buffer = [deque(maxlen=bufferSize) for _ in range(self.channels)]

    def handle_data(self, data_list):
        if self.is_reading:
            for data_value in data_list:
                # Store raw data for plotting
                for i in range(self.channels):
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
        dialog = I2CConfigDialog(current_config, parent=self)
        if dialog.exec():
            new_config = dialog.get_configuration()
            self.group_configs[group_idx] = new_config
            print(f"Configuration for group {group_idx+1} updated: {new_config}")
            # Update labels on the button to reflect new channel assignments
            sda_channel = new_config['data_channel']
            scl_channel = new_config['clock_channel']
            label = f"I2C {group_idx+1}\nCh{sda_channel}:SDA\nCh{scl_channel}:SCL"
            self.channel_buttons[group_idx].setText(label)
            # Clear data buffers
            self.clear_data_buffers()

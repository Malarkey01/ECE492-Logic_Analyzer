# I2C.py

import sys
import serial
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
)
from PyQt6.QtGui import QIcon, QIntValidator
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
import pyqtgraph as pg
import numpy as np
from aesthetic import get_icon
from InterfaceCommands import (
    get_trigger_edge_command,
    get_trigger_pins_command,
    get_num_samples_command,
)
import time

class SerialWorker(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.trigger_modes = ['No Trigger'] * 8  # Updated to match channel count
        self.trigger_channels = ['SCL'] * 4  # Default to SCL for each group
        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def set_trigger_mode(self, channel_idx, mode):
        self.trigger_modes[channel_idx] = mode

    def set_trigger_channel(self, group_idx, channel_name):
        self.trigger_channels[group_idx] = channel_name

    def run(self):
        pre_trigger_buffer_size = 1000
        data_buffer = []
        triggered = [False] * 4  # 4 groups for I2C

        while self.is_running:
            if self.serial.in_waiting:
                raw_data = self.serial.read(self.serial.in_waiting).splitlines()
                for line in raw_data:
                    try:
                        data_value = int(line.strip())
                        data_buffer.append(data_value)
                        if len(data_buffer) > pre_trigger_buffer_size:
                            data_buffer.pop(0)

                        for i in range(4):
                            if not triggered[i]:
                                last_value = data_buffer[-2] if len(data_buffer) >= 2 else None
                                if last_value is not None:
                                    # Extract bits for SDA and SCL
                                    current_sda = (data_value >> (2 * i)) & 1
                                    current_scl = (data_value >> (2 * i + 1)) & 1
                                    last_sda = (last_value >> (2 * i)) & 1
                                    last_scl = (last_value >> (2 * i + 1)) & 1

                                    # Determine which channel to use for trigger
                                    trigger_channel = self.trigger_channels[i]
                                    if trigger_channel == 'SDA':
                                        current_line = current_sda
                                        last_line = last_sda
                                        channel_idx = 2 * i
                                    else:
                                        current_line = current_scl
                                        last_line = last_scl
                                        channel_idx = 2 * i + 1

                                    mode = self.trigger_modes[channel_idx]
                                    if mode != 'No Trigger':
                                        if mode == 'Rising Edge' and last_line == 0 and current_line == 1:
                                            triggered[i] = True
                                            print(f"Trigger condition met on I2C group {i+1}: Rising Edge on {trigger_channel}")
                                        elif mode == 'Falling Edge' and last_line == 1 and current_line == 0:
                                            triggered[i] = True
                                            print(f"Trigger condition met on I2C group {i+1}: Falling Edge on {trigger_channel}")

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
        super(FixedYViewBox, self).__init__(*args, **kwargs)

    def scaleBy(self, s=None, center=None, x=None, y=None):
        y = 1.0  # Fix y-scaling
        if x is not None:
            pass
        else:
            if s is None:
                x = 1.0
            elif isinstance(s, dict):
                x = s.get('x', 1.0)
            elif isinstance(s, (list, tuple)):
                x = s[0]
            else:
                x = s
        super(FixedYViewBox, self).scaleBy(x=x, y=y, center=center)

    def translateBy(self, t=None, x=None, y=None):
        y = 0.0  # Fix y-translation
        if x is not None:
            pass
        else:
            if t is None:
                x = 0.0
            elif isinstance(t, dict):
                x = t.get('x', 0.0)
            elif isinstance(t, (list, tuple)):
                x = t[0]
            else:
                x = t
        super(FixedYViewBox, self).translateBy(x=x, y=y)


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

class I2CDisplay(QWidget):
    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.channels = channels

        self.data_buffer = [[] for _ in range(8)]  # 8 channels
        self.channel_visibility = [False] * 8  # Visibility for each channel

        self.is_single_capture = False  # Initialize single capture flag

        # Initialize trigger modes per channel
        self.current_trigger_modes = ['No Trigger'] * 8
        # Default trigger channels per group (SCL)
        self.trigger_channels = ['SCL'] * 4

        self.trigger_mode_options = ['No Trigger', 'Rising Edge', 'Falling Edge']
        self.trigger_channel_options = ['SDA', 'SCL']

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

        # Set x-axis to show time units based on sample rate
        self.sample_rate = 1000  # Default sample rate in Hz
        self.plot.setXRange(0, 200 / self.sample_rate, padding=0)
        self.plot.setLimits(xMin=0, xMax=1024 / self.sample_rate)
        self.plot.setYRange(-2, 2 * 8, padding=0)  # 8 channels
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)

        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)

        self.plot.setLabel('bottom', 'Time', units='s')  # Label the x-axis as time

        self.colors = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF', '#FFFF33', '#FFA500', '#00F5FF', '#BFFF00']
        self.curves = []
        for i in range(8):  # 8 channels
            color = self.colors[i % len(self.colors)]
            curve = self.plot.plot(pen=pg.mkPen(color=color, width=2))
            curve.setVisible(self.channel_visibility[i])
            self.curves.append(curve)

        button_layout = QGridLayout()
        main_layout.addLayout(button_layout)

        self.channel_buttons = []
        self.trigger_mode_buttons = []
        self.trigger_channel_buttons = []

        for i in range(4):
            sda_channel = 2 * i + 1
            scl_channel = 2 * i + 2
            label = f"I2C {i+1}\nCh{sda_channel}:SDA\nCh{scl_channel}:SCL"
            button = EditableButton(label)
            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel_group(idx, checked))
            color = self.colors[i % len(self.colors)]
            button_layout.addWidget(button, i, 0)
            self.channel_buttons.append(button)

            # Trigger Mode Button
            trigger_button = QPushButton(self.current_trigger_modes[2 * i + 1])  # Default to mode of SCL
            trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx))
            button_layout.addWidget(trigger_button, i, 1)
            self.trigger_mode_buttons.append(trigger_button)

            # Trigger Channel Button
            trigger_channel_button = QPushButton(self.trigger_channels[i])  # Default to 'SCL'
            trigger_channel_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_channel(idx))
            button_layout.addWidget(trigger_channel_button, i, 2)
            self.trigger_channel_buttons.append(trigger_channel_button)

        # Sample Rate input
        self.sample_rate_label = QLabel("Sample Rate (Hz):")
        button_layout.addWidget(self.sample_rate_label, 4, 0)

        self.sample_rate_input = QLineEdit()
        self.sample_rate_input.setValidator(QIntValidator(1, 5000000))
        self.sample_rate_input.setText("1000")
        button_layout.addWidget(self.sample_rate_input, 4, 1)
        self.sample_rate_input.returnPressed.connect(self.handle_sample_rate_input)

        # Number of Samples input
        self.num_samples_label = QLabel("Number of Samples:")
        button_layout.addWidget(self.num_samples_label, 5, 0)

        self.num_samples_input = QLineEdit()
        self.num_samples_input.setValidator(QIntValidator(1, 1023))
        self.num_samples_input.setText("300")
        button_layout.addWidget(self.num_samples_input, 5, 1)

        # Connect the returnPressed signal to send_num_samples_command
        self.num_samples_input.returnPressed.connect(self.send_num_samples_command)

        # Create a horizontal layout for the Start/Stop and Single buttons
        control_buttons_layout = QHBoxLayout()

        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_reading)
        control_buttons_layout.addWidget(self.toggle_button)

        self.single_button = QPushButton("Single")
        self.single_button.clicked.connect(self.start_single_capture)
        control_buttons_layout.addWidget(self.single_button)

        # Add the control buttons layout to the button_layout
        button_layout.addLayout(control_buttons_layout, 6, 0, 1, 3)

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
            # Calculate period based on sample rate
            period = (72 * 10**6) / sample_rate
            print(f"Sample Rate set to {sample_rate} Hz, Period: {period} ticks")
            self.updateSampleTimer(int(period))
            # Update x-axis range
            self.plot.setXRange(0, 200 / self.sample_rate, padding=0)
            self.plot.setLimits(xMin=0, xMax=1024 / self.sample_rate)
        except ValueError as e:
            print(f"Invalid sample rate: {e}")

    def send_num_samples_command(self):
        try:
            num_samples = int(self.num_samples_input.text())
            msb_value, lsb_value = get_num_samples_command(num_samples)
            msb_str = str(msb_value)
            lsb_str = str(lsb_value)
            if self.worker.serial.is_open:
                # Send MSB value
                self.worker.serial.write(msb_str.encode('utf-8'))
                # Send LSB value
                self.worker.serial.write(lsb_str.encode('utf-8'))
            else:
                print("Serial connection is not open")
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

    # period is a 32-bit integer
    def updateSampleTimer(self, period):
        try:
            # Send in command for upper half of period
            self.worker.serial.write(b'5')
            time.sleep(0.001)
            # Send first two hex bits
            selectedBits = period >> 24
            selectedBits = str(selectedBits).encode('utf-8')
            self.worker.serial.write(selectedBits)
            time.sleep(0.001)
            # Send next two hex bits
            mask = 0x00FF0000
            selectedBits = (period & mask) >> 16
            selectedBits = str(selectedBits).encode('utf-8')
            self.worker.serial.write(selectedBits)
            time.sleep(0.001)
            # Send in command for lower half of period
            self.worker.serial.write(b'6')
            time.sleep(0.001)
            # Send next two hex bits
            mask = 0x0000FF00
            selectedBits = (period & mask) >> 8
            selectedBits = str(selectedBits).encode('utf-8')
            self.worker.serial.write(selectedBits)
            time.sleep(0.001)
            # Send last two hex bits
            mask = 0x000000FF
            selectedBits = (period & mask)
            selectedBits = str(selectedBits).encode('utf-8')
            self.worker.serial.write(selectedBits)
            time.sleep(0.001)
        except Exception as e:
            print(f"Failed to update sample timer: {e}")

    def toggle_trigger_mode(self, group_idx):
        trigger_channel = self.trigger_channels[group_idx]
        if trigger_channel == 'SDA':
            channel_idx = 2 * group_idx
        else:
            channel_idx = 2 * group_idx + 1

        # Cycle through trigger modes
        current_mode_idx = self.trigger_mode_options.index(self.current_trigger_modes[channel_idx])
        new_mode_idx = (current_mode_idx + 1) % len(self.trigger_mode_options)
        new_mode = self.trigger_mode_options[new_mode_idx]
        self.current_trigger_modes[channel_idx] = new_mode
        self.trigger_mode_buttons[group_idx].setText(new_mode)
        self.worker.set_trigger_mode(channel_idx, new_mode)
        self.send_trigger_edge_command()
        self.send_trigger_pins_command()

    def toggle_trigger_channel(self, group_idx):
        # Toggle between 'SDA' and 'SCL'
        current_channel = self.trigger_channels[group_idx]
        new_channel = 'SDA' if current_channel == 'SCL' else 'SCL'
        self.trigger_channels[group_idx] = new_channel
        self.trigger_channel_buttons[group_idx].setText(new_channel)
        self.worker.set_trigger_channel(group_idx, new_channel)
        # Update the trigger mode button text to reflect the trigger mode for the new channel
        if new_channel == 'SDA':
            channel_idx = 2 * group_idx
        else:
            channel_idx = 2 * group_idx + 1
        current_mode = self.current_trigger_modes[channel_idx]
        self.trigger_mode_buttons[group_idx].setText(current_mode)
        print(f"Trigger channel for group {group_idx+1} set to {new_channel}")

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
            self.toggle_button.setStyleSheet("")  # Reset to default style
        else:
            self.is_single_capture = False
            self.send_start_message()
            self.start_reading()
            self.toggle_button.setText("Running")
            self.single_button.setEnabled(True)  # Keep Single button enabled
            self.toggle_button.setStyleSheet("background-color: #00FF77; color: black;")  # Change to cyan with black text

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
            self.single_button.setStyleSheet("background-color: #00FF77; color: black;")  # Change to cyan with black text

    def stop_single_capture(self):
        self.is_single_capture = False
        self.stop_reading()
        self.send_stop_message()
        self.single_button.setEnabled(True)
        self.toggle_button.setEnabled(True)
        self.toggle_button.setText("Start")
        self.single_button.setStyleSheet("")  # Reset to default style

    def clear_data_buffers(self):
        self.data_buffer = [[] for _ in range(8)]  # 8 channels

    def handle_data(self, data_list):
        if self.is_reading:
            for data_value in data_list:
                for i in range(8):
                    bit = (data_value >> i) & 1
                    self.data_buffer[i].append(bit)
                    if len(self.data_buffer[i]) > 1024:
                        self.data_buffer[i].pop(0)
            if self.is_single_capture and all(len(buf) >= 1024 for buf in self.data_buffer):
                self.stop_single_capture()

    def update_plot(self):
        for i in range(8):
            if self.channel_visibility[i]:
                inverted_index = 8 - i - 1
                num_samples = len(self.data_buffer[i])
                if num_samples > 1:
                    t = np.arange(num_samples) / self.sample_rate  # Time in seconds
                    square_wave_time = []
                    square_wave_data = []
                    for j in range(1, num_samples):
                        square_wave_time.extend([t[j-1], t[j]])
                        level = self.data_buffer[i][j-1] + inverted_index * 2
                        square_wave_data.extend([level, level])
                        if self.data_buffer[i][j] != self.data_buffer[i][j-1]:
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

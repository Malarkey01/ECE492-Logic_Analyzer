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
    QRadioButton,
    QButtonGroup,
    QSizePolicy,
    QTextEdit,
)
from PyQt6.QtGui import QIcon, QIntValidator, QTextCursor, QFont
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from collections import deque
from InterfaceCommands import (
    get_trigger_edge_command,
    get_trigger_pins_command,
)
from aesthetic import get_icon

class SerialWorker(QThread):
    data_ready = pyqtSignal(int)  # For raw data values
    decoded_message_ready = pyqtSignal(dict)  # For decoded messages

    def __init__(self, port, baudrate, channels=8, group_configs=None):
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.group_configs = group_configs if group_configs else [{} for _ in range(2)]
        self.trigger_modes = ['No Trigger'] * self.channels

        # Initialize SPI decoding variables for each group
        self.states = ['IDLE'] * len(self.group_configs)
        self.bit_counts = [0] * len(self.group_configs)
        self.current_bytes = [0] * len(self.group_configs)
        self.decoded_messages = [[] for _ in range(len(self.group_configs))]
        self.sample_idx = 0  # Initialize sample index

        # Initialize last values
        self.ss_last_values = [1] * len(self.group_configs)
        self.sclk_last_values = [0] * len(self.group_configs)
        self.mosi_last_values = [0] * len(self.group_configs)

        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def set_trigger_mode(self, channel_idx, mode):
        self.trigger_modes[channel_idx] = mode

    def run(self):
        while self.is_running:
            if self.serial.in_waiting:
                raw_data = self.serial.read(self.serial.in_waiting).splitlines()
                for line in raw_data:
                    try:
                        data_value = int(line.strip())
                        self.data_ready.emit(data_value)
                        self.decode_spi(data_value)
                        self.sample_idx += 1  # Increment sample index
                    except ValueError:
                        continue

    def decode_spi(self, data_value):
        for group_idx, group_config in enumerate(self.group_configs):
            ss_channel = group_config['ss_channel'] - 1
            mosi_channel = group_config['mosi_channel'] - 1
            sclk_channel = group_config['sclk_channel'] - 1
            num_bits = group_config.get('num_bits', 8)
            bit_order = group_config.get('bit_order', 'MSB First')

            # Extract SS, MOSI, and SCLK values
            ss = (data_value >> ss_channel) & 1
            mosi = (data_value >> mosi_channel) & 1
            sclk = (data_value >> sclk_channel) & 1

            # Get last values
            ss_last = self.ss_last_values[group_idx]
            sclk_last = self.sclk_last_values[group_idx]

            # Detect edges on SCLK
            sclk_edge = sclk != sclk_last

            state = self.states[group_idx]
            bit_count = self.bit_counts[group_idx]
            current_byte = self.current_bytes[group_idx]

            if state == 'IDLE':
                if ss == 0:  # Slave Select is active (assuming active low)
                    state = 'RECEIVE'
                    bit_count = 0
                    current_byte = 0
                    # Emit SS active signal
                    self.decoded_message_ready.emit({
                        'group_idx': group_idx,
                        'event': 'SS_ACTIVE',
                        'sample_idx': self.sample_idx,
                    })
            if state == 'RECEIVE':
                if ss == 1:
                    # SS went inactive, message complete
                    state = 'IDLE'
                    if bit_count > 0:
                        # Emit incomplete byte if any bits were received
                        self.decoded_message_ready.emit({
                            'group_idx': group_idx,
                            'event': 'DATA',
                            'data': current_byte,
                            'bits': bit_count,
                            'sample_idx': self.sample_idx,
                        })
                    # Emit SS inactive signal
                    self.decoded_message_ready.emit({
                        'group_idx': group_idx,
                        'event': 'SS_INACTIVE',
                        'sample_idx': self.sample_idx,
                    })
                elif sclk_edge and sclk == 1:  # Rising edge of SCLK
                    if bit_order == 'MSB First':
                        current_byte = (current_byte << 1) | mosi
                    else:
                        current_byte |= (mosi << bit_count)
                    bit_count += 1
                    if bit_count == num_bits:
                        # Emit byte received
                        self.decoded_message_ready.emit({
                            'group_idx': group_idx,
                            'event': 'DATA',
                            'data': current_byte,
                            'bits': num_bits,
                            'sample_idx': self.sample_idx,
                        })
                        bit_count = 0
                        current_byte = 0

            # Update states
            self.states[group_idx] = state
            self.bit_counts[group_idx] = bit_count
            self.current_bytes[group_idx] = current_byte

            # Update last values
            self.ss_last_values[group_idx] = ss
            self.sclk_last_values[group_idx] = sclk

    def reset_decoding_states(self):
        # Reset SPI decoding variables for each group
        self.states = ['IDLE'] * len(self.group_configs)
        self.bit_counts = [0] * len(self.group_configs)
        self.current_bytes = [0] * len(self.group_configs)
        self.decoded_messages = [[] for _ in range(len(self.group_configs))]
        self.sample_idx = 0  # Reset sample index

        # Reset last values
        self.ss_last_values = [1] * len(self.group_configs)
        self.sclk_last_values = [0] * len(self.group_configs)
        self.mosi_last_values = [0] * len(self.group_configs)

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
    reset_requested = pyqtSignal(int)      # New signal for reset

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
            self.reset_requested.emit(self.group_idx)  # Emit reset signal
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
        ss_label = QLabel("Slave Select Channel:")
        self.ss_combo = QComboBox()
        self.ss_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.ss_combo.setCurrentIndex(self.current_config.get('ss_channel', 1) - 1)
        ss_layout.addWidget(ss_label)
        ss_layout.addWidget(self.ss_combo)
        layout.addLayout(ss_layout)

        # Data Channel Selection
        data_layout = QHBoxLayout()
        data_label = QLabel("Data Channel:")
        self.data_combo = QComboBox()
        self.data_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.data_combo.setCurrentIndex(self.current_config.get('mosi_channel', 2) - 1)
        data_layout.addWidget(data_label)
        data_layout.addWidget(self.data_combo)
        layout.addLayout(data_layout)

        # Clock Channel Selection
        clock_layout = QHBoxLayout()
        clock_label = QLabel("Clock Channel:")
        self.clock_combo = QComboBox()
        self.clock_combo.addItems([f"Channel {i+1}" for i in range(8)])
        self.clock_combo.setCurrentIndex(self.current_config.get('sclk_channel', 3) - 1)
        clock_layout.addWidget(clock_label)
        clock_layout.addWidget(self.clock_combo)
        layout.addLayout(clock_layout)

        # Number of Data Bits
        bits_layout = QHBoxLayout()
        bits_label = QLabel("Number of Data Bits:")
        self.bits_input = QLineEdit()
        self.bits_input.setValidator(QIntValidator(1, 32))
        self.bits_input.setText(str(self.current_config.get('num_bits', 8)))
        bits_layout.addWidget(bits_label)
        bits_layout.addWidget(self.bits_input)
        layout.addLayout(bits_layout)

        # Bit Order Selection
        order_layout = QHBoxLayout()
        order_label = QLabel("Bit Order:")
        self.order_group = QButtonGroup(self)
        self.order_msb = QRadioButton("MSB First")
        self.order_lsb = QRadioButton("LSB First")
        self.order_group.addButton(self.order_msb)
        self.order_group.addButton(self.order_lsb)
        order_layout.addWidget(order_label)
        order_layout.addWidget(self.order_msb)
        order_layout.addWidget(self.order_lsb)
        layout.addLayout(order_layout)

        if self.current_config.get('bit_order', 'MSB First') == 'MSB First':
            self.order_msb.setChecked(True)
        else:
            self.order_lsb.setChecked(True)

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
            'ss_channel': self.ss_combo.currentIndex() + 1,
            'mosi_channel': self.data_combo.currentIndex() + 1,
            'sclk_channel': self.clock_combo.currentIndex() + 1,
            'num_bits': int(self.bits_input.text()),
            'bit_order': 'MSB First' if self.order_msb.isChecked() else 'LSB First',
            'data_format': self.format_combo.currentText(),
        }

class SPIDisplay(QWidget):
    def __init__(self, port, baudrate, bufferSize, channels=8):
        super().__init__()
        self.period = 65454
        self.num_samples = 0
        self.port = port
        self.baudrate = baudrate
        self.channels = channels
        self.bufferSize = bufferSize

        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]  # 8 channels
        self.sample_indices = deque(maxlen=self.bufferSize)
        self.total_samples = 0

        self.is_single_capture = False

        self.current_trigger_modes = ['No Trigger'] * self.channels
        self.trigger_mode_options = ['No Trigger', 'Rising Edge', 'Falling Edge']

        self.sample_rate = 1000  # Default sample rate in Hz

        # Initialize group configurations with default channels
        self.group_configs = [
            {'ss_channel': 1, 'mosi_channel': 2, 'sclk_channel': 3, 'num_bits': 8, 'bit_order': 'MSB First', 'data_format': 'Hexadecimal'},
            {'ss_channel': 4, 'mosi_channel': 5, 'sclk_channel': 6, 'num_bits': 8, 'bit_order': 'MSB First', 'data_format': 'Hexadecimal'},
        ]

        self.default_group_configs = [
            {'ss_channel': 1, 'mosi_channel': 2, 'sclk_channel': 3, 'num_bits': 8, 'bit_order': 'MSB First', 'data_format': 'Hexadecimal'},
            {'ss_channel': 4, 'mosi_channel': 5, 'sclk_channel': 6, 'num_bits': 8, 'bit_order': 'MSB First', 'data_format': 'Hexadecimal'},
        ]

        self.spi_group_enabled = [False] * 2  # Track which SPI groups are enabled

        # Initialize decoded messages per group
        self.decoded_messages_per_group = {i: [] for i in range(2)}

        self.group_cursors = [[] for _ in range(2)]  # To store cursors per group

        self.setup_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading = False

        self.worker = SerialWorker(self.port, self.baudrate, channels=self.channels, group_configs=self.group_configs)
        self.worker.data_ready.connect(self.handle_data_value)
        self.worker.decoded_message_ready.connect(self.display_decoded_message)
        self.worker.start()

        self.group_curves = []
        for group_idx in range(2):  # Assuming 2 groups
            # Create curves for MOSI, MISO, SCLK, and SS for each group
            mosi_curve = self.plot.plot(pen=pg.mkPen(color=self.colors[group_idx % len(self.colors)], width=4))
            sclk_curve = self.plot.plot(pen=pg.mkPen(color='#DEDEDE', width=4))
            ss_curve = self.plot.plot(pen=pg.mkPen(color='#FFA500', width=4))  # Orange for SS
            mosi_curve.setVisible(False)
            sclk_curve.setVisible(False)
            ss_curve.setVisible(False)
            self.group_curves.append({'mosi_curve': mosi_curve, 'sclk_curve': sclk_curve, 'ss_curve': ss_curve})

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        plot_layout = QHBoxLayout()
        main_layout.addLayout(plot_layout)

        self.graph_layout = pg.GraphicsLayoutWidget()
        plot_layout.addWidget(self.graph_layout, stretch=3)  # Allocate more space to the graph

        self.plot = self.graph_layout.addPlot(viewBox=FixedYViewBox())

        self.plot.setXRange(0, self.bufferSize / self.sample_rate, padding=0)
        self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.setYRange(-2, 2 * self.channels, padding=0)  # 8 channels
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)
        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)
        self.plot.setLabel('bottom', 'Time', units='s')

        self.colors = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF']
        self.group_curves = []
        for group_idx in range(2):  # Assuming 2 groups
            # Create curves for MOSI, SCLK, and SS for each group
            mosi_curve = self.plot.plot(pen=pg.mkPen(color=self.colors[group_idx % len(self.colors)], width=4))
            sclk_curve = self.plot.plot(pen=pg.mkPen(color='#DEDEDE', width=4))
            ss_curve = self.plot.plot(pen=pg.mkPen(color='#FFA500', width=4))  # Orange for SS
            mosi_curve.setVisible(False)
            sclk_curve.setVisible(False)
            ss_curve.setVisible(False)
            self.group_curves.append({'mosi_curve': mosi_curve, 'sclk_curve': sclk_curve, 'ss_curve': ss_curve})

        button_layout = QGridLayout()
        plot_layout.addLayout(button_layout, stretch=1)  # Allocate less space to the control panel

        button_widget = QWidget()
        button_layout = QGridLayout(button_widget)
        plot_layout.addWidget(button_widget)

        self.channel_buttons = []
        self.trigger_mode_buttons = []

        for i in range(2):
            row = i * 2  # Increment by 2 for each group
            group_config = self.group_configs[i]
            ss_channel = group_config['ss_channel']
            mosi_channel = group_config['mosi_channel']
            sclk_channel = group_config['sclk_channel']
            label = f"SPI {i+1}\nCh{ss_channel}:SS\nCh{mosi_channel}:MOSI\nCh{sclk_channel}:SCLK"
            button = SPIChannelButton(label, group_idx=i)

            # Set size policy and fixed width
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            button.setFixedWidth(120)  # Set the fixed width for the button

            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel_group(idx, checked))
            button.configure_requested.connect(self.open_configuration_dialog)
            button_layout.addWidget(button, row, 0, 2, 1)  # Span 2 rows, 1 column

            # Trigger Mode Button
            trigger_button = QPushButton(f"Trigger - {self.current_trigger_modes[ss_channel - 1]}")
            trigger_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            trigger_button.setFixedWidth(150)
            trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx))
            button_layout.addWidget(trigger_button, row, 1)

            # Set row stretches to distribute space equally
            button_layout.setRowStretch(row, 1)

            self.channel_buttons.append(button)
            self.trigger_mode_buttons.append(trigger_button)

            button.reset_requested.connect(self.reset_group_to_default)

        # Calculate the starting row for the next set of widgets
        next_row = 2 * 2  # 2 groups * 2 rows per group

        # Sample Rate input
        self.sample_rate_label = QLabel("Sample Rate (Hz):")
        button_layout.addWidget(self.sample_rate_label, next_row, 0)

        self.sample_rate_input = QLineEdit()
        self.sample_rate_input.setValidator(QIntValidator(1, 5000000))
        self.sample_rate_input.setText("1000")
        self.sample_rate_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.sample_rate_input.setFixedWidth(100)
        button_layout.addWidget(self.sample_rate_input, next_row, 1)
        self.sample_rate_input.returnPressed.connect(self.handle_sample_rate_input)

        # Number of Samples input
        self.num_samples_label = QLabel("Number of Samples:")
        button_layout.addWidget(self.num_samples_label, next_row + 1, 0)

        self.num_samples_input = QLineEdit()
        self.num_samples_input.setValidator(QIntValidator(1, 1023))
        self.num_samples_input.setText("300")
        self.num_samples_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.num_samples_input.setFixedWidth(100)
        button_layout.addWidget(self.num_samples_input, next_row + 1, 1)
        self.num_samples_input.returnPressed.connect(self.send_num_samples_command)

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
        button_layout.addLayout(control_buttons_layout, next_row + 2, 0, 1, 2)

        # Adjust the stretch factors of the plot_layout
        plot_layout.setStretchFactor(self.graph_layout, 1)  # The plot area should expand
        plot_layout.setStretchFactor(button_widget, 0)      # The button area remains fixed

    def reset_group_to_default(self, group_idx):
        # Reset the group configuration to default settings
        default_config = self.default_group_configs[group_idx].copy()
        self.group_configs[group_idx] = default_config
        print(f"Group {group_idx+1} reset to default configuration: {default_config}")

        # Reset the button's label to default
        self.channel_buttons[group_idx].setText(self.channel_buttons[group_idx].default_label)

        # Update trigger mode buttons
        ss_channel = default_config['ss_channel']
        ss_idx = ss_channel - 1

        self.current_trigger_modes[ss_idx] = 'No Trigger'
        self.trigger_mode_buttons[group_idx].setText(f"Trigger - {self.current_trigger_modes[ss_idx]}")

        # Update worker's group configurations
        self.worker.group_configs[group_idx] = default_config

        # Update curves visibility and colors
        is_checked = self.spi_group_enabled[group_idx]
        mosi_curve = self.group_curves[group_idx]['mosi_curve']
        sclk_curve = self.group_curves[group_idx]['sclk_curve']
        ss_curve = self.group_curves[group_idx]['ss_curve']
        mosi_curve.setVisible(is_checked)
        sclk_curve.setVisible(is_checked)
        ss_curve.setVisible(is_checked)
        mosi_curve.setPen(pg.mkPen(color=self.colors[group_idx % len(self.colors)], width=4))
        sclk_curve.setPen(pg.mkPen(color='#DEDEDE', width=4))
        ss_curve.setPen(pg.mkPen(color='#FFA500', width=4))

        # Clear data buffers
        self.clear_data_buffers()

        # Reset button style to default
        self.channel_buttons[group_idx].setStyleSheet("")

        print(f"Group {group_idx+1} has been reset to default settings.")

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
            self.plot.setLimits(xMin=0, xMax=self.bufferSize / self.sample_rate)
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

    def toggle_trigger_mode(self, group_idx):
        group_config = self.group_configs[group_idx]
        ss_channel = group_config['ss_channel'] - 1  # Adjust index
        button = self.trigger_mode_buttons[group_idx]

        # Cycle through trigger modes
        current_mode = self.current_trigger_modes[ss_channel]
        current_mode_idx = self.trigger_mode_options.index(current_mode)
        new_mode_idx = (current_mode_idx + 1) % len(self.trigger_mode_options)
        new_mode = self.trigger_mode_options[new_mode_idx]
        self.current_trigger_modes[ss_channel] = new_mode
        button.setText(f"Trigger - {new_mode}")
        self.worker.set_trigger_mode(ss_channel, new_mode)
        self.send_trigger_edge_command()
        self.send_trigger_pins_command()

    def is_light_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5

    def toggle_channel_group(self, group_idx, is_checked):
        self.spi_group_enabled[group_idx] = is_checked  # Update the enabled list

        # Update curves visibility
        mosi_curve = self.group_curves[group_idx]['mosi_curve']
        sclk_curve = self.group_curves[group_idx]['sclk_curve']
        ss_curve = self.group_curves[group_idx]['ss_curve']
        mosi_curve.setVisible(is_checked)
        sclk_curve.setVisible(is_checked)
        ss_curve.setVisible(is_checked)

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
        self.data_buffer = [deque(maxlen=self.bufferSize) for _ in range(self.channels)]
        self.total_samples = 0  # Reset total samples

        # Remove all cursors
        for group_idx in range(2):
            for cursor_info in self.group_cursors[group_idx]:
                self.plot.removeItem(cursor_info['line'])
                self.plot.removeItem(cursor_info['label'])
            self.group_cursors[group_idx] = []

        # Reset worker's decoding states
        self.worker.reset_decoding_states()

    def handle_data_value(self, data_value):
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

    def display_decoded_message(self, decoded_data):
        group_idx = decoded_data['group_idx']
        if not self.spi_group_enabled[group_idx]:
            return  # Do not display if the group is not enabled
        data_format = self.group_configs[group_idx].get('data_format', 'Hexadecimal')
        event = decoded_data.get('event', None)
        sample_idx = decoded_data.get('sample_idx', None)

        if event == 'SS_ACTIVE' and sample_idx is not None:
            # Create cursor for SS active
            self.create_cursor(group_idx, sample_idx, 'SS Active')
        elif event == 'SS_INACTIVE' and sample_idx is not None:
            # Create cursor for SS inactive
            self.create_cursor(group_idx, sample_idx, 'SS Inactive')
        elif event == 'DATA':
            # Create cursor for Data byte
            data_byte = decoded_data['data']
            num_bits = decoded_data.get('bits', self.group_configs[group_idx].get('num_bits', 8))

            if data_format == 'Binary':
                data_str = bin(data_byte)[2:].zfill(num_bits)
            elif data_format == 'Decimal':
                data_str = str(data_byte)
            elif data_format == 'Hexadecimal':
                data_str = hex(data_byte)
            elif data_format == 'ASCII':
                data_str = chr(data_byte)
            elif data_format == 'BCD':
                # Convert to BCD representation
                data_str = ''.join([str((data_byte >> 4*i) & 0xF) for i in reversed(range((num_bits+3)//4))])
            else:
                data_str = hex(data_byte)
            label_text = f"D:{data_str}"
            self.create_cursor(group_idx, sample_idx, label_text)

    def create_cursor(self, group_idx, sample_idx, label_text):
        # Get base level for this group
        base_level = (2 - group_idx - 1) * 4  # Adjust as needed
        # Cursor color
        cursor_color = '#00F5FF'  # Use your preferred color
        # Create a vertical line segment between MOSI and SCLK levels
        y1 = base_level
        y2 = base_level + 3
        x = 0  # Initial x position, will be updated in update_plot
        # Create line data
        line = pg.PlotDataItem([x, x], [y1, y2], pen=pg.mkPen(color=cursor_color, width=2))
        self.plot.addItem(line)
        # Add a label
        label = pg.TextItem(text=label_text, anchor=(0.1, 0.5), color=cursor_color)
        font = QFont("Arial", 12)
        label.setFont(font)
        self.plot.addItem(label)
        # Store the line, label, and sample index
        self.group_cursors[group_idx].append({
            'line': line,
            'label': label,
            'sample_idx': sample_idx,
            'base_level': base_level,
            'y1': y1,
            'y2': y2
        })

    def clear_decoded_text(self):
        # Clear all decoded messages per group
        for idx in range(2):
            self.decoded_messages_per_group[idx] = []
        # Cursors are already cleared in clear_data_buffers

    def update_plot(self):
        for group_idx, is_enabled in enumerate(self.spi_group_enabled):
            if is_enabled:
                group_config = self.group_configs[group_idx]
                ss_channel = group_config['ss_channel'] - 1  # Adjust index
                mosi_channel = group_config['mosi_channel'] - 1  # Adjust index
                sclk_channel = group_config['sclk_channel'] - 1  # Adjust index

                # Get the curves for this group
                mosi_curve = self.group_curves[group_idx]['mosi_curve']
                sclk_curve = self.group_curves[group_idx]['sclk_curve']
                ss_curve = self.group_curves[group_idx]['ss_curve']

                # Prepare data for plotting
                mosi_data = list(self.data_buffer[mosi_channel])
                sclk_data = list(self.data_buffer[sclk_channel])
                ss_data = list(self.data_buffer[ss_channel])

                num_samples = len(mosi_data)
                if num_samples > 1:
                    t = np.arange(num_samples) / self.sample_rate

                    # Offset per group to separate the signals vertically
                    base_level = (2 - group_idx - 1) * 4  # Adjust as needed

                    # --- Plot MOSI Signal ---
                    mosi_square_wave_time = []
                    mosi_square_wave_data = []
                    for j in range(1, num_samples):
                        mosi_square_wave_time.extend([t[j - 1], t[j]])
                        level = mosi_data[j - 1] + base_level
                        mosi_square_wave_data.extend([level, level])
                        if mosi_data[j] != mosi_data[j - 1]:
                            mosi_square_wave_time.append(t[j])
                            level = mosi_data[j] + base_level
                            mosi_square_wave_data.append(level)
                    mosi_curve.setData(mosi_square_wave_time, mosi_square_wave_data)

                    # --- Plot SCLK Signal ---
                    sclk_square_wave_time = []
                    sclk_square_wave_data = []
                    for j in range(1, num_samples):
                        sclk_square_wave_time.extend([t[j - 1], t[j]])
                        level = sclk_data[j - 1] + base_level + 1  # Offset by 1 to separate from MOSI
                        sclk_square_wave_data.extend([level, level])
                        if sclk_data[j] != sclk_data[j - 1]:
                            sclk_square_wave_time.append(t[j])
                            level = sclk_data[j] + base_level + 1
                            sclk_square_wave_data.append(level)
                    sclk_curve.setData(sclk_square_wave_time, sclk_square_wave_data)

                    # --- Plot SS Signal ---
                    ss_square_wave_time = []
                    ss_square_wave_data = []
                    for j in range(1, num_samples):
                        ss_square_wave_time.extend([t[j - 1], t[j]])
                        level = ss_data[j - 1] + base_level + 2  # Offset by 2 to separate from SCLK
                        ss_square_wave_data.extend([level, level])
                        if ss_data[j] != ss_data[j - 1]:
                            ss_square_wave_time.append(t[j])
                            level = ss_data[j] + base_level + 2
                            ss_square_wave_data.append(level)
                    ss_curve.setData(ss_square_wave_time, ss_square_wave_data)

                    # --- Update Cursors ---
                    cursors_to_remove = []
                    for cursor_info in self.group_cursors[group_idx]:
                        sample_idx = cursor_info['sample_idx']
                        idx_in_buffer = sample_idx - (self.total_samples - num_samples)
                        if 0 <= idx_in_buffer < num_samples:
                            cursor_time = t[int(idx_in_buffer)]
                            # Update the line position
                            x = cursor_time
                            y1 = cursor_info['y1']
                            y2 = cursor_info['y2']
                            cursor_info['line'].setData([x, x], [y1, y2])
                            # Update the label position
                            label_offset = (t[1] - t[0]) * 5  # Adjust label offset as needed
                            cursor_info['label'].setPos(x + label_offset, (y1 + y2) / 2)
                            cursor_info['x_pos'] = x + label_offset  # Store x position for overlap checking
                        else:
                            # Cursor is no longer in the buffer, remove it
                            self.plot.removeItem(cursor_info['line'])
                            self.plot.removeItem(cursor_info['label'])
                            cursors_to_remove.append(cursor_info)
                    # Remove cursors that are no longer in buffer
                    for cursor_info in cursors_to_remove:
                        self.group_cursors[group_idx].remove(cursor_info)

                    # --- Hide Overlapping Labels ---
                    # Collect labels and their x positions
                    labels_with_positions = []
                    for cursor_info in self.group_cursors[group_idx]:
                        label = cursor_info['label']
                        x_pos = cursor_info.get('x_pos', None)
                        if x_pos is not None:
                            labels_with_positions.append((x_pos, label))

                    # Sort labels by x position
                    labels_with_positions.sort(key=lambda item: item[0])

                    # Hide labels that overlap
                    min_label_spacing = (t[1] - t[0]) * 10  # Adjust as needed
                    last_label_x = None
                    for x_pos, label in labels_with_positions:
                        if last_label_x is None:
                            label.setVisible(True)
                            last_label_x = x_pos
                        else:
                            if x_pos - last_label_x < min_label_spacing:
                                # Labels are too close, hide this label
                                label.setVisible(False)
                            else:
                                label.setVisible(True)
                                last_label_x = x_pos
                else:
                    # Clear the curves if no data
                    mosi_curve.setData([], [])
                    sclk_curve.setData([], [])
                    ss_curve.setData([], [])
            else:
                # If group is not enabled, hide curves
                self.group_curves[group_idx]['mosi_curve'].setVisible(False)
                self.group_curves[group_idx]['sclk_curve'].setVisible(False)
                self.group_curves[group_idx]['ss_curve'].setVisible(False)

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
            mosi_channel = new_config['mosi_channel']
            sclk_channel = new_config['sclk_channel']
            label = f"SPI {group_idx+1}\nCh{ss_channel}:SS\nCh{mosi_channel}:MOSI\nCh{sclk_channel}:SCLK"
            self.channel_buttons[group_idx].setText(label)
            # Update trigger mode buttons
            self.trigger_mode_buttons[group_idx].setText(f"Trigger - {self.current_trigger_modes[ss_channel - 1]}")
            # Update curves visibility
            is_checked = self.spi_group_enabled[group_idx]
            mosi_curve = self.group_curves[group_idx]['mosi_curve']
            sclk_curve = self.group_curves[group_idx]['sclk_curve']
            ss_curve = self.group_curves[group_idx]['ss_curve']
            mosi_curve.setVisible(is_checked)
            sclk_curve.setVisible(is_checked)
            ss_curve.setVisible(is_checked)
            # Clear data buffers
            self.clear_data_buffers()
            # Update worker's group configurations
            self.worker.group_configs = self.group_configs

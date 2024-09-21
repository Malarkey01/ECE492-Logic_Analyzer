import sys
import serial
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QPushButton,
    QLabel,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
import pyqtgraph as pg
import numpy as np
from aesthetic import get_icon
from functools import partial

class SerialWorker(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, port, baudrate):
        super().__init__()
        self.is_running = True
        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def run(self):
        while self.is_running:
            if self.serial.in_waiting:
                data = self.serial.read(self.serial.in_waiting).splitlines()
                processed_data = []
                for line in data:
                    try:
                        data_value = int(line.strip())
                        processed_data.append(data_value)
                    except ValueError:
                        continue
                self.data_ready.emit(processed_data)

    def stop_worker(self):
        self.is_running = False
        if self.serial.is_open:
            self.serial.close()

class FixedYViewBox(pg.ViewBox):
    def __init__(self, *args, **kwargs):
        super(FixedYViewBox, self).__init__(*args, **kwargs)

    def scaleBy(self, s=None, center=None, x=None, y=None):
        y = 1.0
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
        y = 0.0
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

class LogicDisplay(QMainWindow):
    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.channels = channels

        self.setWindowTitle("Logic Analyzer")
        self.setWindowIcon(get_icon())

        # Initialize data buffers
        self.data_buffer = [[] for _ in range(self.channels)]
        self.channel_visibility = [False] * self.channels

        # Trigger-related attributes
        self.trigger_channel = None  # No default trigger channel
        self.trigger_conditions = {}  # Store trigger conditions for each channel
        for i in range(self.channels):
            self.trigger_conditions[i] = 'Rising'  # Default to Rising Edge
        self.triggered = False
        self.pre_trigger_buffer = [[] for _ in range(self.channels)]
        self.post_trigger_buffer = [[] for _ in range(self.channels)]
        self.post_trigger_samples = 600  # Number of samples to collect after trigger
        self.post_trigger_count = 0

        self.setup_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading = False

        self.worker = SerialWorker(self.port, self.baudrate)
        self.worker.data_ready.connect(self.handle_data)
        self.worker.start()

    def setup_ui(self):
        self.setWindowTitle("Logic Analyzer")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        self.graph_layout = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.graph_layout)

        self.plot = self.graph_layout.addPlot(viewBox=FixedYViewBox())

        self.plot.setYRange(-2, 2 * self.channels, padding=0)
        self.plot.enableAutoRange(axis=pg.ViewBox.XAxis)
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot.showGrid(x=True, y=True)

        self.plot.getAxis('left').setTicks([])
        self.plot.getAxis('left').setStyle(showValues=False)
        self.plot.getAxis('left').setPen(None)

        # Define the custom colors for the channels
        self.colors = ['#FF6EC7', '#39FF14', '#FF486D', '#BF00FF', '#FFFF33', '#FFA500', '#00F5FF', '#BFFF00']

        self.curves = []
        for i in range(self.channels):
            color = self.colors[i % len(self.colors)]
            curve = self.plot.plot(pen=pg.mkPen(color=color, width=4))
            curve.setVisible(self.channel_visibility[i])
            self.curves.append(curve)

        button_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        self.channel_buttons = []
        self.trigger_buttons = []

        for i in range(self.channels):
            channel_layout = QHBoxLayout()
            label = f"DIO {i+1}"
            button = EditableButton(label)
            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))

            # Trigger button
            trigger_button = QPushButton(self.trigger_conditions[i])
            trigger_button.clicked.connect(partial(self.toggle_trigger, channel_idx=i))

            channel_layout.addWidget(button)
            channel_layout.addWidget(trigger_button)
            button_layout.addLayout(channel_layout)

            # Store buttons for reference
            self.channel_buttons.append(button)
            self.trigger_buttons.append(trigger_button)

        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_reading)
        button_layout.addWidget(self.toggle_button)

    def is_light_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return luminance > 0.5

    def toggle_channel(self, channel_idx, is_checked):
        self.channel_visibility[channel_idx] = is_checked
        self.curves[channel_idx].setVisible(is_checked)

        # Update button background color
        button = self.channel_buttons[channel_idx]
        if is_checked:
            color = self.colors[channel_idx % len(self.colors)]
            text_color = 'black' if self.is_light_color(color) else 'white'
            button.setStyleSheet(f"QPushButton {{ background-color: {color}; color: {text_color}; "
                                 f"border: 1px solid #555; border-radius: 5px; padding: 5px; }}")
        else:
            button.setStyleSheet("")

    def toggle_trigger(self, channel_idx):
        # Toggle the trigger condition
        current_condition = self.trigger_conditions[channel_idx]
        if current_condition == 'Rising':
            self.trigger_conditions[channel_idx] = 'Falling'
        else:
            self.trigger_conditions[channel_idx] = 'Rising'

        # Update the button text
        button = self.trigger_buttons[channel_idx]
        button.setText(self.trigger_conditions[channel_idx])

        # Set this channel as the trigger channel
        previous_trigger_channel = self.trigger_channel
        self.trigger_channel = channel_idx

        # Update the trigger button appearance
        for idx, trig_button in enumerate(self.trigger_buttons):
            if idx == channel_idx:
                # Highlight the selected trigger channel
                trig_button.setStyleSheet("QPushButton { background-color: #FFD700; }")
            else:
                # Reset other buttons
                trig_button.setStyleSheet("")

    def toggle_reading(self):
        if self.is_reading:
            self.stop_reading()
            self.toggle_button.setText("Start")
        else:
            self.start_reading()
            self.toggle_button.setText("Stop")

    def start_reading(self):
        if not self.is_reading:
            self.is_reading = True
            self.triggered = False
            self.post_trigger_count = 0
            self.pre_trigger_buffer = [[] for _ in range(self.channels)]
            self.post_trigger_buffer = [[] for _ in range(self.channels)]
            self.data_buffer = [[] for _ in range(self.channels)]
            # Clear the plot
            for curve in self.curves:
                curve.clear()
            if hasattr(self, 'trigger_line'):
                self.plot.removeItem(self.trigger_line)
                del self.trigger_line
            self.timer.start(1)

    def stop_reading(self):
        if self.is_reading:
            self.is_reading = False
            self.timer.stop()

    def rising_edge_trigger(self, previous_value, current_value):
        return previous_value == 0 and current_value == 1

    def falling_edge_trigger(self, previous_value, current_value):
        return previous_value == 1 and current_value == 0

    def handle_data(self, data_list):
        for data_value in data_list:
            channel_values = []
            for i in range(self.channels):
                bit_value = (data_value >> i) & 1
                channel_values.append(bit_value)

            if not self.triggered:
                # Append to pre-trigger buffers
                for i in range(self.channels):
                    self.pre_trigger_buffer[i].append(channel_values[i])
                    # Limit pre-trigger buffer size
                    if len(self.pre_trigger_buffer[i]) > 600:
                        self.pre_trigger_buffer[i].pop(0)

                # Check trigger condition on the trigger channel
                if self.trigger_channel is not None and len(self.pre_trigger_buffer[self.trigger_channel]) >= 2:
                    prev_value = self.pre_trigger_buffer[self.trigger_channel][-2]
                    curr_value = self.pre_trigger_buffer[self.trigger_channel][-1]
                    condition = self.trigger_conditions[self.trigger_channel]
                    if condition == 'Rising' and prev_value == 0 and curr_value == 1:
                        self.triggered = True
                        print("Trigger occurred!")
                    elif condition == 'Falling' and prev_value == 1 and curr_value == 0:
                        self.triggered = True
                        print("Trigger occurred!")
            else:
                # Collect post-trigger data
                for i in range(self.channels):
                    self.post_trigger_buffer[i].append(channel_values[i])
                self.post_trigger_count += 1

                # Check if enough post-trigger data has been collected
                if self.post_trigger_count >= self.post_trigger_samples:
                    # Combine pre-trigger and post-trigger buffers
                    for i in range(self.channels):
                        self.data_buffer[i] = self.pre_trigger_buffer[i] + self.post_trigger_buffer[i]
                    # Stop data acquisition
                    self.stop_reading()

    def update_plot(self):
        if self.triggered:
            for i in range(self.channels):
                if self.channel_visibility[i]:
                    inverted_index = self.channels - i - 1
                    t = np.arange(len(self.data_buffer[i]))
                    if len(t) > 1:
                        square_wave_time = []
                        square_wave_data = []
                        for j in range(1, len(t)):
                            square_wave_time.extend([t[j-1], t[j]])
                            square_wave_data.extend([
                                self.data_buffer[i][j-1] + inverted_index * 2,
                                self.data_buffer[i][j-1] + inverted_index * 2,
                            ])
                            if self.data_buffer[i][j] != self.data_buffer[i][j-1]:
                                square_wave_time.append(t[j])
                                square_wave_data.append(self.data_buffer[i][j] + inverted_index * 2)
                        self.curves[i].setData(square_wave_time, square_wave_data)
            # Add a vertical line at the trigger point
            trigger_position = len(self.pre_trigger_buffer[0])
            if not hasattr(self, 'trigger_line'):
                self.trigger_line = pg.InfiniteLine(pos=trigger_position, angle=90, pen=pg.mkPen('r', width=2))
                self.plot.addItem(self.trigger_line)
        else:
            # Optionally, display pre-trigger data or a message
            pass

    def closeEvent(self, event):
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()

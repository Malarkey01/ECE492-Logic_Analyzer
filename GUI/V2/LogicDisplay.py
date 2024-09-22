import sys
import serial
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QInputDialog,
    QMenu,
    QPushButton,
    QLabel,
    QLineEdit,  # Added QLabel and QLineEdit
)
from PyQt6.QtGui import QIcon, QIntValidator  # Added QIntValidator
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
import pyqtgraph as pg
import numpy as np
from aesthetic import get_icon

class SerialWorker(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.is_running = True
        self.channels = channels
        self.trigger_modes = ['No Trigger'] * channels  # Initialize trigger modes for each channel
        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def set_trigger_mode(self, channel_idx, mode):
        self.trigger_modes[channel_idx] = mode

    def run(self):
        pre_trigger_buffer_size = 1000  # Adjust as needed
        data_buffer = []
        triggered = [False] * self.channels  # Trigger state per channel

        while self.is_running:
            if self.serial.in_waiting:
                raw_data = self.serial.read(self.serial.in_waiting).splitlines()
                for line in raw_data:
                    try:
                        data_value = int(line.strip())
                        data_buffer.append(data_value)
                        # Keep the buffer size manageable
                        if len(data_buffer) > pre_trigger_buffer_size:
                            data_buffer.pop(0)

                        # Check trigger conditions for each channel
                        for i in range(self.channels):
                            if not triggered[i] and self.trigger_modes[i] != 'No Trigger':
                                last_value = data_buffer[-2] if len(data_buffer) >= 2 else None
                                if last_value is not None:
                                    current_bit = (data_value >> i) & 1
                                    last_bit = (last_value >> i) & 1

                                    if self.trigger_modes[i] == 'Rising Edge' and last_bit == 0 and current_bit == 1:
                                        triggered[i] = True
                                        print(f"Trigger condition met on channel {i+1}: Rising Edge")
                                    elif self.trigger_modes[i] == 'Falling Edge' and last_bit == 1 and current_bit == 0:
                                        triggered[i] = True
                                        print(f"Trigger condition met on channel {i+1}: Falling Edge")
                        # If any channel is triggered or all are set to 'No Trigger', emit data
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

        self.data_buffer = [[] for _ in range(self.channels)]
        self.channel_visibility = [False] * self.channels

        self.setup_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.is_reading = False

        self.worker = SerialWorker(self.port, self.baudrate, channels=self.channels)
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

        button_layout = QGridLayout()
        main_layout.addLayout(button_layout)

        self.channel_buttons = []
        self.trigger_mode_buttons = []
        self.trigger_modes = ['No Trigger', 'Rising Edge', 'Falling Edge']
        self.trigger_mode_indices = [0] * self.channels  # Initialize indices for each channel

        for i in range(self.channels):
            # Channel button
            label = f"DIO {i+1}"
            button = EditableButton(label)
            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))
            # Set the channel color property
            color = self.colors[i % len(self.colors)]
            button.setProperty('channelColor', color)
            button_layout.addWidget(button, i, 0)  # Place in column 0
            self.channel_buttons.append(button)

            # Trigger mode button
            trigger_button = QPushButton(self.trigger_modes[self.trigger_mode_indices[i]])
            trigger_button.clicked.connect(lambda _, idx=i: self.toggle_trigger_mode(idx))
            button_layout.addWidget(trigger_button, i, 1)  # Place in column 1
            self.trigger_mode_buttons.append(trigger_button)

        # Sample Rate Label
        self.sample_rate_label = QLabel("Sample Rate (Hz):")
        button_layout.addWidget(self.sample_rate_label, self.channels, 0)

        # Sample Rate Input
        self.sample_rate_input = QLineEdit()
        self.sample_rate_input.setValidator(QIntValidator(0, 1000000))
        self.sample_rate_input.setText("1000")  # Default value
        button_layout.addWidget(self.sample_rate_input, self.channels, 1)

        # Start/Stop button
        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_reading)
        button_layout.addWidget(self.toggle_button, self.channels + 1, 0, 1, 2)  # Span two columns

        # Adding a movable vertical cursor
        self.cursor = pg.InfiniteLine(pos=0, angle=90, movable=True, pen=pg.mkPen(color='y', width=2))
        self.plot.addItem(self.cursor)

        # Label to display cursor position
        self.cursor_label = pg.TextItem(anchor=(0, 1), color='y')
        self.plot.addItem(self.cursor_label)
        self.update_cursor_position()

        # Connect cursor movement to a function
        self.cursor.sigPositionChanged.connect(self.update_cursor_position)

    def toggle_trigger_mode(self, channel_idx):
        self.trigger_mode_indices[channel_idx] = (self.trigger_mode_indices[channel_idx] + 1) % len(self.trigger_modes)
        mode = self.trigger_modes[self.trigger_mode_indices[channel_idx]]
        self.trigger_mode_buttons[channel_idx].setText(mode)
        # Update the worker's trigger mode for this channel
        if self.worker:
            self.worker.set_trigger_mode(channel_idx, mode)

    def is_light_color(self, hex_color):
        """
        Determines if a hex color is light or dark.
        Returns True if the color is light, False if dark.
        """
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
            # Decide text color based on background color brightness
            text_color = 'black' if self.is_light_color(color) else 'white'
            # Set the button style
            button.setStyleSheet(f"QPushButton {{ background-color: {color}; color: {text_color}; "
                                 f"border: 1px solid #555; border-radius: 5px; padding: 5px; }}")
        else:
            # Reset to default style
            button.setStyleSheet("")

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
            self.timer.start(1)

    def stop_reading(self):
        if self.is_reading:
            self.is_reading = False
            self.timer.stop()

    def handle_data(self, data_list):
        if self.is_reading:
            for data_value in data_list:
                for i in range(self.channels):
                    bit_value = (data_value >> i) & 1
                    self.data_buffer[i].append(bit_value)
                    if len(self.data_buffer[i]) > 600:
                        self.data_buffer[i].pop(0)

    def update_plot(self):
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

    def update_cursor_position(self):
        cursor_pos = self.cursor.pos().x()
        self.cursor_label.setText(f"Cursor: {cursor_pos:.2f}")
        self.cursor_label.setPos(cursor_pos, self.channels * 2 - 1)  # Adjust label position vertically

    def closeEvent(self, event):
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()

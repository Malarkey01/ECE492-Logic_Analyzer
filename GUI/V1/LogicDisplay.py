import sys
import serial
from PyQt6.QtWidgets import QApplication, QMainWindow, QGridLayout, QPushButton, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
import pyqtgraph as pg
import numpy as np

class SerialWorker(QThread):
    data_ready = pyqtSignal(list)  # Signal to send data back to the main thread

    def __init__(self, port, baudrate):
        super().__init__()
        self.serial = serial.Serial(port, baudrate)
        self.is_running = True

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
        self.serial.close()

class LogicDisplay(QMainWindow):
    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.channels = channels

        # Buffers for each channel to hold the logic signal values
        self.data_buffer = [[] for _ in range(self.channels)]

        # Flags for visibility of each channel (start in OFF state)
        self.channel_visibility = [False] * self.channels

        self.setup_ui()

        # Timer for updating the plot
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        # Flag to indicate whether data reading is active
        self.is_reading = False

        # Start the serial worker thread to read data
        self.worker = SerialWorker(self.port, self.baudrate)
        self.worker.data_ready.connect(self.handle_data)
        self.worker.start()

    def setup_ui(self):
        self.setWindowTitle("Logic Analyzer")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # Main layout: horizontal layout to place graph and buttons side by side
        main_layout = QHBoxLayout(central_widget)

        # Setup the pyqtgraph layout for the graph
        self.graph_layout = pg.GraphicsLayoutWidget()
        main_layout.addWidget(self.graph_layout)

        # Create a single plot widget for all channels
        self.plot = self.graph_layout.addPlot()
        self.plot.setTitle("Logic Signals")
        self.plot.setYRange(-2, 2 * self.channels, padding=0)  # Adjust Y range to fit all channels
        self.plot.showGrid(x=True, y=True)

        # Remove numeric values from the y-axis and replace them with channel names
        self.plot.getAxis('left').setTicks([[(i * 2, f'Channel {self.channels - i}') for i in range(self.channels)]])
        self.plot.getAxis('left').setStyle(showValues=False)  # Hide the numeric values

        # Create curve objects for each channel
        self.curves = []
        for i in range(self.channels):
            curve = self.plot.plot(pen=pg.mkPen(color=pg.intColor(i, hues=16)))
            curve.setVisible(False)  # Start with channels hidden
            self.curves.append(curve)

        # Layout for the toggle buttons (Channel 1 - Channel 8)
        button_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        # Create and add toggle buttons for each channel
        self.channel_buttons = []
        for i in range(self.channels):
            button = QPushButton(f"Channel {i+1}")
            button.setCheckable(True)
            button.setChecked(False)  # Start with all channels off (unchecked)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))
            button_layout.addWidget(button)
            self.channel_buttons.append(button)

        # Create the combined toggle button for Start/Stop
        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_reading)
        button_layout.addWidget(self.toggle_button)


    def toggle_channel(self, channel_idx, is_checked):
        """Toggles the visibility of a specific channel."""
        self.channel_visibility[channel_idx] = is_checked
        self.curves[channel_idx].setVisible(is_checked)

    def toggle_reading(self):
        """Toggles between starting and stopping the data reading."""
        if self.is_reading:
            self.stop_reading()
            self.toggle_button.setText("Start")
        else:
            self.start_reading()
            self.toggle_button.setText("Stop")

    def start_reading(self):
        if not self.is_reading:
            self.is_reading = True
            self.timer.start(1)  # Start the timer for regular updates

    def stop_reading(self):
        if self.is_reading:
            self.is_reading = False
            self.timer.stop()  # Stop the timer to pause updating the plot

    def handle_data(self, data_list):
        if self.is_reading:  # Only handle data if reading is active
            for data_value in data_list:
                for i in range(self.channels):
                    bit_value = (data_value >> i) & 1
                    self.data_buffer[i].append(bit_value)

                    if len(self.data_buffer[i]) > 600:
                        self.data_buffer[i].pop(0)

    def update_plot(self):
        # Update the plot with the latest data, applying vertical offsets to each channel
        for i in range(self.channels):
            if self.channel_visibility[i]:
                # Invert the channel index so that Channel 1 is at the top
                inverted_index = self.channels - i - 1

                # Create the time axis
                t = np.arange(len(self.data_buffer[i]))

                # We need to create the square wave by adding additional points for each transition
                if len(t) > 1:
                    square_wave_time = []
                    square_wave_data = []
                    for j in range(1, len(t)):
                        # Add the previous point
                        square_wave_time.extend([t[j-1], t[j]])
                        square_wave_data.extend([self.data_buffer[i][j-1] + inverted_index * 2, self.data_buffer[i][j-1] + inverted_index * 2])

                        # Check if there's a change in the logic level
                        if self.data_buffer[i][j] != self.data_buffer[i][j-1]:
                            # Add vertical transition
                            square_wave_time.append(t[j])
                            square_wave_data.append(self.data_buffer[i][j] + inverted_index * 2)

                    # Update the curve with square wave data
                    self.curves[i].setData(square_wave_time, square_wave_data)

    def closeEvent(self, event):
        self.worker.stop_worker()  # Stop the worker when the window is closed
        self.worker.quit()
        event.accept()

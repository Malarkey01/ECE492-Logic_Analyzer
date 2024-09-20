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
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
import pyqtgraph as pg
import numpy as np
from aesthetic import get_icon

class SerialWorker(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, port, baudrate):
        super().__init__()
        self.is_running = True
        self.serial_buffer = []  # Queue to store incoming serial data
        try:
            self.serial = serial.Serial(port, baudrate, timeout=0.1)  # Use timeout to avoid blocking
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

    def run(self):
        while self.is_running:
            if self.serial.in_waiting:
                try:
                    # Read a chunk of data from the serial port
                    data_chunk = self.serial.read(self.serial.in_waiting)
                    self.serial_buffer.extend(data_chunk.splitlines())

                    # Process the data and emit it
                    processed_data = [int(line.strip()) for line in self.serial_buffer if line.strip().isdigit()]
                    self.data_ready.emit(processed_data)

                    # Clear the buffer after processing
                    self.serial_buffer.clear()
                except Exception as e:
                    print(f"Error during serial read: {str(e)}")

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
        x = x or t.get('x', 0) if t else 0
        super(FixedYViewBox, self).translateBy(x=x, y=0)

class LogicDisplay(QMainWindow):
    def __init__(self, port, baudrate, channels=8):
        super().__init__()
        self.channels = channels
        self.is_reading = False
        self.data_buffer = [[] for _ in range(channels)]
        self.channel_visibility = [True] * channels

        self.initUI()
        self.worker = SerialWorker(port, baudrate)
        self.worker.data_ready.connect(self.handle_data)
        self.worker.start()

    def initUI(self):
        self.setWindowTitle("Logic Analyzer")
        self.setWindowIcon(get_icon())

        # Create graph widget
        self.graphWidget = pg.PlotWidget(viewBox=FixedYViewBox())
        self.curves = [self.graphWidget.plot(pen='g') for _ in range(self.channels)]

        layout = QVBoxLayout()
        layout.addWidget(self.graphWidget)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)

        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_reading)
        layout.addWidget(self.toggle_button)

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
                    # Trim buffer to prevent excessive growth
                    if len(self.data_buffer[i]) > 1000:
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

    def closeEvent(self, event):
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()

import sys
import serial
from PyQt6.QtWidgets import QApplication, QMainWindow, QGridLayout, QPushButton, QWidget
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
        grid_layout = QGridLayout(central_widget)

        # Setup the pyqtgraph layout
        self.graph_layout = pg.GraphicsLayoutWidget()
        grid_layout.addWidget(self.graph_layout, 0, 0, 1, 2)

        # Create plot widgets for each channel
        self.plots = []
        self.curves = []

        for i in range(self.channels):
            if i % 2 == 0:
                plot = self.graph_layout.addPlot(row=i // 2, col=0)
            else:
                plot = self.graph_layout.addPlot(row=i // 2, col=1)

            plot.setTitle(f"Channel {i+1}")
            plot.setYRange(-0.5, 1.5, padding=0)
            curve = plot.plot(pen=pg.mkPen(color=pg.intColor(i, hues=16)))
            self.plots.append(plot)
            self.curves.append(curve)

        # Start/Stop buttons
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_reading)
        grid_layout.addWidget(self.start_button, 1, 0)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_reading)
        grid_layout.addWidget(self.stop_button, 1, 1)

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
        # Update the plot with the latest data
        for i in range(self.channels):
            t = np.arange(len(self.data_buffer[i]))
            self.curves[i].setData(t, self.data_buffer[i])

    def closeEvent(self, event):
        self.worker.stop_worker()  # Stop the worker when the window is closed
        self.worker.quit()
        event.accept()


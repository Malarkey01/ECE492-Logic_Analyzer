import serial
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
import pyqtgraph as pg
from aesthetic import get_icon

class SerialWorker(QThread):
    data_ready = pyqtSignal(list)

    def __init__(self, port, baudrate):
        super().__init__()
        self.is_running = True
        self.buffer = []  # Buffer to store incoming data
        try:
            self.serial = serial.Serial(port, baudrate)
        except serial.SerialException as e:
            print(f"Failed to open serial port: {str(e)}")
            self.is_running = False

        # Timer to print buffer contents every 10 seconds
        self.print_timer = QTimer()
        self.print_timer.timeout.connect(self.print_buffer)
        self.print_timer.start(10000)  # 10 seconds

    def run(self):
        while self.is_running:
            if self.serial.in_waiting:
                data = self.serial.read(self.serial.in_waiting).splitlines()
                processed_data = []
                for line in data:
                    try:
                        data_value = int(line.strip())
                        processed_data.append(data_value)
                        self.buffer.append(data_value)  # Add data to buffer
                    except ValueError:
                        continue
                self.data_ready.emit(processed_data)

    def stop_worker(self):
        self.is_running = False
        self.print_timer.stop()  # Stop the timer when the worker stops
        if self.serial.is_open:
            self.serial.close()

    def print_buffer(self):
        """Prints the contents of the buffer to the terminal every 10 seconds."""
        if self.buffer:
            print(f"Buffer contents (last 10 seconds): {self.buffer}")
            # Clear the buffer after printing
            self.buffer.clear()
        else:
            print("Buffer is empty")

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

    def translateBy(self, *args, **kwargs):
        pass

class LogicDisplay(QMainWindow):
    def __init__(self, port, baudrate, channels):
        super().__init__()

        self.setWindowTitle("Logic Display")
        self.worker = SerialWorker(port, baudrate)
        self.worker.data_ready.connect(self.update_graph)

        self.graph = pg.PlotWidget()
        self.graph.setBackground('w')
        self.graph.setTitle("Logic Signal")
        self.graph.setLabel('left', 'Amplitude')
        self.graph.setLabel('bottom', 'Time (s)')
        self.graph.setYRange(0, 1)

        layout = QVBoxLayout()
        layout.addWidget(self.graph)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.data_lines = [self.graph.plot(pen=pg.mkPen(color='b')) for _ in range(channels)]
        self.data_buffer = [[] for _ in range(channels)]

        self.worker.start()

    def update_graph(self, data):
        for i in range(min(len(self.data_lines), len(data))):
            self.data_buffer[i].append(data[i])
            self.data_lines[i].setData(self.data_buffer[i])

    def closeEvent(self, event):
        self.worker.stop_worker()
        event.accept()

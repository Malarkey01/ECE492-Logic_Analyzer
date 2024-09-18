import sys
import serial
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMenu,
    QInputDialog,
    QPushButton,
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
import pyqtgraph as pg
from aesthetic import get_icon
import numpy as np

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
        
        self.setWindowIcon(get_icon())

        self.data_buffer = [[] for _ in range(self.channels)]
        self.channel_visibility = [False] * self.channels

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

        self.curves = []
        for i in range(self.channels):
            curve = self.plot.plot(pen=pg.mkPen(color=pg.intColor(i, hues=16)))
            curve.setVisible(self.channel_visibility[i])
            self.curves.append(curve)

        button_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        self.channel_buttons = []
        for i in range(self.channels):
            label = f"DIO {i+1}"
            button = EditableButton(label)
            button.setCheckable(True)
            button.setChecked(False)
            button.toggled.connect(lambda checked, idx=i: self.toggle_channel(idx, checked))
            button_layout.addWidget(button)
            self.channel_buttons.append(button)

        self.toggle_button = QPushButton("Start")
        self.toggle_button.clicked.connect(self.toggle_reading)
        button_layout.addWidget(self.toggle_button)

    def toggle_channel(self, channel_idx, is_checked):
        self.channel_visibility[channel_idx] = is_checked
        self.curves[channel_idx].setVisible(is_checked)

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

    def closeEvent(self, event):
        self.worker.stop_worker()
        self.worker.quit()
        self.worker.wait()
        event.accept()

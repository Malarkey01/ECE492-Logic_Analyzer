from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QThread, pyqtSignal
import serial
import time

class SerialThread(QThread):
    received_signal = pyqtSignal(str)  # Custom signal to update GUI

    def __init__(self, port, baudrate):
        super().__init__()
        self.ser = serial.Serial(port, baudrate, timeout=1)

    def run(self):
        try:
            while True:
                if self.ser.in_waiting:
                    data = self.ser.readline().decode('utf-8').rstrip()
                    self.received_signal.emit(f"Received: {data}")
                time.sleep(0.1)
        except Exception as e:
            print(f"Error in serial thread: {e}")
        finally:
            self.ser.close()

class SerialApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # Setting up the window icon
        self.setWindowIcon(QIcon("C:/Users/Xevious/Desktop/Kaps.png"))  # Replace 'path_to_icon/icon.png' with the actual path to your icon

        self.setStyleSheet("""
            QMainWindow {
                background-color: #333333;
                color: #cccccc;
            }
            QPushButton {
                background-color: #555555;
                color: #cccccc;
                border: 1px solid #666666;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #777777;
            }
            QTextEdit {
                background-color: #222222;
                color: #cccccc;
            }
        """)

        self.setWindowTitle("Serial Monitor")
        self.setGeometry(100, 100, 480, 320)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.text_display = QTextEdit(central_widget)
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)

        self.button1 = QPushButton("Button 1", central_widget)
        self.button2 = QPushButton("Button 2", central_widget)
        layout.addWidget(self.button1)
        layout.addWidget(self.button2)

        # Serial thread
        self.serial_thread = SerialThread('COM3', 115200)  # Adjust your COM port here
        self.serial_thread.received_signal.connect(self.update_display)
        self.serial_thread.start()

    def update_display(self, message):
        self.text_display.append(message)

if __name__ == "__main__":
    app = QApplication([])
    window = SerialApp()
    window.show()
    app.exec()

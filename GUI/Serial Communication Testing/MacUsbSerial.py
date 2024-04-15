from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QThread, pyqtSignal
import serial

class CommunicationThread(QThread):
    received_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, port=None, baudrate=None, mode="serial"):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.mode = mode
        self.com = None

    def run(self):
        if not self.setup_connection():
            return  # Exit the thread if connection setup fails

        try:
            while True:
                if self.mode == "serial" and self.com.in_waiting:
                    data = self.com.readline().decode('utf-8').rstrip()
                    self.received_signal.emit(f"Received: {data}")
                elif self.mode == "i2c":
                    data = self.com.read_i2c_data()
                    self.received_signal.emit(f"Received I2C: {data}")
                elif self.mode == "spi":
                    data = self.com.transfer_spi_data([0x01])
                    self.received_signal.emit(f"Received SPI: {data[0]}")
                self.sleep(0.1)
        except Exception as e:
            self.error_signal.emit(f"Error in {self.mode} thread: {e}")
        finally:
            if self.com and self.mode in ["serial", "spi", "i2c"]:
                self.com.close()

    def setup_connection(self):
        try:
            if self.mode == "serial":
                self.com = serial.Serial(self.port, self.baudrate, timeout=1)
            elif self.mode == "i2c":
                self.com = initialize_usb_to_i2c_device()
            elif self.mode == "spi":
                self.com = initialize_usb_to_spi_device()
            return True
        except Exception as e:
            self.error_signal.emit(f"Failed to establish {self.mode} connection: {e}")
            return False

def initialize_usb_to_i2c_device():
    return None

def initialize_usb_to_spi_device():
    return None

class CommunicationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # self.setWindowIcon(QIcon("C:/Users/Xevious/Desktop/Kaps.png"))  # Replace 'path_to_icon/icon.png' with the actual path to your icon

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
        
        self.setWindowTitle("Communication Monitor")
        self.setGeometry(100, 100, 480, 320)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.text_display = QTextEdit(central_widget)
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)

        self.button_serial = QPushButton("UTF-8 Serial", central_widget)
        self.button_i2c = QPushButton("I2C Communication", central_widget)
        self.button_spi = QPushButton("SPI Communication", central_widget)
        layout.addWidget(self.button_serial)
        layout.addWidget(self.button_i2c)
        layout.addWidget(self.button_spi)

        self.button_serial.clicked.connect(lambda: self.start_communication("serial", '/dev/tty.usbmodem11303', 115200))
        self.button_i2c.clicked.connect(lambda: self.start_communication("i2c"))
        self.button_spi.clicked.connect(lambda: self.start_communication("spi"))

    def start_communication(self, mode, port=None, baudrate=None):
        self.com_thread = CommunicationThread(port, baudrate, mode)
        self.com_thread.received_signal.connect(self.update_display)
        self.com_thread.error_signal.connect(self.display_error)
        self.com_thread.start()

    def update_display(self, message):
        self.text_display.append(message)

    def display_error(self, message):
        QMessageBox.critical(self, "Connection Error", message + "\n\nPlease check your connection settings and try again.")

if __name__ == "__main__":
    app = QApplication([])
    window = CommunicationApp()
    window.show()
    app.exec()

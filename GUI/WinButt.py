import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QWidget)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("My App")
        
        button = QPushButton("Push Me!")
        
        # self.setFixedSize(QSize(1280, 720))
        self.setMinimumSize(QSize(400, 300))
        # self.setMaximumSize(QSize(1280, 720))
        
        self.setCentralWidget(button)
        
app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()


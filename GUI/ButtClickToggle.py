import sys
from PySide6.QtCore import QSize
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setMinimumSize(QSize(400, 300))
        self.setWindowTitle("My App")
        
        button = QPushButton("Push Me!")
        self.setCentralWidget(button)
        
        button.setCheckable(True)
        button.clicked.connect(self.button_was_clicked)
        button.clicked.connect(self.button_was_toggled)    
        
    def button_was_clicked(self):
        print("Clicked!")
        
    def button_was_toggled(self, checked):
        print("Checked?", checked)
        
app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()


import sys
from PyQt6.QtWidgets import QApplication
from connection import SerialApp

def main():
    app = QApplication(sys.argv)
    window = SerialApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

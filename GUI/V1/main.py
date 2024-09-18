import sys
from PyQt6.QtWidgets import QApplication
from connection import SerialApp
from aesthetic import apply_styles  # Import the apply_styles function

def main():
    app = QApplication(sys.argv)
    apply_styles(app)  # Apply the dark mode and icon
    window = SerialApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt6.QtCore import QSize, Qt
from HomeWindow import HomeWindow

if __name__ == "__main__":
    app = QApplication([])

    window = HomeWindow()
    window.show()

    app.exec()

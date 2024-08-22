from PyQt6.QtWidgets import QApplication

from HomeWindow import HomeWindow

if __name__ == "__main__":
    app = QApplication([])

    window = HomeWindow()
    window.show()

    app.exec()

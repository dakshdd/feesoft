import sys
import os
import shutil
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel
from PyQt5.QtGui import QIcon, QFont


class RemoteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Remote App - PALAK IT & SECURITY")
        self.setGeometry(200, 200, 400, 300)

        layout = QVBoxLayout()

        title = QLabel("PALAK IT & SECURITY")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)

        # Buttons
        btn_tally = QPushButton("Ritu-Tally")
        btn_tally.setIcon(QIcon("icons/tally.png"))   # icon path
        btn_tally.clicked.connect(self.launch_tally)
        layout.addWidget(btn_tally)

        btn_data = QPushButton("Ritu-Data")
        btn_data.setIcon(QIcon("icons/data.png"))
        btn_data.clicked.connect(self.open_data)
        layout.addWidget(btn_data)

        btn_export = QPushButton("Ritu-Export")
        btn_export.setIcon(QIcon("icons/export.png"))
        btn_export.clicked.connect(self.export_data)
        layout.addWidget(btn_export)

        btn_logoff = QPushButton("Logoff")
        btn_logoff.setIcon(QIcon("icons/power.png"))
        btn_logoff.clicked.connect(self.logoff)
        layout.addWidget(btn_logoff)

        self.setLayout(layout)

    def launch_tally(self):
        os.startfile("C:/Program Files/Tally/Tally.exe")

    def open_data(self):
        source = "C:/RemoteApp/Data/input.xlsx"
        destination = "C:/RemoteApp/Data/output.xlsx"
        shutil.copy(source, destination)
        print("Data copied successfully!")

    def export_data(self):
        os.startfile("C:/RemoteApp/Export/export.bat")

    def logoff(self):
        QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RemoteApp()
    window.show()
    sys.exit(app.exec_())

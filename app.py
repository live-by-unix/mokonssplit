import sys
import os
import threading
import zipfile

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QProgressBar, QMessageBox, QLineEdit, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QPalette, QColor


# -----------------------------
# Worker Signals
# -----------------------------
class WorkerSignals(QObject):
    progress = Signal(int)
    done = Signal(str)
    error = Signal(str)


# -----------------------------
# Compression Thread
# -----------------------------
class CompressorThread(threading.Thread):
    def __init__(self, input_path, output_path, signals):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.signals = signals

    def run(self):
        try:
            total_size = os.path.getsize(self.input_path)
            processed = 0

            with zipfile.ZipFile(self.output_path, "w", zipfile.ZIP_DEFLATED) as z:
                with open(self.input_path, "rb") as f:
                    chunk = f.read(1024 * 1024)
                    while chunk:
                        z.writestr(os.path.basename(self.input_path), chunk)
                        processed += len(chunk)
                        progress = int((processed / total_size) * 100)
                        self.signals.progress.emit(progress)
                        chunk = f.read(1024 * 1024)

            self.signals.done.emit("Compression complete!")

        except Exception as e:
            self.signals.error.emit(str(e))


# -----------------------------
# Decompression Thread
# -----------------------------
class DecompressorThread(threading.Thread):
    def __init__(self, input_path, output_dir, signals):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.signals = signals

    def run(self):
        try:
            with zipfile.ZipFile(self.input_path, "r") as z:
                files = z.namelist()
                total = len(files) or 1

                for i, file in enumerate(files):
                    z.extract(file, self.output_dir)
                    progress = int(((i + 1) / total) * 100)
                    self.signals.progress.emit(progress)

            self.signals.done.emit("Decompression complete!")

        except Exception as e:
            self.signals.error.emit(str(e))


# -----------------------------
# Main App Window
# -----------------------------
class MokonsSplit(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MokonsSplit")
        self.resize(600, 350)

        # -----------------------------
        # Light/Dark Mode Toggle
        # -----------------------------
        self.theme_toggle = QCheckBox("Dark Mode")
        self.theme_toggle.stateChanged.connect(self.toggle_theme)

        # -----------------------------
        # Compression UI
        # -----------------------------
        self.compress_label = QLabel("Compression")
        self.compress_label.setAlignment(Qt.AlignCenter)

        self.compress_path = QLineEdit()
        self.compress_path.setPlaceholderText("Specify absolute path of file/folder")

        self.compress_select = QPushButton("Select")
        self.compress_select.clicked.connect(self.select_compress_file)

        self.compress_button = QPushButton("Compress")
        self.compress_button.clicked.connect(self.compress_file)

        self.compress_progress = QProgressBar()

        compress_row = QHBoxLayout()
        compress_row.addWidget(self.compress_path)
        compress_row.addWidget(self.compress_select)

        # -----------------------------
        # Decompression UI
        # -----------------------------
        self.decompress_label = QLabel("Decompression")
        self.decompress_label.setAlignment(Qt.AlignCenter)

        self.decompress_path = QLineEdit()
        self.decompress_path.setPlaceholderText(
            "Specify path of where you want MokonsSplit to put the uncompressed file"
        )

        self.decompress_select = QPushButton("Select")
        self.decompress_select.clicked.connect(self.select_decompress_folder)

        self.decompress_button = QPushButton("Decompress")
        self.decompress_button.clicked.connect(self.decompress_file)

        self.decompress_progress = QProgressBar()

        decompress_row = QHBoxLayout()
        decompress_row.addWidget(self.decompress_path)
        decompress_row.addWidget(self.decompress_select)

        # -----------------------------
        # Layout
        # -----------------------------
        layout = QVBoxLayout()
        layout.addWidget(self.theme_toggle)

        layout.addWidget(self.compress_label)
        layout.addLayout(compress_row)
        layout.addWidget(self.compress_button)
        layout.addWidget(self.compress_progress)

        layout.addSpacing(20)

        layout.addWidget(self.decompress_label)
        layout.addLayout(decompress_row)
        layout.addWidget(self.decompress_button)
        layout.addWidget(self.decompress_progress)

        self.setLayout(layout)

    # -----------------------------
    # Theme Toggle
    # -----------------------------
    def toggle_theme(self):
        dark = self.theme_toggle.isChecked()
        palette = QPalette()

        if dark:
            palette.setColor(QPalette.Window, QColor(30, 30, 30))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(45, 45, 45))
            palette.setColor(QPalette.Text, Qt.white)
        else:
            palette = QApplication.style().standardPalette()

        QApplication.instance().setPalette(palette)

    # -----------------------------
    # Compression Logic
    # -----------------------------
    def select_compress_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Compress")
        if path:
            self.compress_path.setText(path)

    def compress_file(self):
        input_path = self.compress_path.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "Invalid input path.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Compressed File", os.path.basename(input_path) + ".zip"
        )
        if not output_path:
            return

        self.start_thread(
            CompressorThread, input_path, output_path, self.compress_progress
        )

    # -----------------------------
    # Decompression Logic
    # -----------------------------
    def select_decompress_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.decompress_path.setText(folder)

    def decompress_file(self):
        input_path, _ = QFileDialog.getOpenFileName(self, "Select ZIP File")
        if not input_path:
            return

        output_dir = self.decompress_path.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "Error", "Invalid output directory.")
            return

        self.start_thread(
            DecompressorThread, input_path, output_dir, self.decompress_progress
        )

    # -----------------------------
    # Thread Handler
    # -----------------------------
    def start_thread(self, thread_class, *args):
        progress_bar = args[-1]
        progress_bar.setValue(0)

        signals = WorkerSignals()
        signals.progress.connect(progress_bar.setValue)
        signals.done.connect(lambda msg: QMessageBox.information(self, "Success", msg))
        signals.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))

        thread = thread_class(*args[:-1], signals)
        thread.start()


# -----------------------------
# Entry Point
# -----------------------------
def main():
    app = QApplication(sys.argv)
    window = MokonsSplit()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

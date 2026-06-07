import sys
import os
import threading
import zipfile

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QProgressBar,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QObject


class WorkerSignals(QObject):
    progress = Signal(int)
    done = Signal(str)
    error = Signal(str)


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
                        # Store the file in chunks under its basename
                        z.writestr(os.path.basename(self.input_path), chunk)
                        processed += len(chunk)
                        progress = int((processed / total_size) * 100)
                        self.signals.progress.emit(progress)
                        chunk = f.read(1024 * 1024)

            self.signals.done.emit("Compression complete!")
        except Exception as e:
            self.signals.error.emit(str(e))


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


class MokonsSplit(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MokonsSplit")
        self.resize(500, 300)

        self.label = QLabel("Choose an action:")
        self.label.setAlignment(Qt.AlignCenter)

        self.compress_btn = QPushButton("Compress File")
        self.decompress_btn = QPushButton("Decompress File")

        self.progress = QProgressBar()
        self.progress.setValue(0)

        layout = QVBoxLayout()
        layout.addWidget(self.label)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.compress_btn)
        btn_row.addWidget(self.decompress_btn)
        layout.addLayout(btn_row)

        layout.addWidget(self.progress)
        self.setLayout(layout)

        self.compress_btn.clicked.connect(self.compress_file)
        self.decompress_btn.clicked.connect(self.decompress_file)

        self._thread = None
        self._signals = None

    def compress_file(self):
        input_path, _ = QFileDialog.getOpenFileName(self, "Select File to Compress")
        if not input_path:
            return

        default_name = os.path.basename(input_path) + ".zip"
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Compressed File", default_name
        )
        if not output_path:
            return

        self.start_thread(CompressorThread, input_path, output_path)

    def decompress_file(self):
        input_path, _ = QFileDialog.getOpenFileName(self, "Select ZIP File")
        if not input_path:
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not output_dir:
            return

        self.start_thread(DecompressorThread, input_path, output_dir)

    def start_thread(self, thread_class, *args):
        self.progress.setValue(0)

        self._signals = WorkerSignals()
        self._signals.progress.connect(self.progress.setValue)
        self._signals.done.connect(self.show_done)
        self._signals.error.connect(self.show_error)

        self._thread = thread_class(*args, self._signals)
        self._thread.start()

    def show_done(self, msg: str):
        QMessageBox.information(self, "Success", msg)

    def show_error(self, msg: str):
        QMessageBox.critical(self, "Error", msg)


def main():
    app = QApplication(sys.argv)
    window = MokonsSplit()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

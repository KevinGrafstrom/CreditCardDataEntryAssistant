import sys
import re

from paddleocr import PaddleOCR
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

class OcrWorker(QObject):
    finished = Signal(list, str, str, str)
    failed = Signal(str)

    def __init__(self, ocr, image_path):
        super().__init__()
        self.ocr = ocr
        self.image_path = image_path

    def run(self):
        try:
            results = self.ocr.predict(self.image_path)

            recognized_text = []
            card_number = ""
            cvv = ""
            exp_date = ""

            for page in results:
                for text in page["rec_texts"]:
                    recognized_text.append(text)

                    card_number_matches = re.findall(r"\d{4}\s?\d{4}\s?\d{4}\s?\d{4}", text)

                    if len(card_number_matches) > 0:
                        card_number = re.sub(r"\s+", "", card_number_matches[0])

                    cvv_matches = re.fullmatch(r"\s*(\d{3})\s*", text)
                    if cvv_matches is not None:
                        cvv = cvv_matches.group(1)

                    exp_date_matches = re.fullmatch(r"\s*(\d{2})/(\d{2})\s*", text)
                    if exp_date_matches is not None:
                        exp_date = exp_date_matches.group(1) + exp_date_matches.group(2)

            self.finished.emit(recognized_text, card_number, cvv, exp_date)
        except Exception as error:
            self.failed.emit(str(error))

class OcrWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ocr = PaddleOCR(lang="en")
        self.image_path = None
        self.card_number = ""
        self.cvv = ""
        self.exp_date = ""

        self.setWindowTitle("OCR Memory")
        self.resize(800, 600)

        self.title_label = QLabel("OCR Memory")

        self.selected_image_label = QLabel("No image selected")

        self.choose_image_button = QPushButton("Choose Image")
        self.choose_image_button.clicked.connect(self.choose_image)

        self.run_ocr_button = QPushButton("Run OCR")
        self.run_ocr_button.clicked.connect(self.run_ocr)
        self.run_ocr_button.setEnabled(False)

        self.copy_card_number_button = QPushButton("Copy Card Number to Clipboard")
        self.copy_card_number_button.clicked.connect(self.copy_card_number_to_clipboard)
        self.copy_card_number_button.setEnabled(False)

        self.copy_cvv_button = QPushButton("Copy CVV to Clipboard")
        self.copy_cvv_button.clicked.connect(self.copy_cvv_to_clipboard)
        self.copy_cvv_button.setEnabled(False)

        self.copy_exp_date_button = QPushButton("Copy Expiry Date to Clipboard")
        self.copy_exp_date_button.clicked.connect(self.copy_exp_date_to_clipboard)
        self.copy_exp_date_button.setEnabled(False)

        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("OCR results will appear here...")

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.selected_image_label)
        layout.addWidget(self.choose_image_button)
        layout.addWidget(self.run_ocr_button)
        layout.addWidget(self.copy_card_number_button)
        layout.addWidget(self.copy_cvv_button)
        layout.addWidget(self.copy_exp_date_button)
        layout.addWidget(self.output_text)

        container = QWidget()
        container.setLayout(layout)

        self.setCentralWidget(container)

    def choose_image(self):
        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose an image",
            "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.webp);;All Files (*)",
        )

        if not image_path:
            return

        self.image_path = image_path
        self.selected_image_label.setText(image_path)
        self.run_ocr_button.setEnabled(True)
        self.copy_card_number_button.setEnabled(False)
        self.copy_cvv_button.setEnabled(False)
        self.copy_exp_date_button.setEnabled(False)
        self.output_text.clear()

    def copy_card_number_to_clipboard(self):
        QApplication.clipboard().setText(self.card_number)

    def copy_cvv_to_clipboard(self):
        QApplication.clipboard().setText(self.cvv)

    def copy_exp_date_to_clipboard(self):
        QApplication.clipboard().setText(self.exp_date)

    def run_ocr(self):
        if not self.image_path:
            return

        self.output_text.setPlainText("Running OCR...")
        self.output_text.repaint()

        self.run_ocr_button.setEnabled(False)
        self.copy_card_number_button.setEnabled(False)
        self.copy_cvv_button.setEnabled(False)
        self.copy_exp_date_button.setEnabled(False)

        QTimer.singleShot(100, self.start_ocr_worker)

    def start_ocr_worker(self):
        self.thread = QThread()
        self.worker = OcrWorker(self.ocr, self.image_path)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.handle_ocr_finished)
        self.worker.failed.connect(self.handle_ocr_failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)

        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def handle_ocr_finished(self, recognized_text, card_number, cvv, exp_date):
        self.card_number = card_number
        self.cvv = cvv
        self.exp_date = exp_date

        all_text = "\n".join(recognized_text)

        all_text = (
            f"{all_text}"
            f"\n card number: {self.card_number}"
            f"\n cvv: {self.cvv}"
            f"\n exp date: {self.exp_date}"
        )

        if recognized_text:
            self.output_text.setPlainText("OCR Complete.")
            # self.output_text.setPlainText(all_text)
        else:
            self.output_text.setPlainText("No text found.")

        self.copy_card_number_button.setEnabled(bool(self.card_number))
        self.copy_cvv_button.setEnabled(bool(self.cvv))
        self.copy_exp_date_button.setEnabled(bool(self.exp_date))
        self.run_ocr_button.setEnabled(True)

    def handle_ocr_failed(self, error_message):
        self.output_text.setPlainText(f"OCR failed:\n{error_message}")
        self.run_ocr_button.setEnabled(True)


def main():
    app = QApplication(sys.argv)

    window = OcrWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
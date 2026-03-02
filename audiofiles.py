import sys
import os
from io import BytesIO

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QCheckBox,
    QGroupBox, QHBoxLayout, QLabel,
    QFileDialog, QSpinBox
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from mutagen import File
from mutagen.id3 import ID3, APIC
from mutagen.flac import Picture
from PIL import Image


SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".wav", ".ogg"}


class AudioFiles(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioFiles")
        self.resize(1000, 800)
        self.setAcceptDrops(True)

        self.files = []
        self.cover_image_path = None

        # ---------------- Rename Options ----------------
        self.track_cb = QCheckBox("Include Track Number")
        self.disc_cb = QCheckBox("Include Disc Number")
        self.artist_cb = QCheckBox("Include Artist")
        self.album_cb = QCheckBox("Include Album")
        self.title_cb = QCheckBox("Include Title")

        self.track_cb.setChecked(True)
        self.title_cb.setChecked(True)

        for cb in [self.track_cb, self.disc_cb,
                   self.artist_cb, self.album_cb, self.title_cb]:
            cb.stateChanged.connect(self.refresh_table)

        self.update_metadata_cb = QCheckBox("Update Metadata to Match Rename")
        self.update_metadata_cb.stateChanged.connect(self.on_update_metadata_toggled)

        rename_layout = QVBoxLayout()
        for cb in [self.track_cb, self.disc_cb,
                   self.artist_cb, self.album_cb, self.title_cb]:
            rename_layout.addWidget(cb)
        rename_layout.addWidget(self.update_metadata_cb)

        rename_group = QGroupBox("Rename Options")
        rename_group.setLayout(rename_layout)

        # ---------------- Cover Art Section ----------------
        self.cover_cb = QCheckBox("Replace Cover Art")

        self.upload_button = QPushButton("Upload Cover Image")
        self.upload_button.clicked.connect(self.load_cover_image)

        self.width_input = QSpinBox()
        self.width_input.setRange(50, 3000)
        self.width_input.setValue(600)

        self.height_input = QSpinBox()
        self.height_input.setRange(50, 3000)
        self.height_input.setValue(600)

        self.preserve_cb = QCheckBox("Preserve Aspect Ratio")
        self.preserve_cb.stateChanged.connect(self.toggle_resize_inputs)

        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Set cover art size to"))
        size_layout.addWidget(self.width_input)
        size_layout.addWidget(QLabel("px by"))
        size_layout.addWidget(self.height_input)
        size_layout.addWidget(QLabel("px"))

        cover_layout = QVBoxLayout()
        cover_layout.addWidget(self.cover_cb)
        cover_layout.addWidget(self.upload_button)
        cover_layout.addLayout(size_layout)
        cover_layout.addWidget(self.preserve_cb)

        cover_group = QGroupBox("Cover Art Options")
        cover_group.setLayout(cover_layout)

        # ---------------- Table ----------------
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name"])
        self.table.horizontalHeader().setStretchLastSection(True)

        # ---------------- Rename Button ----------------
        self.rename_button = QPushButton("Rename Files")
        self.rename_button.clicked.connect(self.rename_files)

        # ---------------- Progress Bar ----------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # ---------------- Main Layout ----------------
        layout = QVBoxLayout()
        layout.addWidget(rename_group)
        layout.addWidget(cover_group)
        layout.addWidget(self.table)
        layout.addWidget(self.rename_button)
        layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # ---------------- Menu Bar ----------------
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")

        open_file_action = QAction("Open File...", self)
        open_file_action.setShortcut("Ctrl+O")
        open_file_action.triggered.connect(self.open_files)
        file_menu.addAction(open_file_action)

        open_folder_action = QAction("Open Folder...", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)

    # ---------------- Menu Bar Actions ----------------
    def open_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Audio Files",
            "",
            "Audio Files (*.mp3 *.flac *.m4a *.wav *.ogg);;All Files (*)"
        )
        for path in file_paths:
            self.add_file(path)
        if file_paths:
            self.refresh_table()

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Open Folder",
            ""
        )
        if folder_path:
            for root, _, files in os.walk(folder_path):
                for f in files:
                    self.add_file(os.path.join(root, f))
            self.refresh_table()

    # ---------------- Menu Actions ----------------
    def open_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Audio Files",
            "",
            "Audio Files (*.mp3 *.flac *.m4a *.wav *.ogg);;All Files (*)"
        )
        for path in file_paths:
            self.add_file(path)
        if file_paths:
            self.refresh_table()

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Open Folder",
            ""
        )
        if folder_path:
            for root, _, files in os.walk(folder_path):
                for f in files:
                    self.add_file(os.path.join(root, f))
            self.refresh_table()

    # ---------------- Drag & Drop ----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                self.add_file(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for f in files:
                        self.add_file(os.path.join(root, f))
        self.refresh_table()

    def add_file(self, filepath):
        if filepath not in self.files:
            if os.path.splitext(filepath)[1].lower() in SUPPORTED_EXTENSIONS:
                self.files.append(filepath)

    # ---------------- Cover Logic ----------------
    def toggle_resize_inputs(self):
        if self.preserve_cb.isChecked():
            self.width_input.setEnabled(False)
            self.height_input.setEnabled(False)
        else:
            self.width_input.setEnabled(True)
            self.height_input.setEnabled(True)

    def load_cover_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.cover_image_path = file_path
            QMessageBox.information(self, "Loaded", "Cover image loaded successfully.")

    def process_cover_image(self):
        if not self.cover_image_path:
            return None

        img = Image.open(self.cover_image_path)

        target_width = self.width_input.value()
        target_height = self.height_input.value()

        if self.preserve_cb.isChecked():
            img.thumbnail((target_width, target_height), Image.LANCZOS)
        else:
            img = img.resize((target_width, target_height), Image.LANCZOS)

        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG")
        return img_bytes.getvalue()

    def embed_cover(self, filepath, image_data):
        ext = os.path.splitext(filepath)[1].lower()

        try:
            if ext == ".mp3":
                audio = ID3(filepath)
                audio.delall("APIC")
                audio.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=image_data
                ))
                audio.save()

            elif ext == ".flac":
                audio = File(filepath)
                audio.clear_pictures()
                pic = Picture()
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.data = image_data
                audio.add_picture(pic)
                audio.save()
        except Exception:
            pass

    # ---------------- Metadata Warning ----------------
    def on_update_metadata_toggled(self, state):
        if state == Qt.Checked:
            result = QMessageBox.warning(
                self,
                "Warning: Metadata Will Be Modified",
                "Enabling this option will permanently overwrite the metadata tags "
                "(track number, disc number, artist, album, title) in your audio files "
                "to match your rename selections.\n\n"
                "This action cannot be undone. Are you sure you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if result == QMessageBox.No:
                self.update_metadata_cb.blockSignals(True)
                self.update_metadata_cb.setChecked(False)
                self.update_metadata_cb.blockSignals(False)

    def write_metadata(self, filepath, metadata, track_number):
        """Write back only the fields selected for renaming into the file's tags."""
        try:
            audio = File(filepath, easy=True)
            if not audio:
                return

            if self.track_cb.isChecked():
                audio["tracknumber"] = str(track_number)

            if self.disc_cb.isChecked():
                audio["discnumber"] = str(metadata["disc"])

            if self.artist_cb.isChecked():
                audio["artist"] = metadata["artist"]

            if self.album_cb.isChecked():
                audio["album"] = metadata["album"]

            if self.title_cb.isChecked():
                audio["title"] = metadata["title"]

            audio.save()
        except Exception:
            pass

    # ---------------- Metadata ----------------
    def get_metadata(self, filepath):
        audio = File(filepath, easy=True)
        if not audio:
            return None

        return {
            "track": int(audio.get("tracknumber", ["0"])[0].split('/')[0]),
            "disc": int(audio.get("discnumber", ["1"])[0].split('/')[0]),
            "artist": audio.get("artist", ["Unknown Artist"])[0],
            "album": audio.get("album", ["Unknown Album"])[0],
            "title": audio.get("title", ["Unknown Title"])[0],
        }

    # ---------------- Sorting + Disc Logic ----------------
    def generate_sorted_data(self):
        file_data = []

        for f in self.files:
            metadata = self.get_metadata(f)
            if metadata:
                file_data.append((f, metadata))

        file_data.sort(key=lambda x: (x[1]["disc"], x[1]["track"]))

        discs = {d[1]["disc"] for d in file_data}
        multi_disc = len(discs) > 1

        sequential_map = {}
        counter = 1

        for f, metadata in file_data:
            if multi_disc and not self.disc_cb.isChecked():
                sequential_map[f] = counter
                counter += 1
            else:
                sequential_map[f] = metadata["track"]

        return file_data, sequential_map

    # ---------------- Filename Builder ----------------
    def build_filename(self, metadata, ext, track_number):
        parts = []

        if self.track_cb.isChecked():
            parts.append(str(track_number).zfill(2))

        if self.disc_cb.isChecked():
            parts.append(f"Disc{metadata['disc']}")

        if self.artist_cb.isChecked():
            parts.append(metadata["artist"])

        if self.album_cb.isChecked():
            parts.append(metadata["album"])

        if self.title_cb.isChecked():
            parts.append(metadata["title"])

        if not parts:
            return None

        return " - ".join(parts) + ext

    # ---------------- Preview Table ----------------
    def refresh_table(self):
        self.table.setRowCount(len(self.files))
        file_data, sequential_map = self.generate_sorted_data()

        for row, (filepath, metadata) in enumerate(file_data):
            original_name = os.path.basename(filepath)
            ext = os.path.splitext(filepath)[1]
            track_number = sequential_map[filepath]

            new_name = self.build_filename(metadata, ext, track_number)

            original_item = QTableWidgetItem(original_name)
            original_item.setFlags(Qt.ItemIsEnabled)

            new_item = QTableWidgetItem(new_name or "ERROR")
            new_item.setFlags(Qt.ItemIsEnabled)

            if new_name:
                new_path = os.path.join(os.path.dirname(filepath), new_name)
                if os.path.exists(new_path) and new_path != filepath:
                    new_item.setBackground(Qt.red)

            self.table.setItem(row, 0, original_item)
            self.table.setItem(row, 1, new_item)

    # ---------------- Rename + Cover Apply ----------------
    def rename_files(self):
        file_data, sequential_map = self.generate_sorted_data()

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(file_data))

        image_data = None
        if self.cover_cb.isChecked():
            image_data = self.process_cover_image()
            if not image_data:
                QMessageBox.warning(self, "Error", "No cover image selected.")
                self.progress_bar.setVisible(False)
                return

        processed = 0

        for i, (filepath, metadata) in enumerate(file_data):
            ext = os.path.splitext(filepath)[1]
            track_number = sequential_map[filepath]
            new_name = self.build_filename(metadata, ext, track_number)

            if not new_name:
                continue

            new_path = os.path.join(os.path.dirname(filepath), new_name)

            try:
                if new_path != filepath:
                    os.rename(filepath, new_path)
                    filepath = new_path

                if image_data:
                    self.embed_cover(filepath, image_data)

                if self.update_metadata_cb.isChecked():
                    self.write_metadata(filepath, metadata, track_number)

                processed += 1
            except Exception:
                pass

            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()

        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Done", f"Processed {processed} files.")
        self.files.clear()
        self.refresh_table()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioFiles()
    window.show()
    sys.exit(app.exec())

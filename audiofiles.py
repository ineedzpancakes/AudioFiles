import sys
import os
from io import BytesIO
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QCheckBox,
    QGroupBox, QHBoxLayout, QLabel,
    QFileDialog, QSpinBox, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtCore import Qt
from mutagen import File
from mutagen.id3 import ID3, APIC
from mutagen.flac import Picture
from PIL import Image


SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".wav", ".ogg"}

FIELD_LABELS = {
    "track":  "Include Track Number",
    "disc":   "Include Disc Number",
    "artist": "Include Artist",
    "album":  "Include Album",
    "title":  "Include Title",
    "date":   "Include Date (YYYYMMDD)",
}


class DraggableFieldList(QListWidget):
    """Checkable, drag-to-reorder list of rename fields."""

    def __init__(self, on_change, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setSpacing(1)
        self.setFixedHeight(len(FIELD_LABELS) * 26 + 6)

        default_checked = {"track", "title"}
        for key, label in FIELD_LABELS.items():
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable |
                Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled
            )
            item.setCheckState(Qt.Checked if key in default_checked else Qt.Unchecked)
            self.addItem(item)

        self.model().rowsMoved.connect(self._emit_change)
        self.itemChanged.connect(self._emit_change)

    def _emit_change(self, *_):
        self.on_change()

    def ordered_checked_keys(self):
        return [
            self.item(i).data(Qt.UserRole)
            for i in range(self.count())
            if self.item(i).checkState() == Qt.Checked
        ]

    def is_checked(self, key):
        for i in range(self.count()):
            item = self.item(i)
            if item.data(Qt.UserRole) == key:
                return item.checkState() == Qt.Checked
        return False


class AudioRenamer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioFiles")
        self.resize(1000, 800)
        self.setAcceptDrops(True)

        self.files = []
        self.cover_image_path = None

        # ---------------- Rename Options ----------------
        self.field_list = DraggableFieldList(self.refresh_table)

        self.update_metadata_cb = QCheckBox("Update Metadata to Match Rename")
        self.update_metadata_cb.stateChanged.connect(self.on_update_metadata_toggled)

        rename_layout = QVBoxLayout()
        rename_layout.addWidget(QLabel("Drag to reorder · Check to include:"))
        rename_layout.addWidget(self.field_list)
        rename_layout.addWidget(self.update_metadata_cb)
        rename_layout.addStretch()

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

        self.cover_preview = QLabel()
        self.cover_preview.setFixedSize(120, 120)
        self.cover_preview.setAlignment(Qt.AlignCenter)
        self.cover_preview.setStyleSheet("border: 1px solid #aaa; background: #1a1a1a;")
        self.cover_preview.setText("No image")
        self.cover_preview.setVisible(False)

        cover_preview_layout = QHBoxLayout()
        cover_preview_layout.addStretch()
        cover_preview_layout.addWidget(self.cover_preview)
        cover_preview_layout.addStretch()

        cover_layout = QVBoxLayout()
        cover_layout.addWidget(self.cover_cb)
        cover_layout.addWidget(self.upload_button)
        cover_layout.addLayout(cover_preview_layout)
        cover_layout.addLayout(size_layout)
        cover_layout.addWidget(self.preserve_cb)
        cover_layout.addStretch()

        cover_group = QGroupBox("Cover Art Options")
        cover_group.setLayout(cover_layout)

        # ---------------- Table ----------------
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.Interactive)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)

        # ---------------- Rename Button ----------------
        self.rename_button = QPushButton("Rename Files")
        self.rename_button.clicked.connect(self.rename_files)

        # ---------------- Progress Bar ----------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # ---------------- Options Row (side by side) ----------------
        options_layout = QHBoxLayout()
        options_layout.addWidget(rename_group, stretch=1)
        options_layout.addWidget(cover_group, stretch=1)

        # ---------------- Main Layout ----------------
        layout = QVBoxLayout()
        layout.addLayout(options_layout)
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

    def showEvent(self, event):
        super().showEvent(event)
        total = self.table.viewport().width()
        self.table.setColumnWidth(0, total // 2)

    # ---------------- Menu Bar Actions ----------------
    def open_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Audio Files", "",
            "Audio Files (*.mp3 *.flac *.m4a *.wav *.ogg);;All Files (*)"
        )
        for path in file_paths:
            self.add_file(path)
        if file_paths:
            self.refresh_table()

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder", "")
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
        enabled = not self.preserve_cb.isChecked()
        self.width_input.setEnabled(enabled)
        self.height_input.setEnabled(enabled)

    def load_cover_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Cover Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.cover_image_path = file_path
            pixmap = QPixmap(file_path).scaled(
                120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.cover_preview.setPixmap(pixmap)
            self.cover_preview.setVisible(True)

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
                audio.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=image_data))
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
        if state == Qt.CheckState.Checked or state == 2:
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
        try:
            audio = File(filepath, easy=True)
            if not audio:
                return
            if self.field_list.is_checked("track"):
                audio["tracknumber"] = str(track_number)
            if self.field_list.is_checked("disc"):
                audio["discnumber"] = str(metadata["disc"])
            if self.field_list.is_checked("artist"):
                audio["artist"] = metadata["artist"]
            if self.field_list.is_checked("album"):
                audio["album"] = metadata["album"]
            if self.field_list.is_checked("title"):
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
            "track":  int(audio.get("tracknumber", ["0"])[0].split('/')[0]),
            "disc":   int(audio.get("discnumber",  ["1"])[0].split('/')[0]),
            "artist": audio.get("artist", ["Unknown Artist"])[0],
            "album":  audio.get("album",  ["Unknown Album"])[0],
            "title":  audio.get("title",  ["Unknown Title"])[0],
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
            if multi_disc and not self.field_list.is_checked("disc"):
                sequential_map[f] = counter
                counter += 1
            else:
                sequential_map[f] = metadata["track"]

        return file_data, sequential_map

    # ---------------- Filename Builder ----------------
    def build_filename(self, metadata, ext, track_number, filepath=None):
        parts = []
        for key in self.field_list.ordered_checked_keys():
            if key == "track":
                parts.append(str(track_number).zfill(2))
            elif key == "disc":
                parts.append(f"Disc{metadata['disc']}")
            elif key == "artist":
                parts.append(metadata["artist"])
            elif key == "album":
                parts.append(metadata["album"])
            elif key == "title":
                parts.append(metadata["title"])
            elif key == "date":
                if filepath and os.path.exists(filepath):
                    mtime = os.path.getmtime(filepath)
                    parts.append(datetime.fromtimestamp(mtime).strftime("%Y%m%d"))
                else:
                    parts.append(datetime.now().strftime("%Y%m%d"))

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
            new_name = self.build_filename(metadata, ext, track_number, filepath)

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
            new_name = self.build_filename(metadata, ext, track_number, filepath)

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
    window = AudioRenamer()
    window.show()
    sys.exit(app.exec())

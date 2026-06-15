import rumps
import sys
import os
import json
from pathlib import Path


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QListWidget, QListWidgetItem,
    QMessageBox, QFrame, QDialog, QSizePolicy
)
from PyQt6.QtGui import QCloseEvent, QFont
from PyQt6.QtCore import Qt



APP_NAME = "SullybaseClipboard"
SUPPORT_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
DATA_FILE = SUPPORT_DIR / "items.json"



class ItemEditor(QMainWindow):
    def __init__(self, parent=None, name="", content=""):
        super().__init__(parent)
        self.setWindowTitle("Item Editor")
        self.setMinimumSize(520, 360)
        self.result_name = None
        self.result_content = None


        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QWidget {
                background-color: #1a1a2e;
                color: #e8e8f0;
            }
            QLineEdit, QTextEdit {
                background-color: #0f0f1a;
                color: #e8e8f0;
                border: 1px solid #16213e;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton {
                background-color: #16213e;
                color: #e8e8f0;
                border: 1px solid #0f3460;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #1f4068;
                border: 1px solid #1f4068;
            }
        """)


        central = QWidget()
        self.setCentralWidget(central)


        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)


        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name")
        self.name_edit.setText(name)


        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Content")
        self.content_edit.setText(content)


        button_row = QHBoxLayout()
        button_row.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        save_btn = QPushButton("Save")
        cancel_btn.clicked.connect(self.handle_cancel)
        save_btn.clicked.connect(self.handle_save)
        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)


        layout.addWidget(QLabel("Name"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Content"))
        layout.addWidget(self.content_edit)
        layout.addLayout(button_row)


        central.setLayout(layout)


    def handle_cancel(self):
        self.result_name = None
        self.result_content = None
        self.close()


    def handle_save(self):
        name = self.name_edit.text().strip()
        content = self.content_edit.toPlainText()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a name.")
            return
        self.result_name = name
        self.result_content = content
        self.close()



class ClipboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sullybase Clipboard Organizer")
        self.setMinimumSize(400, 200)


        self.items = []
        self.last_copied_name = None


        self._setup_storage()
        self._setup_style()
        self._build_ui()
        self._load_items()
        self.refresh_list()


    def _setup_storage(self):
        SUPPORT_DIR.mkdir(parents=True, exist_ok=True)


    def _setup_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QWidget {
                background-color: #1a1a2e;
                color: #e8e8f0;
            }
            QLabel {
                color: #e8e8f0;
            }
            QListWidget {
                background-color: #0f0f1a;
                border: 1px solid #16213e;
                border-radius: 8px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 10px;
                margin: 4px;
                border-radius: 6px;
                background-color: #16213e;
            }
            QListWidget::item:selected {
                background-color: #1f4068;
            }
            QPushButton {
                background-color: #16213e;
                color: #e8e8f0;
                border: 1px solid #0f3460;
                border-radius: 6px;
                padding: 8px 14px;
                min-width: 72px;
            }
            QPushButton:hover {
                background-color: #1f4068;
                border: 1px solid #1f4068;
            }
        """)


    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)


        main = QVBoxLayout()
        main.setContentsMargins(18, 16, 18, 18)
        main.setSpacing(12)


        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)


        title_col = QVBoxLayout()
        self.title_label = QLabel("Sullybase Clipboard Organizer")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setWeight(QFont.Weight.Bold)
        self.title_label.setFont(title_font)


        self.last_label = QLabel("Last copied: None")
        small_font = QFont()
        small_font.setPointSize(10)
        small_font.setWeight(QFont.Weight.Light)
        self.last_label.setFont(small_font)
        self.last_label.setStyleSheet("color: #8b9bb4;")


        title_col.addWidget(self.title_label)
        title_col.addWidget(self.last_label)
        top_bar.addLayout(title_col)
        top_bar.addStretch(1)


        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")


        self.add_btn.clicked.connect(self.add_item)
        self.edit_btn.clicked.connect(self.edit_item)
        self.delete_btn.clicked.connect(self.delete_item)


        # Make buttons compress better by setting size policies
        self.add_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.edit_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.delete_btn.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))


        top_bar.addWidget(self.add_btn)
        top_bar.addWidget(self.edit_btn)
        top_bar.addWidget(self.delete_btn)


        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.copy_item)


        bottom_bar = QHBoxLayout()
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.clicked.connect(self.copy_item)
        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #8b9bb4;")


        bottom_bar.addWidget(self.copy_btn)
        bottom_bar.addStretch(1)
        bottom_bar.addWidget(self.status)


        main.addLayout(top_bar)
        main.addWidget(self.list_widget)
        main.addLayout(bottom_bar)
        central.setLayout(main)


    def _load_items(self):
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception:
                self.items = []


    def _save_items(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=2, ensure_ascii=False)


    def refresh_list(self):
        self.list_widget.clear()
        for item in self.items:
            row = QListWidgetItem(item["name"])
            row.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(row)
        self.status.setText(f"{len(self.items)} item(s)")


    def selected_item(self):
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None


    def add_item(self):
        editor = ItemEditor(self)
        editor.exec() if hasattr(editor, 'exec') else editor.show()
        
        # Use a simpler approach: show modal-like behavior
        editor.show()
        editor.raise_()
        editor.activateWindow()
        
        # Wait for the editor to be closed and check results
        import time
        while editor.isVisible():
            QApplication.processEvents()
            time.sleep(0.05)
        
        if editor.result_name is not None:
            self.items.append({
                "name": editor.result_name,
                "content": editor.result_content
            })
            self._save_items()
            self.refresh_list()
            self.status.setText(f"Added {editor.result_name}")


    def edit_item(self):
        current = self.selected_item()
        if not current:
            QMessageBox.information(self, "Edit Item", "Select an item first.")
            return


        editor = ItemEditor(self, current["name"], current["content"])
        editor.show()
        editor.raise_()
        editor.activateWindow()
        
        # Wait for the editor to be closed and check results
        import time
        while editor.isVisible():
            QApplication.processEvents()
            time.sleep(0.05)
        
        if editor.result_name is not None:
            index = next((i for i, x in enumerate(self.items) if x["name"] == current["name"] and x["content"] == current["content"]), None)
            if index is not None:
                self.items[index] = {
                    "name": editor.result_name,
                    "content": editor.result_content
                }
                self._save_items()
                self.refresh_list()
                self.status.setText(f"Edited {editor.result_name}")


    def delete_item(self):
        current = self.selected_item()
        if not current:
            QMessageBox.information(self, "Delete Item", "Select an item first.")
            return


        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete '{current['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.items = [x for x in self.items if not (x["name"] == current["name"] and x["content"] == current["content"])]
            self._save_items()
            self.refresh_list()
            self.status.setText(f"Deleted {current['name']}")


    def copy_item(self):
        current = self.selected_item()
        if not current:
            QMessageBox.information(self, "Copy Item", "Select an item first.")
            return


        QApplication.clipboard().setText(current["content"])
        self.last_copied_name = current["name"]
        self.last_label.setText(f"Last copied: {current['name']}")
        self.status.setText(f"Copied {current['name']}")


    def closeEvent(self, event: QCloseEvent):
        self.hide()
        event.ignore()



class SullybaseClipboardApp(rumps.App):
    def __init__(self):
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.window = ClipboardWindow()
        self.window.hide()

        # Get the path to icon.png in the same directory as this script
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")

        super().__init__("SullybaseClipboard", icon=icon_path, quit_button=None)
        self.menu = ["Open Sullybase Clipboard", "Quit"]


    @rumps.clicked("Open Sullybase Clipboard")
    def open_window(self, _):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()


    @rumps.clicked("Quit")
    def quit_app(self, _):
        self.window._save_items()
        rumps.quit_application()



if __name__ == "__main__":
    app = SullybaseClipboardApp()
    app.run()
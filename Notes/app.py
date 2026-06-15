import rumps
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QFileDialog, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QAction, QCloseEvent, QFont
from PyQt6.QtCore import Qt

class NotesWindow(QMainWindow):
    def __init__(self, notes_app):
        super().__init__()
        self.notes_app = notes_app
        self.setWindowTitle("SullybaseNotes")
        self.setGeometry(100, 100, 650, 450)
        
        # Apply dark blue professional theme to window
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
        """)
        
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
            }
        """)
        self.setCentralWidget(central_widget)
        
        # Top bar with word/char count on left and buttons on right
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(20, 15, 20, 15)
        top_bar.setSpacing(10)
        
        # Word and character count (left side) - Professional minimalistic style
        self.count_label = QLabel("Words: 0 | Characters: 0")
        count_font = QFont()
        count_font.setPointSize(11)
        count_font.setWeight(QFont.Weight.Light)
        self.count_label.setFont(count_font)
        self.count_label.setStyleSheet("""
            QLabel {
                color: #8b9bb4;
                padding: 8px 16px;
                font-weight: 300;
            }
        """)
        top_bar.addWidget(self.count_label)
        
        # Add spacer to push buttons to the right
        spacer = QWidget()
        spacer.setStyleSheet("width: 0px;")
        top_bar.addWidget(spacer)
        
        # Note switch buttons (right side) - Professional minimalistic blue dark mode
        button_font = QFont()
        button_font.setPointSize(10)
        button_font.setWeight(QFont.Weight.Medium)
        
        self.note1_button = QPushButton("Note 1")
        self.note1_button.setFont(button_font)
        self.note1_button.setFixedSize(90, 32)
        self.note1_button.clicked.connect(self.switch_to_note1)
        self.note1_button.setStyleSheet("""
            QPushButton {
                background-color: #16213e;
                color: #8b9bb4;
                border: 1px solid #0f3460;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1f4068;
                border: 1px solid #1f4068;
            }
        """)
        top_bar.addWidget(self.note1_button)
        
        self.note2_button = QPushButton("Note 2")
        self.note2_button.setFont(button_font)
        self.note2_button.setFixedSize(90, 32)
        self.note2_button.clicked.connect(self.switch_to_note2)
        self.note2_button.setStyleSheet("""
            QPushButton {
                background-color: #16213e;
                color: #8b9bb4;
                border: 1px solid #0f3460;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1f4068;
                border: 1px solid #1f4068;
            }
        """)
        top_bar.addWidget(self.note2_button)
        
        # Main text edit - Professional dark blue theme
        self.text_edit = QTextEdit()
        text_font = QFont()
        text_font.setPointSize(14)
        text_font.setWeight(QFont.Weight.Light)
        self.text_edit.setFont(text_font)
        self.text_edit.textChanged.connect(self.update_count)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0f0f1a;
                color: #e8e8f0;
                border: 1px solid #16213e;
                border-radius: 8px;
                padding: 18px;
                font-weight: 300;
            }
            QTextEdit:focus {
                border: 1px solid #1f4068;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_bar)
        main_layout.addWidget(self.text_edit)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)
        
        # Load both notes
        self.load_all_notes()
        self.current_note = 1
        self.update_display()
    
    def load_all_notes(self):
        """Load both notes from files"""
        self.note1_text = self.load_note(1)
        self.note2_text = self.load_note(2)
    
    def load_note(self, note_num):
        """Load a specific note"""
        path = self.get_note_path(note_num)
        try:
            with open(path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            return ""
    
    def save_note(self, note_num, text):
        """Save a specific note"""
        path = self.get_note_path(note_num)
        with open(path, 'w') as file:
            file.write(text)
    
    def get_note_path(self, note_num):
        """Get path for a specific note"""
        support_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "SullybaseNotes")
        os.makedirs(support_dir, exist_ok=True)
        return os.path.join(support_dir, f"notes_{note_num}.txt")
    
    def update_display(self):
        """Update display based on current note"""
        if self.current_note == 1:
            self.text_edit.setPlainText(self.note1_text)
            self.note1_button.setStyleSheet("""
                QPushButton {
                    background-color: #1f4068;
                    color: #e8e8f0;
                    border: 1px solid #1f4068;
                    border-radius: 6px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2a5298;
                    border: 1px solid #2a5298;
                }
            """)
            self.note2_button.setStyleSheet("""
                QPushButton {
                    background-color: #16213e;
                    color: #8b9bb4;
                    border: 1px solid #0f3460;
                    border-radius: 6px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #1f4068;
                    border: 1px solid #1f4068;
                }
            """)
        else:
            self.text_edit.setPlainText(self.note2_text)
            self.note1_button.setStyleSheet("""
                QPushButton {
                    background-color: #16213e;
                    color: #8b9bb4;
                    border: 1px solid #0f3460;
                    border-radius: 6px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #1f4068;
                    border: 1px solid #1f4068;
                }
            """)
            self.note2_button.setStyleSheet("""
                QPushButton {
                    background-color: #1f4068;
                    color: #e8e8f0;
                    border: 1px solid #1f4068;
                    border-radius: 6px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2a5298;
                    border: 1px solid #2a5298;
                }
            """)
        self.update_count()
    
    def switch_to_note1(self):
        """Switch to note 1"""
        # Save current note before switching
        if self.current_note == 1:
            self.note1_text = self.text_edit.toPlainText()
        else:
            self.note2_text = self.text_edit.toPlainText()
            self.save_note(2, self.note2_text)
        
        self.current_note = 1
        self.update_display()
    
    def switch_to_note2(self):
        """Switch to note 2"""
        # Save current note before switching
        if self.current_note == 1:
            self.note1_text = self.text_edit.toPlainText()
            self.save_note(1, self.note1_text)
        else:
            self.note2_text = self.text_edit.toPlainText()
        
        self.current_note = 2
        self.update_display()
    
    def update_count(self):
        """Update word and character count"""
        text = self.text_edit.toPlainText()
        char_count = len(text)
        words = text.split()
        word_count = len(words)
        self.count_label.setText(f"Words: {word_count} | Characters: {char_count}")
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", 
                                                    "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'r') as file:
                self.text_edit.setPlainText(file.read())
    
    def save_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", 
                                                      "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, 'w') as file:
                file.write(self.text_edit.toPlainText())
    
    def save_notes(self):
        """Save current note"""
        text = self.text_edit.toPlainText()
        if self.current_note == 1:
            self.note1_text = text
            self.save_note(1, text)
        else:
            self.note2_text = text
            self.save_note(2, text)
    
    def closeEvent(self, a0: QCloseEvent):
        self.save_notes()
        self.hide()
        a0.accept()

class NotesApp(rumps.App):
    def __init__(self):
        self.pyqt_app = QApplication(sys.argv)
        self.notes_window = NotesWindow(self)
        self.notes_window.hide()
        
        super().__init__("NotesApp", icon="icon.png")
        
        # Add menu item to open notepad - rumps uses menu attribute
        self.menu = ["Open Notepad"]
    
    @rumps.clicked("Open Notepad")
    def open_notes(self, _):
        self.notes_window.show()
        self.notes_window.save_notes()

if __name__ == "__main__":
    NotesApp().run()

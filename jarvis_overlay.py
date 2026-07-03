import sys
import os
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView

class StateUpdater(QObject):
    update_signal = pyqtSignal(str)

def listen_for_commands(updater):
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            state = line.strip().lower()
            if state.startswith('custom:') or state in ['idle', 'listening', 'speaking', 'waiting']:
                updater.update_signal.emit(state)
        except:
            break

class JarvisOverlay(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # The pill in jarvis_ui.html is 450x80, the glow spans 600x600.
        # We need a window large enough to show the pill and its glow without clipping.
        win_width = 600
        win_height = 150
        
        screen = QApplication.primaryScreen().geometry()
        self.x_center = (screen.width() - win_width) // 2
        
        self.setGeometry(self.x_center, 10, win_width, win_height)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = QWebEngineView(self)
        self.view.page().setBackgroundColor(Qt.transparent)
        
        ui_path = os.path.abspath("jarvis_ui.html")
        self.view.load(QUrl.fromLocalFile(ui_path))
        
        self.layout.addWidget(self.view)
        
        self.updater = StateUpdater()
        self.updater.update_signal.connect(self.set_state)
        threading.Thread(target=listen_for_commands, args=(self.updater,), daemon=True).start()

    def set_state(self, state):
        # Escape single quotes just in case
        safe_state = state.replace("'", "\\'")
        self.view.page().runJavaScript(f"setState('{safe_state}')")

def main():
    app = QApplication(sys.argv)
    overlay = JarvisOverlay()
    overlay.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

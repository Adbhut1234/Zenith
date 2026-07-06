import sys
import os
import threading

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QColor


class StateUpdater(QObject):
    update_signal = pyqtSignal(str)


def listen_for_commands(updater):
    """Read state commands from stdin (sent by agent.py via subprocess)."""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            updater.update_signal.emit(line.strip())
        except Exception:
            break


class JarvisOverlay(QWidget):
    def __init__(self):
        super().__init__()

        # Frameless + always on top + transparent
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        # Size the window to fit the pill + its ambient glow.
        # The pill is 488px wide x 70px tall; the glow adds ~60px below.
        # 640 x 160 gives comfortable room around the pill.
        WIN_W, WIN_H = 640, 160
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width()  - WIN_W) // 2
        y = 5     # flush near top of screen
        self.setGeometry(x, y, WIN_W, WIN_H)

        # QWebEngineView fills the whole window
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = QWebEngineView(self)
        self.view.setAttribute(Qt.WA_TranslucentBackground)
        self.view.setAttribute(Qt.WA_NoSystemBackground)
        self.view.page().setBackgroundColor(QColor(Qt.transparent))

        html_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'jarvis_ui.html'
        )
        self.view.load(QUrl.fromLocalFile(html_path))
        self.view.loadFinished.connect(self._on_load)

        layout.addWidget(self.view)

        # Stdin command listener (agent.py pipes state strings here)
        self.updater = StateUpdater()
        self.updater.update_signal.connect(self.set_state)
        threading.Thread(
            target=listen_for_commands,
            args=(self.updater,),
            daemon=True
        ).start()

    def _on_load(self, ok):
        """Brief startup animation so user can confirm the overlay is alive."""
        if ok:
            QTimer.singleShot(300,  lambda: self.set_state('listening'))
            QTimer.singleShot(3500, lambda: self.set_state('idle'))

    def set_state(self, state):
        """
        Map agent state strings to JS setState() calls.
        Handles: idle, listening, speaking, waiting, thinking, tool, custom:<text>
        """
        safe = state.replace("'", "\\'").replace('"', '\\"')
        self.view.page().runJavaScript(f"setState('{safe}')")


def main():
    app = QApplication(sys.argv)
    overlay = JarvisOverlay()
    overlay.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

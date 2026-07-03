import sys
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QObject, pyqtSignal, QEasingCurve, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QBrush

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

        self.pill_width = 380
        self.pill_height = 65
        
        win_width = self.pill_width + 80
        win_height = self.pill_height + 80
        
        screen = QApplication.primaryScreen().geometry()
        self.x_center = (screen.width() - win_width) // 2
        
        self.y_hidden = -win_height - 10
        self.y_visible = 30
        
        self.setGeometry(self.x_center, self.y_hidden, win_width, win_height)
        
        self.layout = QVBoxLayout(self)
        self.label = QLabel("", self)
        self.label.setAlignment(Qt.AlignCenter)
        
        # Professional font styling
        font = QFont("Segoe UI", 15, QFont.Medium)
        self.label.setFont(font)
        self.label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.9);
            letter-spacing: 1px;
            margin-top: 2px;
        """)
        
        # Soft text shadow for readability
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 2)
        self.label.setGraphicsEffect(shadow)
        
        self.layout.addWidget(self.label)
        
        self.current_state = 'idle'
        
        # Apple-style smooth bounce animation
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(700)
        self.animation.setEasingCurve(QEasingCurve.OutElastic)

        # Gradient animation offset
        self.gradient_offset = 0.0
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(20) # 50fps smooth
        
        self.updater = StateUpdater()
        self.updater.update_signal.connect(self.set_state)
        threading.Thread(target=listen_for_commands, args=(self.updater,), daemon=True).start()

        QTimer.singleShot(100, lambda: self.set_state('listening'))
        QTimer.singleShot(3500, lambda: self.set_state('idle'))

    def update_animation(self):
        speed = 0.05 if self.current_state == 'speaking' else 0.02
        self.gradient_offset = (self.gradient_offset + speed) % 2.0
        if self.current_state != 'idle':
            self.update()

    def paintEvent(self, event):
        if self.current_state == 'idle' and self.y() < 0:
            return 

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Margin for the glow
        pill_rect = QRect(40, 40, self.pill_width, self.pill_height)
        
        # 1. Draw outer soft glow
        if self.current_state in ['listening', 'speaking', 'waiting']:
            glow_rect = pill_rect.adjusted(-6, -6, 6, 6)
            glow_gradient = QLinearGradient(glow_rect.topLeft(), glow_rect.bottomRight())
            
            # Shifting colors
            offset = self.gradient_offset
            
            if self.current_state == 'listening':
                c1, c2, c3 = QColor(10, 132, 255, 120), QColor(94, 92, 230, 120), QColor(255, 55, 95, 120)
            elif self.current_state == 'speaking':
                # Purple/Pink for speaking
                c1, c2, c3 = QColor(191, 90, 242, 160), QColor(255, 55, 95, 160), QColor(255, 149, 0, 160)
            else:
                # Dim resting state for waiting
                c1, c2, c3 = QColor(255, 255, 255, 30), QColor(100, 100, 100, 30), QColor(255, 255, 255, 30)

            # Creating a shifting liquid wave effect
            glow_gradient.setColorAt(abs(math.sin(offset)), c1)
            glow_gradient.setColorAt(abs(math.cos(offset)), c2)
            glow_gradient.setColorAt(abs(math.sin(offset + 1)), c3)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow_gradient))
            painter.drawRoundedRect(glow_rect, self.pill_height // 2 + 6, self.pill_height // 2 + 6)
            
            # Second layer of glow for softer falloff
            glow_rect2 = pill_rect.adjusted(-2, -2, 2, 2)
            painter.setBrush(QBrush(glow_gradient))
            painter.drawRoundedRect(glow_rect2, self.pill_height // 2 + 2, self.pill_height // 2 + 2)

        # 2. Draw the sleek dark glass pill
        painter.setBrush(QColor(22, 22, 24, 230))
        
        # Subtle white top-border for 3D glass lighting
        painter.setPen(QPen(QColor(255, 255, 255, 35), 1.5))
        painter.drawRoundedRect(pill_rect, self.pill_height // 2, self.pill_height // 2)

    def set_state(self, state):
        
        if state.startswith('custom:'):
            self.current_state = 'speaking'
            self.label.setText(state[7:])
            self.animation.setEndValue(self.pos().__class__(self.x_center, self.y_visible))
            self.animation.setEasingCurve(QEasingCurve.OutElastic)
            self.animation.start()
            self.update()
            return
            
        self.current_state = state
        
        if state == 'idle':
            self.label.setText("")
            self.animation.setEndValue(self.pos().__class__(self.x_center, self.y_hidden))
            self.animation.setEasingCurve(QEasingCurve.InBack)
            self.animation.start()
            
        elif state == 'listening':
            self.label.setText("Jarvis is listening...")
            self.animation.setEndValue(self.pos().__class__(self.x_center, self.y_visible))
            self.animation.setEasingCurve(QEasingCurve.OutElastic)
            self.animation.start()
            
        elif state == 'speaking':
            self.label.setText("Processing...")
            self.animation.setEndValue(self.pos().__class__(self.x_center, self.y_visible))
            self.animation.setEasingCurve(QEasingCurve.OutElastic)
            self.animation.start()
            
        elif state == 'waiting':
            self.label.setText("Waiting for command...")
            self.animation.setEndValue(self.pos().__class__(self.x_center, self.y_visible))
            self.animation.setEasingCurve(QEasingCurve.OutElastic)
            self.animation.start()
            
        self.update()

import math
def main():
    app = QApplication(sys.argv)
    overlay = JarvisOverlay()
    overlay.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

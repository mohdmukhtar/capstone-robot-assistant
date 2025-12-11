# task_dashboard.py

import sys
import queue
import datetime
import pygame 

# Use the non-blocking Pygame class
from pygamefacetest import RobotFace

# PyQt Imports
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
from PyQt5.QtCore import (
    Qt, QSize, QDateTime, QPropertyAnimation, QEasingCurve, QTimer, 
    QSequentialAnimationGroup, QParallelAnimationGroup
)
from PyQt5.QtGui import QFont

# --- CONFIGURATION & MOCK DATA ---
CUSTOM_FONT_NAME = "Consolas" 
MAX_TASKS_TO_DISPLAY = 4 

MOCK_RESPONSE_DATA = {
    "intent": "LIST_TASKS",
    "user": "Mohamed",
    "conversational_speech": "Hey Mohamed! Your task queue is looking sharp. Let's tackle these priorities together.",
    "structured_text_output": {
        "user_tasks": [
            {"id": 1, "description": "Finalize the robot chassis design and send files to 3D printing", "due_date": "2025-12-09", "status": "COMPLETED"},
            {"id": 2, "description": "Review the PyQT GUI test script and prepare for multi-threading integration", "due_date": "2025-12-20", "status": "PENDING"},
            {"id": 3, "description": "Order the standard parts for the robot assembly", "due_date": "2025-12-25", "status": "PENDING"},
            {"id": 4, "description": "Meet with group to review the capstone project winter semester plans", "due_date": "2026-01-05", "status": "PENDING"},
        ]
    }
}
INITIAL_PHRASE = "Hello. My expressive face display is now active. I am Mico."


# --- 1. PYGAME INTEGRATION WIDGET (Face View) ---

class PygameFaceWidget(QtWidgets.QWidget):
    frame_ready = QtCore.pyqtSignal(QtGui.QImage)
    speech_finished = QtCore.pyqtSignal() 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(False)
        self.robot_face = RobotFace(self.width(), self.height()) 
        
        self.robot_face.speech_done_callback = self.speech_done_callback 
        
        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setGeometry(0, 0, self.width(), self.height())
        self.frame_ready.connect(self.update_image)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33) # ~30 FPS

        self.speech_queue = queue.Queue()
        self.speech_timer = QtCore.QTimer(self)
        self.speech_timer.timeout.connect(self.check_speech_queue)
        self.speech_timer.start(100)
        
    def stop_rendering(self):
        """Stops the internal QTimer that drives Pygame rendering."""
        if self.timer.isActive():
            self.timer.stop()
            print("DEBUG: Pygame rendering QTimer stopped.")
        if self.speech_timer.isActive():
            self.speech_timer.stop()
            print("DEBUG: Speech queue QTimer stopped.")

    def speech_done_callback(self):
        """Called by RobotFace via property, emits the PyQt signal."""
        print("DEBUG: PygameFaceWidget received speech_done_callback. Emitting signal.")
        self.speech_finished.emit()

    def resizeEvent(self, event):
        new_width = self.width()
        new_height = self.height()
        
        self.image_label.setGeometry(0, 0, new_width, new_height)
        self.robot_face = RobotFace(new_width, new_height) 
        self.robot_face.speech_done_callback = self.speech_done_callback 
        
        super().resizeEvent(event)

    @QtCore.pyqtSlot(QtGui.QImage)
    def update_image(self, image):
        self.image_label.setPixmap(QtGui.QPixmap.fromImage(image).scaled(
            self.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        
    def update_frame(self):
        self.robot_face.update_logic()
        pygame_surface = self.robot_face.draw()

        raw_data = pygame.image.tobytes(pygame_surface, 'RGBA') 
        
        qimage = QtGui.QImage(raw_data, 
                              self.width(), 
                              self.height(), 
                              self.width() * 4, 
                              QtGui.QImage.Format_RGBX8888) 
                               
        qimage = qimage.rgbSwapped()
        
        self.frame_ready.emit(qimage)

    def check_speech_queue(self):
        try:
            text = self.speech_queue.get_nowait()
            self.robot_face.start_speech(text)
        except queue.Empty:
            pass
            
    def enqueue_speech(self, text):
        self.speech_queue.put(text)


# --- 2. TASK DASHBOARD WIDGET (Task View) ---

class TaskViewWidget(QtWidgets.QWidget):
    def __init__(self, data, custom_font_name, parent=None):
        super().__init__(parent)
        self.data = data
        
        self.HEADER_FONT = QFont(custom_font_name, 32); self.HEADER_FONT.setWeight(QFont.ExtraBold)
        self.TASK_FONT = QFont(custom_font_name, 14); self.TASK_FONT.setWeight(QFont.DemiBold) 
        self.INFO_FONT = QFont(custom_font_name, 14)

        self.setStyleSheet("""
            QWidget { background-color: #0d1117; }
            QLabel { color: #E0E0E0; }
            #HeaderLabel { 
                color: #58A6FF;
                border-bottom: 2px solid #30363d;
                padding-bottom: 5px; 
            }
            #TaskCard {
                border-radius: 8px;
            }
        """)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(60, 25, 60, 25) 
        self.main_layout.setSpacing(10)
        
        self.widgets_to_animate = {}
        self.task_cards = []
        self.due_date_labels = [] 
        
        self.display_task_list()

    def _create_task_card(self, task):
        task_card = QtWidgets.QWidget()
        task_card_layout = QtWidgets.QVBoxLayout(task_card)
        task_card_layout.setContentsMargins(10, 10, 10, 10) 
        task_card.setObjectName("TaskCard")
        
        status = task.get("status", "UNKNOWN").upper()
        
        if status == "PENDING":
            card_style = "background-color: #161b22; border: 2px solid #FFD700;"
            status_icon = "▶️"
            status_color = "#FFD700"
        elif status == "COMPLETED":
            card_style = "background-color: #1F301F; border: 2px solid #00FF00;"
            status_icon = "✅"
            status_color = "#00FF00"
        else:
            card_style = "background-color: #161b22; border: 2px solid #58A6FF;"
            status_icon = "❓"
            status_color = "#58A6FF"
            
        task_card.setStyleSheet(f"#TaskCard {{ {card_style} }}")
        
        top_row_layout = QtWidgets.QHBoxLayout()
        
        status_label = QtWidgets.QLabel(f"<span style='font-size: 18px; font-weight: bold; color: {status_color};'>{status_icon} {status}</span>")
        status_label.setFont(self.INFO_FONT)
        top_row_layout.addWidget(status_label)
        
        due_date_label = QtWidgets.QLabel(f"Due Date: {task['due_date']}")
        due_date_label.setFont(self.INFO_FONT)
        due_date_label.setObjectName("DueDateText") 
        due_date_label.setStyleSheet("color: transparent;") 
        
        self.due_date_labels.append(due_date_label) 
        
        top_row_layout.addStretch(1)
        top_row_layout.addWidget(due_date_label)
        
        task_card_layout.addLayout(top_row_layout)
        
        description_label = QtWidgets.QLabel(task['description'])
        description_label.setFont(self.TASK_FONT) 
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #FFFFFF; margin-top: 5px;")
        
        task_card_layout.addWidget(description_label)
        
        task_card._target_height = task_card.sizeHint().height()

        return task_card

    def display_task_list(self):
        self.widgets_to_animate = {}
        self.task_cards = []
        self.due_date_labels = []

        greeting_text = self.data.get("conversational_speech", "Hello! Here is the latest update.")
        greeting_label = QtWidgets.QLabel("") 
        greeting_label.setFont(self.INFO_FONT) 
        greeting_label.setStyleSheet("color: #777777;")
        self.main_layout.addWidget(greeting_label)
        
        header_text = f"{self.data.get('user', 'MOHAMED')}'S TASK DASHBOARD"
        header_label = QtWidgets.QLabel("") 
        header_label.setObjectName("HeaderLabel") 
        header_label.setFont(self.HEADER_FONT) 
        header_label.setAlignment(Qt.AlignCenter)
        
        self.main_layout.addWidget(header_label)
        self.main_layout.addSpacing(20)
        
        self.widgets_to_animate['header'] = {'widget': header_label, 'text': header_text}
        self.widgets_to_animate['greeting'] = {'widget': greeting_label, 'text': greeting_text}

        task_container = QtWidgets.QWidget()
        task_layout = QtWidgets.QVBoxLayout(task_container)
        task_layout.setSpacing(15)
        task_layout.setContentsMargins(0, 0, 0, 0)
        
        all_tasks = self.data.get("structured_text_output", {}).get("user_tasks", [])
        
        def sort_key(task):
            try:
                status_priority = 1 if task['status'].upper() == 'PENDING' else 2
                date_obj = datetime.datetime.strptime(task['due_date'], '%Y-%m-%d')
                return (status_priority, date_obj)
            except:
                return (status_priority, datetime.datetime.max) 

        sorted_tasks = sorted(all_tasks, key=sort_key)
        tasks_to_display = sorted_tasks[:MAX_TASKS_TO_DISPLAY]

        for task in tasks_to_display:
            task_card = self._create_task_card(task) 
            task_layout.addWidget(task_card)
            
            task_card.setVisible(False) 
            self.task_cards.append(task_card) 

        self.main_layout.addStretch(1) 
        self.main_layout.addWidget(task_container)
        self.main_layout.addStretch(1)

        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd | hh:mm:ss AP")
        footer_label = QtWidgets.QLabel(f"Mico System Status | {current_time}")
        footer_label.setAlignment(Qt.AlignRight)
        footer_label.setFont(self.INFO_FONT)
        footer_label.setStyleSheet("color: #30363d;")
        
        opacity_effect = QtWidgets.QGraphicsOpacityEffect(footer_label)
        opacity_effect.setOpacity(0.0) 
        footer_label.setGraphicsEffect(opacity_effect)
        
        self.main_layout.addWidget(footer_label)
        self.widgets_to_animate['footer'] = footer_label

    def start_dashboard_animation(self):
        """Orchestrates the animation sequence (typing, slide-in, wipe, fade-in)."""
        TYPING_DURATION = 1050
        TASK_STEP_DURATION = 450
        DUE_DATE_DURATION = 500
        FADE_DURATION = 1500
        
        # PHASE 1: PARALLEL TYPING
        parallel_typing_group = QParallelAnimationGroup()
        for key in ['header', 'greeting']:
            data = self.widgets_to_animate[key]
            anim = self._create_typing_animation(data['widget'], data['text'], TYPING_DURATION)
            parallel_typing_group.addAnimation(anim)
        
        # PHASE 2: SEQUENTIAL DOWNWARD SLIDE/FADE
        task_slide_sequence = QSequentialAnimationGroup()
        for card in self.task_cards:
            card.show()
            slide_anim = self._create_fall_in_animation(card, TASK_STEP_DURATION)
            task_slide_sequence.addAnimation(slide_anim)
            
        # PHASE 3: DUE DATE WIPE
        due_date_wipe_group = QParallelAnimationGroup()
        for label in self.due_date_labels:
            wipe_anim = self._create_wipe_animation(label, DUE_DATE_DURATION)
            due_date_wipe_group.addAnimation(wipe_anim)

        # PHASE 4: MAIN ORCHESTRATOR
        self.orchestrator = QSequentialAnimationGroup()
        self.orchestrator.addAnimation(parallel_typing_group)
        self.orchestrator.addPause(200) 
        self.orchestrator.addAnimation(task_slide_sequence)
        self.orchestrator.addPause(200) 
        self.orchestrator.addAnimation(due_date_wipe_group)

        # Footer Fade
        footer_fade_anim = QPropertyAnimation(self.widgets_to_animate['footer'].graphicsEffect(), b"opacity")
        footer_fade_anim.setDuration(FADE_DURATION)
        footer_fade_anim.setStartValue(0.0)
        footer_fade_anim.setEndValue(1.0)
        footer_fade_anim.setEasingCurve(QEasingCurve.InQuad)
        
        self.orchestrator.addPause(500) 
        self.orchestrator.addAnimation(footer_fade_anim)
        
        self.orchestrator.start()
        self._orchestrator = self.orchestrator 

    def _create_typing_animation(self, label, full_text, duration_ms):
        interval = int(duration_ms / len(full_text))
        typing_timer = QTimer(label)
        label._typing_timer = typing_timer
        def type_character():
            if len(label.text()) < len(full_text):
                label.setText(full_text[:len(label.text()) + 1])
            else:
                typing_timer.stop() 
        typing_timer.timeout.connect(type_character)
        typing_timer.start(interval)
        dummy_anim = QPropertyAnimation(label, b"windowOpacity")
        dummy_anim.setDuration(duration_ms)
        dummy_anim.setStartValue(1.0) 
        dummy_anim.setEndValue(1.0)   
        return dummy_anim

    def _create_fall_in_animation(self, widget, duration_ms):
        target_height = widget._target_height if hasattr(widget, '_target_height') else widget.sizeHint().height()
        widget.setMaximumHeight(0) 
        opacity_effect = QtWidgets.QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0.0)
        height_anim = QPropertyAnimation(widget, b"maximumHeight")
        height_anim.setDuration(duration_ms)
        height_anim.setStartValue(0)
        height_anim.setEndValue(target_height)
        height_anim.setEasingCurve(QEasingCurve.OutCubic)
        opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_anim.setDuration(duration_ms)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        widget_group = QParallelAnimationGroup()
        widget_group.addAnimation(height_anim)
        widget_group.addAnimation(opacity_anim)
        def reset_height_constraint():
            widget.setMaximumHeight(1000) 
            widget.setGraphicsEffect(None)    
        widget_group.finished.connect(reset_height_constraint)
        widget._fall_in_anim = widget_group
        return widget_group

    def _create_wipe_animation(self, label, duration_ms):
        wipe_anim = QPropertyAnimation(label, b"windowOpacity") 
        wipe_anim.setDuration(duration_ms)
        wipe_anim.setStartValue(1.0) 
        wipe_anim.setEndValue(1.0)
        steps = 50
        interval = duration_ms // steps
        current_step = [0] 
        wipe_timer = QTimer(label)
        label._wipe_timer = wipe_timer
        def timer_step():
            current_step[0] += 1
            reveal_threshold = steps * 0.1 
            if current_step[0] > reveal_threshold:
                color_css = "color: #58A6FF; font-weight: bold;" 
            else:
                color_css = "color: transparent;" 
            label.setStyleSheet(color_css)
            if current_step[0] >= steps:
                wipe_timer.stop()
        wipe_timer.timeout.connect(timer_step)
        wipe_timer.start(interval)
        return wipe_anim


# --- 3. MAIN ORCHESTRATOR WINDOW ---

class TaskDashboard(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mico Assistant: Expressive Face")
        # Set to Landscape 900x500
        self.setGeometry(100, 100, 900, 500) 
        
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0) 

        # --- A. STACKED WIDGET FOR VIEW SWITCHING ---
        self.stacked_widget = QtWidgets.QStackedWidget()
        
        self.face_container = QtWidgets.QWidget()
        face_layout = QtWidgets.QVBoxLayout(self.face_container)
        face_layout.setContentsMargins(0, 0, 0, 0)
        self.face_widget = PygameFaceWidget()
        face_layout.addWidget(self.face_widget)
        
        self.task_widget = TaskViewWidget(MOCK_RESPONSE_DATA, CUSTOM_FONT_NAME)
        
        self.stacked_widget.addWidget(self.face_container) 
        self.stacked_widget.addWidget(self.task_widget)    
        self.main_layout.addWidget(self.stacked_widget)
        
        self.start_initial_sequence()

    def start_speech(self):
        """Helper to start the speech after a short delay."""
        self.face_widget.enqueue_speech(INITIAL_PHRASE)

    def start_initial_sequence(self):
        """
        Phase 1: Start speech and connect the transition to the speech-finished signal.
        """
        
        # 1. Start Mico speaking after a small startup delay
        QtCore.QTimer.singleShot(500, self.start_speech)
        
        # 2. Connect the signal to the transition method. 
        self.face_widget.speech_finished.connect(self.start_task_transition)

    def start_task_transition(self):
        """Phase 2: Fade out face, switch view, and start task animations."""
        
        print("DEBUG: Transition Started - start_task_transition has been called.")
        
        # CRITICAL FIX: Stop the constant Pygame redraw timer immediately
        self.face_widget.stop_rendering()
        
        face_fade_effect = QtWidgets.QGraphicsOpacityEffect(self.face_container)
        self.face_container.setGraphicsEffect(face_fade_effect)

        fade_anim = QPropertyAnimation(face_fade_effect, b"opacity")
        fade_anim.setDuration(800)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)

        def switch_view_and_animate():
            print("DEBUG: View Switch and Dashboard Animation Start.")
            # 1. Switch the view to the task dashboard
            self.stacked_widget.setCurrentIndex(1)
            # 2. Start the task dashboard animations
            self.task_widget.start_dashboard_animation()
            # 3. Clean up the face container
            self.face_container.setGraphicsEffect(None)
            
        fade_anim.finished.connect(switch_view_and_animate)
        fade_anim.start()


# --- Execution ---
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    
    window = TaskDashboard()
    window.show()
    
    sys.exit(app.exec_())

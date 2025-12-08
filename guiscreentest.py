import sys
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QGraphicsOpacityEffect
)
from PyQt5.QtCore import (
    Qt, QSize, QDateTime, QPropertyAnimation, QEasingCurve, QTimer, 
    QSequentialAnimationGroup, QParallelAnimationGroup, QPoint
)
from PyQt5.QtGui import QFont

# --- CONFIGURATION ---
CUSTOM_FONT_NAME = "Consolas" # Stable system font
MAX_TASKS_TO_DISPLAY = 4 

# --- MOCK DATA ---
# CRITICAL FIX: Restored to the original 4 tasks with their original descriptions and dates.
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

class AssistantWindow(QMainWindow):
    def __init__(self, data, custom_font_name):
        super().__init__()
        self.data = data
        self.setWindowTitle("Mico Assistant: Task Dashboard")
        self.setFixedSize(QSize(1024, 600))
        
        # --- Font Definitions ---
        self.HEADER_FONT = QFont(custom_font_name, 32); self.HEADER_FONT.setWeight(QFont.ExtraBold)
        # MODIFICATION 2: REDUCED FONT SIZE for task boxes (17 -> 14)
        self.TASK_FONT = QFont(custom_font_name, 14); self.TASK_FONT.setWeight(QFont.DemiBold) 
        self.INFO_FONT = QFont(custom_font_name, 14)

        # --- Style Sheets ---
        self.setStyleSheet("""
            QMainWindow { background-color: #0d1117; } /* Dark Blue/Black */
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
        
        # Central Widget and Layouts
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        # REDUCED MARGINS for 0.8x effect
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(40, 25, 40, 25) # Increased margin for centering effect
        self.main_layout.setSpacing(10)
        
        self.widgets_to_animate = {}
        self.task_cards = []
        self.due_date_labels = [] 
        
        self.display_task_list()
        self.start_dashboard_animation()

    def clear_layout(self, layout):
        """Helper function to remove all widgets from a layout."""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else: 
                    self.clear_layout(item.layout())

    def _create_task_card(self, task):
        """Builds a single task widget."""
        task_card = QWidget()
        
        # REDUCED PADDING for 0.8x effect
        task_card_layout = QVBoxLayout(task_card)
        task_card_layout.setContentsMargins(10, 10, 10, 10) 
        task_card.setObjectName("TaskCard")
        
        status = task.get("status", "UNKNOWN").upper()
        
        # Styling based on status
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
        
        top_row_layout = QHBoxLayout()
        
        # Status Label 
        status_label = QLabel(f"<span style='font-size: 18px; font-weight: bold; color: {status_color};'>{status_icon} {status}</span>")
        status_label.setFont(self.INFO_FONT)
        top_row_layout.addWidget(status_label)
        
        # Due Date (Text is set to transparent initially for the wipe effect)
        due_date_label = QLabel(f"Due Date: {task['due_date']}")
        due_date_label.setFont(self.INFO_FONT)
        due_date_label.setObjectName("DueDateText") 
        due_date_label.setStyleSheet("color: transparent;") # CRITICAL: Hide text
        
        self.due_date_labels.append(due_date_label) 
        
        top_row_layout.addStretch(1)
        top_row_layout.addWidget(due_date_label)
        
        task_card_layout.addLayout(top_row_layout)
        
        # Task Description (Main content)
        description_label = QLabel(task['description'])
        description_label.setFont(self.TASK_FONT) # Uses the reduced TASK_FONT
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #FFFFFF; margin-top: 5px;")
        
        task_card_layout.addWidget(description_label)
        
        # Store the height hint before it's modified by the layout
        task_card._target_height = task_card.sizeHint().height()

        return task_card

    def display_task_list(self):
        """
        Builds the content structure and sets initial states for animation targets.
        """
        self.widgets_to_animate = {}
        self.task_cards = []
        self.due_date_labels = []

        # 2.1 Title and Greeting Area
        greeting_text = self.data.get("conversational_speech", "Hello! Here is the latest update.")
        greeting_label = QLabel("") 
        greeting_label.setFont(self.INFO_FONT) 
        greeting_label.setStyleSheet("color: #777777;")
        self.main_layout.addWidget(greeting_label)
        
        # UPDATED: Header Text 
        header_text = "MOHAMED'S TASK DASHBOARD"
        header_label = QLabel("") 
        header_label.setObjectName("HeaderLabel") 
        header_label.setFont(self.HEADER_FONT) 
        # MODIFICATION 1: CENTERED ALIGNMENT
        header_label.setAlignment(Qt.AlignCenter)
        
        self.main_layout.addWidget(header_label)
        self.main_layout.addSpacing(20)
        
        self.widgets_to_animate['header'] = {'widget': header_label, 'text': header_text}
        self.widgets_to_animate['greeting'] = {'widget': greeting_label, 'text': greeting_text}


        # 2.2 Task List Area
        task_container = QWidget()
        task_layout = QVBoxLayout(task_container)
        task_layout.setSpacing(15)
        task_layout.setContentsMargins(0, 0, 0, 0)
        
        # CRITICAL FIX: Sort tasks by due_date (Ascending: Soonest date first)
        all_tasks = self.data.get("structured_text_output", {}).get("user_tasks", [])
        
        def sort_key(task):
            try:
                # Use a combined key: Status (Completed last) then Due Date
                status_priority = 1 if task['status'].upper() == 'PENDING' else 2
                date_obj = datetime.datetime.strptime(task['due_date'], '%Y-%m-%d')
                return (status_priority, date_obj)
            except:
                return (status_priority, datetime.datetime.max) # Put unparseable dates last

        # Sort the tasks
        sorted_tasks = sorted(all_tasks, key=sort_key)
        
        # Truncate to display limit
        tasks_to_display = sorted_tasks[:MAX_TASKS_TO_DISPLAY]

        for task in tasks_to_display:
            task_card = self._create_task_card(task) 
            task_layout.addWidget(task_card)
            
            task_card.setVisible(False) 
            self.task_cards.append(task_card) 

        self.main_layout.addStretch(1) 
        self.main_layout.addWidget(task_container)
        self.main_layout.addStretch(1)

        # 2.3 Footer 
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd | hh:mm:ss AP")
        footer_label = QLabel(f"Mico System Status | {current_time}")
        footer_label.setAlignment(Qt.AlignRight)
        footer_label.setFont(self.INFO_FONT)
        footer_label.setStyleSheet("color: #30363d;")
        
        opacity_effect = QGraphicsOpacityEffect(footer_label)
        opacity_effect.setOpacity(0.0) 
        footer_label.setGraphicsEffect(opacity_effect)
        
        self.main_layout.addWidget(footer_label)
        self.widgets_to_animate['footer'] = footer_label

    # --- MAIN ORCHESTRATION (No Changes) ---

    def start_dashboard_animation(self):
        """
        Orchestrates the animation sequence.
        """
        TYPING_DURATION = 1050
        TASK_STEP_DURATION = 450
        DUE_DATE_DURATION = 500
        FADE_DURATION = 1500
        
        # --- PHASE 1: PARALLEL TYPING ---
        parallel_typing_group = QParallelAnimationGroup()
        h_data = self.widgets_to_animate['header']
        h_anim = self._create_typing_animation(h_data['widget'], h_data['text'], TYPING_DURATION)
        parallel_typing_group.addAnimation(h_anim)
        g_data = self.widgets_to_animate['greeting']
        g_anim = self._create_typing_animation(g_data['widget'], g_data['text'], TYPING_DURATION)
        parallel_typing_group.addAnimation(g_anim)
        
        # --- PHASE 2: SEQUENTIAL DOWNWARD SLIDE/FADE ---
        task_slide_sequence = QSequentialAnimationGroup()
        for card in self.task_cards:
            card.show()
            slide_anim = self._create_fall_in_animation(card, TASK_STEP_DURATION)
            task_slide_sequence.addAnimation(slide_anim)
            
        # --- PHASE 3: DUE DATE WIPE ---
        due_date_wipe_group = QParallelAnimationGroup()
        for label in self.due_date_labels:
            wipe_anim = self._create_wipe_animation(label, DUE_DATE_DURATION)
            due_date_wipe_group.addAnimation(wipe_anim)


        # --- PHASE 4: MAIN ORCHESTRATOR ---
        self.orchestrator = QSequentialAnimationGroup()
        self.orchestrator.addAnimation(parallel_typing_group)
        
        self.orchestrator.addPause(200) 
        self.orchestrator.addAnimation(task_slide_sequence)
        
        self.orchestrator.addPause(200) 
        self.orchestrator.addAnimation(due_date_wipe_group)

        footer_fade_anim = QPropertyAnimation(self.widgets_to_animate['footer'].graphicsEffect(), b"opacity")
        footer_fade_anim.setDuration(FADE_DURATION)
        footer_fade_anim.setStartValue(0.0)
        footer_fade_anim.setEndValue(1.0)
        footer_fade_anim.setEasingCurve(QEasingCurve.InQuad)
        
        self.orchestrator.addPause(500) 
        self.orchestrator.addAnimation(footer_fade_anim)
        
        self.orchestrator.start()
        self._orchestrator = self.orchestrator 


    # --- ANIMATION CREATION HELPERS (No Changes) ---

    def _create_typing_animation(self, label, full_text, duration_ms):
        """Animates text appearing character by character using QTimer."""
        
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

        # Dummy animation 
        dummy_anim = QPropertyAnimation(label, b"windowOpacity")
        dummy_anim.setDuration(duration_ms)
        dummy_anim.setStartValue(1.0) 
        dummy_anim.setEndValue(1.0)   
        return dummy_anim

    def _create_fall_in_animation(self, widget, duration_ms):
        """
        Animates a widget to "fall in" by animating its maximum height and fading in.
        This is much more stable than animating the 'pos' property in a layout.
        """
        # Store target height and set initial constraints
        target_height = widget._target_height if hasattr(widget, '_target_height') else widget.sizeHint().height()
        widget.setMaximumHeight(0) 
        
        # Opacity Effect
        opacity_effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(opacity_effect)
        opacity_effect.setOpacity(0.0)

        # 1. Height Animation (Fall-in effect)
        height_anim = QPropertyAnimation(widget, b"maximumHeight")
        height_anim.setDuration(duration_ms)
        height_anim.setStartValue(0)
        height_anim.setEndValue(target_height)
        height_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 2. Opacity Animation (Fade-in)
        opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_anim.setDuration(duration_ms)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        
        # Combine animations
        widget_group = QParallelAnimationGroup()
        widget_group.addAnimation(height_anim)
        widget_group.addAnimation(opacity_anim)
        
        # CRITICAL: After animation finishes, remove height constraint to ensure layout freedom
        def reset_height_constraint():
            widget.setMaximumHeight(1000) 
            widget.setGraphicsEffect(None)    
            
        widget_group.finished.connect(reset_height_constraint)

        widget._fall_in_anim = widget_group
        
        return widget_group


    def _create_wipe_animation(self, label, duration_ms):
        """Animates the text color of a label to reveal it (wipe effect)."""
        
        # Dummy animation to time the effect
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
                 # Snap to the final desired style (blue, bold)
                color_css = "color: #58A6FF; font-weight: bold;" 
            else:
                 # Keep text transparent
                color_css = "color: transparent;" 
                
            label.setStyleSheet(color_css)

            if current_step[0] >= steps:
                wipe_timer.stop()
                
        wipe_timer.timeout.connect(timer_step)
        wipe_timer.start(interval)
        
        return wipe_anim


# --- STANDALONE TEST EXECUTION ---
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    
    window = AssistantWindow(MOCK_RESPONSE_DATA, CUSTOM_FONT_NAME)
    window.show()
    
    sys.exit(app.exec_())
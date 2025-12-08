import sys
import random

# --- IMPORT FIX: Using aliases for guaranteed access ---
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui

# --- Configuration ---
FACE_COLOR = QtGui.QColor("#161b22") # Dark background
EYE_COLOR = QtGui.QColor("#58A6FF")  # Bright blue accent (Not used directly on pupils, but kept for context)
PUPIL_COLOR = QtGui.QColor("#4DC7FF") # Bright, saturated blue for pupils
MOUTH_COLOR = QtGui.QColor("#4DC7FF") # Matching bright blue for the mouth

class RobotFaceWidget(QtWidgets.QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QtWidgets.QGraphicsScene()
        self.setScene(self.scene)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet(f"background-color: {FACE_COLOR.name()}; border: none;")
        
        self.eye_components = {}
        self.mouth_component = None
        self.mouth_base_size = 100
        self.init_face_elements()
        
        # Timers and Animation Groups
        self.blink_timer = QtCore.QTimer(self)
        self.blink_timer.timeout.connect(self.blink_eyes)
        self.blink_timer.start(random.randint(2500, 4500)) 
        
        self.speech_timer = QtCore.QTimer(self)
        self.speech_timer.timeout.connect(self._process_speech_step)
        self.speech_index = 0
        self.speech_text = ""
        self.animation_running = False

    def init_face_elements(self):
        self.scene.setSceneRect(-400, -300, 800, 600)
        
        # INCREASED EYE SIZE FOR VISUAL IMPACT
        eye_size = 80  # Increased from 50
        
        # Left Eye Pupil 
        pupil_l = QtWidgets.QGraphicsEllipseItem(-eye_size/2, -eye_size/2, eye_size, eye_size)
        pupil_l.setBrush(QtGui.QBrush(PUPIL_COLOR))
        pupil_l.setPos(-100, -100)
        self.scene.addItem(pupil_l)

        # Right Eye Pupil
        pupil_r = QtWidgets.QGraphicsEllipseItem(-eye_size/2, -eye_size/2, eye_size, eye_size)
        pupil_r.setBrush(QtGui.QBrush(PUPIL_COLOR))
        pupil_r.setPos(100, -100)
        self.scene.addItem(pupil_r)
        
        self.eye_components = {
            'l_pupil': pupil_l,
            'r_pupil': pupil_r,
        }

        # --- Mouth (QGraphicsPathItem replacement) ---
        path = QtGui.QPainterPath()
        rect_width = self.mouth_base_size 
        rect_height = 10 # Starting height for a flat line
        path.arcTo(-rect_width / 2, -rect_height / 2, rect_width, rect_height, 0, -180) 
        
        self.mouth_component = QtWidgets.QGraphicsPathItem(path)
        self.mouth_component.setPos(0, 150)
        
        # INCREASED PEN THICKNESS FOR BOLDER LOOK
        self.mouth_component.setPen(QtGui.QPen(MOUTH_COLOR, 25)) # Increased from 15
        
        self.mouth_component._initial_rect = self.mouth_component.boundingRect()
        self.scene.addItem(self.mouth_component)
        
    def blink_eyes(self, duration_ms=200):
        """Animates a quick blink by scaling the pupils vertically using QVariantAnimation."""
        
        def create_blink_animation(item):
            anim = QtCore.QVariantAnimation()
            anim.setDuration(duration_ms)
            anim.setEasingCurve(QtCore.QEasingCurve.InQuad)
            
            anim.setStartValue(1.0)
            anim.setKeyValueAt(0.5, 0.01)
            anim.setEndValue(1.0)
            
            anim.valueChanged.connect(lambda scale_y: item.setScale(QtCore.QPointF(1.0, scale_y)))
            
            return anim

        if not self.animation_running:
            self.animation_running = True
            self.blink_timer.stop()
            
            l_anim = create_blink_animation(self.eye_components['l_pupil'])
            r_anim = create_blink_animation(self.eye_components['r_pupil'])
            
            def finished():
                self.animation_running = False
                self.blink_timer.start(random.randint(2500, 4500))
                
            l_anim.finished.connect(finished)
            l_anim.start()
            r_anim.start()

    def mouth_open_animation(self, target_height_factor, duration_ms=100):
        """
        Animates the mouth path based on speech.
        """
        if not self.mouth_component:
            return

        # Animate the pen width
        pen_anim = QtCore.QVariantAnimation()
        pen_anim.setDuration(duration_ms)
        pen_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)

        start_width = self.mouth_component.pen().width()
        # Ensure the pen is slightly thicker when open for visual emphasis
        end_width = 25 + (target_height_factor * 5) # Base 25 + factor
        
        pen_anim.setStartValue(start_width)
        pen_anim.setEndValue(end_width)
        
        def update_pen(width):
            new_pen = QtGui.QPen(MOUTH_COLOR, width)
            self.mouth_component.setPen(new_pen)
            
        pen_anim.valueChanged.connect(update_pen)
        pen_anim.start()

        # Animate the path (height change)
        def animate_mouth_path(factor):
            # Adjusted Base/Max heights to better suit the thicker line
            base_h = 10 # Flatter neutral line
            max_h = 40 # Smaller max opening (since line is thicker)
            
            new_h = base_h + (max_h - base_h) * (factor - 1.0) 
            new_h = max(base_h, new_h) 
            
            # Recreate the arc path with the new height
            new_path = QtGui.QPainterPath()
            new_path.arcTo(-self.mouth_base_size / 2, -new_h / 2, self.mouth_base_size, new_h, 0, -180)
            self.mouth_component.setPath(new_path)

        path_anim = QtCore.QVariantAnimation()
        path_anim.setDuration(duration_ms)
        path_anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)
        
        # Calculate current factor based on visual height range (10 to 40)
        current_h = self.mouth_component.boundingRect().height()
        current_factor = 1.0 + (current_h - 10.0) / (40.0 - 10.0)
        
        path_anim.setStartValue(current_factor)
        path_anim.setEndValue(target_height_factor)
        path_anim.valueChanged.connect(animate_mouth_path)
        path_anim.start()


    # --- Speech Simulation Logic (Unchanged) ---
    def start_speech_simulation(self, text):
        if self.speech_timer.isActive():
            self.speech_timer.stop()
        self.speech_text = text.upper()
        self.speech_index = 0
        self.speech_timer.start(50) 

    def _process_speech_step(self):
        if self.speech_index >= len(self.speech_text):
            self.mouth_open_animation(1.0, 300) 
            self.speech_timer.stop()
            print("\nSpeech simulation ended.")
            return

        char = self.speech_text[self.speech_index]
        
        if char in 'A E I O U':
            self.mouth_open_animation(1.7, 50) 
        elif char in 'B C D F G H J K L M N P Q R S T V W X Y Z':
            self.mouth_open_animation(1.2, 50) 
        else:
            self.mouth_open_animation(1.0, 50) 

        if random.random() < 0.005: 
             self.blink_eyes() 

        sys.stdout.write(char)
        sys.stdout.flush() 

        self.speech_index += 1


class RobotFaceWindow(QtWidgets.QMainWindow):
    def __init__(self, test_text):
        super().__init__()
        self.setWindowTitle("Mico Expressive Face Prototype")
        self.setGeometry(100, 100, 800, 600)
        
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        
        self.face_widget = RobotFaceWidget()
        self.main_layout.addWidget(self.face_widget)

        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_panel)
        
        self.test_text = test_text
        self.text_label = QtWidgets.QLabel(f"**Passage:** {self.test_text}")
        
        self.start_button = QtWidgets.QPushButton("Start Speech Simulation")
        self.start_button.clicked.connect(self.run_test_sequence)
        
        control_layout.addWidget(self.text_label)
        control_layout.addStretch(1)
        control_layout.addWidget(self.start_button)
        
        self.main_layout.addWidget(control_panel)

    def run_test_sequence(self):
        print("\n--- Starting Speech Simulation ---")
        self.face_widget.start_speech_simulation(self.test_text)
        

# --- STANDALONE TEST EXECUTION ---
if __name__ == '__main__':
    TEST_PASSAGE = "Hello Mohamed, I'm Mico. I can help you organize and prioritize your capstone tasks, oh! The design review is set for Friday."
    app = QtWidgets.QApplication(sys.argv)
    window = RobotFaceWindow(TEST_PASSAGE)
    window.show()
    sys.exit(app.exec_())
    
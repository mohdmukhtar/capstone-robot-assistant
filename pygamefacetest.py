# pygamefacetest.py

import pygame
import random
import sys
import queue

# --- Configuration (Landscape: 900 wide x 500 high) ---
WIDTH, HEIGHT = 900, 500 
DARK_BACKGROUND = (22, 27, 34)
BLUE_ACCENT = (77, 199, 255)
PUPIL_COLOR = BLUE_ACCENT
MOUTH_COLOR = BLUE_ACCENT
HEAD_OUTLINE = (50, 50, 50) 

# Proportionally scaled face elements for 900x500 (Landscape)
EYE_RADIUS = 75       
EYE_Y_POS = 200       
EYE_X_OFFSET = 120    

MOUTH_Y_POS = 350     
MOUTH_BASE_WIDTH = 250 
MOUTH_BASE_HEIGHT = 15 
MOUTH_MAX_HEIGHT = 70  
MOUTH_THICKNESS = 35   

class RobotFace:
    def __init__(self, width=WIDTH, height=HEIGHT):
        if not pygame.get_init():
            pygame.init()
            
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height), depth=32) 
        
        # State Variables
        self.EYE_OPEN = True
        self.MOUTH_HEIGHT = MOUTH_BASE_HEIGHT
        
        # Blinking variables
        self.blink_countdown = random.randint(30, 90)
        self.is_blinking_closed = False
        self.blink_duration = 5 
        self.current_blink_frame = 0

        # Speech variables
        self.speech_text = ""
        self.speech_index = 0
        self.speech_frame_delay = 3
        self.speech_frame_count = 0
        
        self.speech_done_callback = None

    def start_speech(self, text):
        """Called externally to begin speech simulation."""
        self.speech_text = text.upper()
        self.speech_index = 0
        self.speech_frame_count = 0
        print(f"\n--- Mico starts talking: {text} ---")

    def _process_speech_step(self):
        """Handles lip sync based on character being 'spoken'."""
        if self.speech_index >= len(self.speech_text):
            self.animate_mouth(MOUTH_BASE_HEIGHT)
            self.speech_text = ""
            print("Speech ended.")
            if self.speech_done_callback:
                self.speech_done_callback()
            return

        char = self.speech_text[self.speech_index]
        
        # Simple Vowel-based Lip Sync
        if char in 'A E I O U':
            target_factor = 1.7
        elif char in 'B C D F G H J K L M N P Q R S T V W X Y Z':
            target_factor = 1.2
        else:
            target_factor = 1.0

        height_range = MOUTH_MAX_HEIGHT - MOUTH_BASE_HEIGHT
        target_h = MOUTH_BASE_HEIGHT + height_range * (target_factor - 1.0)
        target_h = max(MOUTH_BASE_HEIGHT, target_h)
        
        self.animate_mouth(target_h)

        sys.stdout.write(char)
        sys.stdout.flush() 

        self.speech_index += 1

    def animate_mouth(self, target_height):
        """Sets the mouth height."""
        self.MOUTH_HEIGHT = target_height

    def _handle_blinking(self):
        """Updates the blinking state based on frame counts."""
        if self.is_blinking_closed:
            self.current_blink_frame += 1
            if self.current_blink_frame >= self.blink_duration:
                self.EYE_OPEN = True
                self.is_blinking_closed = False
                self.blink_countdown = random.randint(90, 200)
                self.current_blink_frame = 0
        
        elif self.speech_text:
            if random.random() < 0.005: 
                self.EYE_OPEN = False
                self.is_blinking_closed = True
                self.current_blink_frame = 0
        
        else:
            self.blink_countdown -= 1
            if self.blink_countdown <= 0:
                self.EYE_OPEN = False
                self.is_blinking_closed = True
                self.current_blink_frame = 0

    def update_logic(self):
        """Called by the PyQt QTimer to update state."""
        self._handle_blinking()
        
        if self.speech_text:
            self.speech_frame_count += 1
            if self.speech_frame_count >= self.speech_frame_delay:
                self._process_speech_step()
                self.speech_frame_count = 0

    def draw(self):
        """Draws the current state and returns the surface."""
        screen = self.surface
        screen.fill(DARK_BACKGROUND) 
        
        center_x = self.width // 2

        # --- Eyes ---
        if self.EYE_OPEN:
            pygame.draw.circle(screen, PUPIL_COLOR, (center_x - EYE_X_OFFSET, EYE_Y_POS), EYE_RADIUS)
            pygame.draw.circle(screen, PUPIL_COLOR, (center_x + EYE_X_OFFSET, EYE_Y_POS), EYE_RADIUS)
            
            pygame.draw.circle(screen, (255, 255, 255), (center_x - EYE_X_OFFSET + 15, EYE_Y_POS - 20), 10)
            pygame.draw.circle(screen, (255, 255, 255), (center_x + EYE_X_OFFSET + 15, EYE_Y_POS - 20), 10)
            
        else:
            half_line = EYE_RADIUS * 1.5 
            pygame.draw.line(screen, PUPIL_COLOR, (center_x - EYE_X_OFFSET - half_line, EYE_Y_POS), 
                            (center_x - EYE_X_OFFSET + half_line, EYE_Y_POS), 15)
            pygame.draw.line(screen, PUPIL_COLOR, (center_x + EYE_X_OFFSET - half_line, EYE_Y_POS), 
                            (center_x + EYE_X_OFFSET + half_line, EYE_Y_POS), 15)

        # --- Mouth ---
        current_mouth_height = self.MOUTH_HEIGHT
        
        mouth_rect_x = center_x - MOUTH_BASE_WIDTH // 2 
        mouth_rect_y = MOUTH_Y_POS - current_mouth_height // 2

        mouth_rect = pygame.Rect(mouth_rect_x, mouth_rect_y, MOUTH_BASE_WIDTH, current_mouth_height)
        
        pygame.draw.arc(screen, MOUTH_COLOR, mouth_rect, 
                        3.14159, 2 * 3.14159, MOUTH_THICKNESS)
        
        return self.surface
    
import pygame
import sys

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 400, 300
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Blinking Robot Face")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)

# Clock to control frame rate
clock = pygame.time.Clock()

# Blinking mechanism variables
EYE_OPEN = True
BLINK_EVENT = pygame.USEREVENT + 1
# Blink every 2 to 5 seconds (randomized interval set each time the event is generated)
pygame.time.set_timer(BLINK_EVENT, 3000) 

def draw_robot_face(eyes_open_state):
    """Draws the robot face based on the current eye state."""
    screen.fill(GRAY)  # Background color

    # Draw head
    pygame.draw.rect(screen, BLACK, (100, 50, 200, 200), 2)

    if eyes_open_state:
        # Draw open eyes (circles)
        pygame.draw.circle(screen, WHITE, (160, 130), 30)
        pygame.draw.circle(screen, WHITE, (240, 130), 30)
        # Pupils
        pygame.draw.circle(screen, BLACK, (160, 130), 10)
        pygame.draw.circle(screen, BLACK, (240, 130), 10)
    else:
        # Draw closed eyes (simple lines or thin rectangles)
        pygame.draw.line(screen, WHITE, (130, 130), (190, 130), 5)
        pygame.draw.line(screen, WHITE, (210, 130), (270, 130), 5)

    # Draw mouth
    pygame.draw.rect(screen, WHITE, (140, 180, 120, 30))


# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Handle the custom blink event
        if event.type == BLINK_EVENT:
            EYE_OPEN = not EYE_OPEN  # Toggle eye state
            # If eyes just closed, set a short timer to open them quickly (e.g., 200ms)
            if not EYE_OPEN:
                pygame.time.set_timer(BLINK_EVENT, 200)
            # If eyes just opened, set a longer, random timer for the next blink
            else:
                import random
                next_blink_time = random.randint(2000, 5000) # 2 to 5 seconds
                pygame.time.set_timer(BLINK_EVENT, next_blink_time)
            

    # Drawing
    draw_robot_face(EYE_OPEN)

    # Update the display (only once per loop to avoid flickering)
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(30)

# Quit Pygame
pygame.quit()
sys.exit()

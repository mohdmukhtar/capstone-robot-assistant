import cv2
import os

# Create a folder to store the data
dataset_folder = 'dataset'
if not os.path.exists(dataset_folder):
    os.makedirs(dataset_folder)

# Load the face detector
cascade_file = "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(cascade_file)

# Initialize webcam
cap = cv2.VideoCapture(1)

# --- IMPORTANT ---
# Get a unique ID for the person
# Start with 1 for the first person, 2 for the second, etc.
user_id = input('Enter user ID (e.g., 1, 2, 3...): ')
print(f"Looking for faces. Taking 30 pictures for user {user_id}...")

count = 0
while count < 30:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    for (x, y, w, h) in faces:
        # Draw rectangle
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Increment sample count
        count += 1

        # Save the captured face (in grayscale)
        # Format: dataset/User.1.1.jpg, dataset/User.1.2.jpg ...
        file_name = f"{dataset_folder}/User.{user_id}.{count}.jpg"
        cv2.imwrite(file_name, gray[y:y + h, x:x + w])

        # Show the face count on the video feed
        cv2.putText(frame, f"Samples: {count}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow('Data Gatherer', frame)

    # Wait 100ms
    if cv2.waitKey(100) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"Done. Collected {count} samples for user {user_id}.")
import cv2

# --- 1. Load the recognizer and the trainer data ---
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read('trainer.yml')  # Load our trained model

# --- 2. Load the face detector (Haar Cascade) ---
cascade_file = "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(cascade_file)

# --- 3. Create a list of names ---
# This links the ID from the trainer to a name.
# ID 1 = index 1 = 'Prasa'
# ID 2 = index 2 = 'Alice'
# IMPORTANT: Index 0 is a dummy value since our IDs start at 1
names = ['None', 'Surya', 'Patrick', 'Mohamed', 'Shaymaa', 'Khush']  # <-- CHANGE THESE to match your IDs

# --- 4. Initialize Webcam ---
cap = cv2.VideoCapture(1)
print("Starting webcam... Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )

    for (x, y, w, h) in faces:
        # --- 5. THIS IS THE RECOGNITION STEP ---
        # The recognizer.predict() function returns the ID and a "confidence" score
        id, confidence = recognizer.predict(gray[y:y + h, x:x + w])

        # --- 6. Check the confidence score ---
        # The LBPH recognizer gives a *lower* score for a *better* match.
        # A score < 50-60 is a good match. > 80-90 is a bad match.
        if confidence < 70:
            # We have a match! Get the name from our 'names' list
            display_name = names[id]
            text_color = (255, 0, 0)  # Green for a match
            confidence_text = f"{round(100 - confidence)}% Match"
        else:
            # No match
            display_name = "Unknown"
            text_color = (0, 0, 255)  # Red for unknown
            confidence_text = f"{round(100 - confidence)}% Match"

        # --- 7. Draw the rectangle and text ---
        cv2.rectangle(frame, (x, y), (x + w, y + h), text_color, 2)
        cv2.putText(frame, display_name, (x, y - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
        #cv2.putText(frame, confidence_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Display the result
    cv2.imshow('Facial Recognition', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()
print("Webcam feed closed.")
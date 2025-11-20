import cv2
import numpy as np
from PIL import Image
import os

# --- 1. Create the LBPH Face Recognizer ---
# We will use this to train
recognizer = cv2.face.LBPHFaceRecognizer_create()

# --- 2. Load the face detector ---
cascade_file = "haarcascade_frontalface_default.xml"
face_detector = cv2.CascadeClassifier(cascade_file)

# Path to your dataset
path = 'dataset'


# --- 3. Function to get images and labels ---
def getImagesAndLabels(dataset_path):
    # Get all file paths in the dataset folder
    imagePaths = [os.path.join(dataset_path, f) for f in os.listdir(dataset_path)]

    faceSamples = []
    ids = []

    for imagePath in imagePaths:
        # Open the image and convert it to grayscale
        PIL_img = Image.open(imagePath).convert('L')  # 'L' is grayscale
        img_numpy = np.array(PIL_img, 'uint8')

        # Get the User ID from the filename (e.g., "User.1.5.jpg" -> ID 1)
        # We split the filename by '.' and take the second part
        try:
            id = int(os.path.split(imagePath)[-1].split(".")[1])
        except ValueError:
            print(f"Skipping file {imagePath}, incorrect format.")
            continue

        # Detect the face in the image
        faces = face_detector.detectMultiScale(img_numpy)

        for (x, y, w, h) in faces:
            # Add the face region to our list of samples
            faceSamples.append(img_numpy[y:y + h, x:x + w])
            # Add the corresponding ID
            ids.append(id)

    return faceSamples, ids


# --- 4. Train the model ---
print("\nTraining model... This may take a moment.")
faces, ids = getImagesAndLabels(path)

# This is the line that trains the recognizer
recognizer.train(faces, np.array(ids))

# --- 5. Save the trained model ---
# It will save the file as 'trainer.yml' in your project folder
recognizer.write('trainer.yml')

print(f"\nModel trained. {len(np.unique(ids))} faces were trained. Exiting.")
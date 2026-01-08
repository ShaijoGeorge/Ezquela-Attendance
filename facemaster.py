import cv2
import os
import numpy as np
from PIL import Image

# Path to the Haar Cascade (Face Detection logic)
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

def detect_face(img_path):
    """Detects a face in an image and returns the face region."""
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    
    if len(faces) == 0:
        return None, None
    
    (x, y, w, h) = faces[0]
    return gray[y:y+w, x:x+h], (x, y, w, h)

def train_model(data_folder_path):
    """Trains the LBPH model with student images."""
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = []
    ids = []
    
    for root, dirs, files in os.walk(data_folder_path):
        for file in files:
            if file.endswith("jpg") or file.endswith("png"):
                path = os.path.join(root, file)
                folder_name = os.path.basename(root)
                try:
                    # Extract ID from folder name (e.g., 's12' -> 12)
                    label_id = int(folder_name.replace('s', ''))
                    pil_image = Image.open(path).convert("L") 
                    image_array = np.array(pil_image, "uint8")
                    
                    # Detect face again to ensure quality
                    faces_rect = face_cascade.detectMultiScale(image_array)
                    for (x, y, w, h) in faces_rect:
                        faces.append(image_array[y:y+h, x:x+w])
                        ids.append(label_id)
                except ValueError:
                    continue

    if len(faces) > 0:
        recognizer.train(faces, np.array(ids))
        recognizer.save("trainer.yml")
        return True
    return False

def predict_face(img_path):
    """Predicts which student is in the photo."""
    if not os.path.exists("trainer.yml"):
        return None, 0
        
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("trainer.yml")
    
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    
    for (x, y, w, h) in faces:
        id_, confidence = recognizer.predict(gray[y:y+h, x:x+w])
        # Lower confidence = better match. < 70 is usually good for LBPH.
        if confidence < 70: 
            return id_, confidence
            
    return None, 0
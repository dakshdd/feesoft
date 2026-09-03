import face_recognition
import cv2

# Load a sample image (replace with your own image path)
image_path = "sample.jpg"   # यहाँ अपनी image का नाम डालो
image = face_recognition.load_image_file(image_path)

# Detect all face locations
face_locations = face_recognition.face_locations(image)

print(f"Found {len(face_locations)} face(s) in this image.")

# Optional: show image with rectangles
for (top, right, bottom, left) in face_locations:
    cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)

# Convert to BGR for OpenCV display
image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
cv2.imshow("Face Detection Test", image_bgr)
cv2.waitKey(0)
cv2.destroyAllWindows()

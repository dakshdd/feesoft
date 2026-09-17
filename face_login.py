# face_login.py
import os
import cv2
import numpy as np
import face_recognition
from flask import Blueprint, request, jsonify, session
from pymongo import MongoClient
from datetime import datetime

face_bp = Blueprint("face_bp", __name__)

# MongoDB
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/"
)

client = MongoClient(MONGO_URI)
db = client["school_db"]
users = db["users"]

# Face matching tolerance
FACE_TOLERANCE = 0.50


# --------------------------------------------------
# REGISTER FACE
# --------------------------------------------------

@face_bp.route("/face/register", methods=["POST"])
def register_face():

    username = request.form.get("username", "").strip()

    if not username:
        return jsonify({
            "success": False,
            "message": "Username required"
        })

    user = users.find_one({"username": username})

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found"
        })

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return jsonify({
            "success": False,
            "message": "Camera not available"
        })

    encoding = None

    try:
        while True:

            ret, frame = camera.read()

            if not ret:
                continue

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            locations = face_recognition.face_locations(rgb)

            # Exactly one face required
            if len(locations) == 1:

                encodings = face_recognition.face_encodings(
                    rgb,
                    locations
                )

                if encodings:
                    encoding = encodings[0]
                    break

            cv2.imshow("Register Face - Press Q to Cancel", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    if encoding is None:
        return jsonify({
            "success": False,
            "message": "Face registration cancelled or no face detected"
        })

    # Save encoding in MongoDB
    users.update_one(
        {"username": username},
        {
            "$set": {
                "face_encoding": encoding.tolist(),
                "face_enabled": True,
                "face_registered_at": datetime.now()
            }
        }
    )

    return jsonify({
        "success": True,
        "message": f"Face registered successfully for {username}"
    })


# --------------------------------------------------
# FACE LOGIN
# --------------------------------------------------

@face_bp.route("/face/login", methods=["GET"])
def face_login():

    # Get all users having registered face
    registered_users = list(
        users.find(
            {
                "face_enabled": True,
                "face_encoding": {
                    "$exists": True
                }
            },
            {
                "username": 1,
                "role": 1,
                "face_encoding": 1
            }
        )
    )

    if not registered_users:
        return jsonify({
            "success": False,
            "message": "No registered faces found"
        })

    known_encodings = []
    known_users = []

    for user in registered_users:

        try:
            enc = np.array(
                user["face_encoding"],
                dtype=np.float64
            )

            if len(enc) == 128:
                known_encodings.append(enc)
                known_users.append(user)

        except Exception:
            continue

    if not known_encodings:
        return jsonify({
            "success": False,
            "message": "No valid face encodings found"
        })

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        return jsonify({
            "success": False,
            "message": "Camera not available"
        })

    matched_user = None

    try:

        while True:

            ret, frame = camera.read()

            if not ret:
                continue

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            locations = face_recognition.face_locations(rgb)

            encodings = face_recognition.face_encodings(
                rgb,
                locations
            )

            for face_encoding in encodings:

                distances = face_recognition.face_distance(
                    known_encodings,
                    face_encoding
                )

                if len(distances) == 0:
                    continue

                best_index = np.argmin(distances)
                best_distance = distances[best_index]

                if best_distance <= FACE_TOLERANCE:

                    matched_user = known_users[best_index]
                    break

            if matched_user:
                break

            cv2.imshow(
                "Face Login - Press Q to Cancel",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    if not matched_user:

        return jsonify({
            "success": False,
            "message": "Face not recognized"
        })

    username = matched_user["username"]

    # Update last login
    users.update_one(
        {"username": username},
        {
            "$set": {
                "last_login": datetime.now()
            }
        }
    )

    # Flask session
    session["user"] = username
    session["role"] = matched_user.get("role", "")

    return jsonify({
        "success": True,
        "username": username,
        "role": matched_user.get("role", ""),
        "message": "Face login successful"
    })

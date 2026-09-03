import cv2
import face_recognition
import os
import numpy as np
from flask import Flask, render_template, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "change-this-key"

# Session timeout (5 minutes)
SESSION_TIMEOUT = timedelta(minutes=5)

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["school_db"]
users = db["users"]

# Load known faces
known_encodings = []
known_names = []

for file in os.listdir("users"):
    img_path = os.path.join("users", file)
    img = face_recognition.load_image_file(img_path)
    enc = face_recognition.face_encodings(img)[0]
    known_encodings.append(enc)
    known_names.append(os.path.splitext(file)[0])


def detect_face():
    video = cv2.VideoCapture(0)
    while True:
        ret, frame = video.read()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        faces = face_recognition.face_locations(rgb_frame)
        encodings = face_recognition.face_encodings(rgb_frame, faces)

        for enc in encodings:
            matches = face_recognition.compare_faces(known_encodings, enc)
            face_dist = face_recognition.face_distance(known_encodings, enc)
            best_match = np.argmin(face_dist)

            if matches[best_match]:
                username = known_names[best_match]
                users.update_one(
                    {"username": username},
                    {"$set": {"last_login": datetime.now()}}
                )
                video.release()
                cv2.destroyAllWindows()
                return username

        cv2.imshow("Face Login", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video.release()
    cv2.destroyAllWindows()
    return None


@app.before_request
def check_session_timeout():
    if "user" in session:
        if datetime.now() > session.get("expires", datetime.now()):
            session.clear()
            return redirect(url_for("login"))


@app.route("/")
def login():
    user = detect_face()
    if user:
        session["user"] = user
        session["expires"] = datetime.now() + SESSION_TIMEOUT
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user" in session:
        return render_template("dashboard.html", user=session["user"])
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)

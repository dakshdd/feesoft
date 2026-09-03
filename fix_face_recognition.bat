@echo off
echo ============================================
echo Fixing Face Recognition Environment
echo ============================================

REM Use correct Python path
set PYTHON_EXE=C:\Users\daksh\AppData\Local\Programs\Python\Python314\python.exe

echo Using Python: %PYTHON_EXE%

echo Uninstalling old packages...
%PYTHON_EXE% -m pip uninstall -y face-recognition face_recognition_models dlib

echo Installing required packages...
%PYTHON_EXE% -m pip install cmake
%PYTHON_EXE% -m pip install dlib
%PYTHON_EXE% -m pip install git+https://github.com/ageitgey/face_recognition_models
%PYTHON_EXE% -m pip install face-recognition opencv-python pymongo flask werkzeug

echo ============================================
echo Installation complete! Testing import...
echo ============================================

%PYTHON_EXE% -c "import face_recognition; print('Face Recognition OK')"

echo ============================================
echo Running Camera Test...
echo ============================================

REM Create a temporary test script for camera
echo import cv2> test_camera.py
echo cam = cv2.VideoCapture(0)>> test_camera.py
echo ret, frame = cam.read()>> test_camera.py
echo if ret:>> test_camera.py
echo ^    print('Camera working, frame captured!')>> test_camera.py
echo else:>> test_camera.py
echo ^    print('Camera not detected!')>> test_camera.py
echo cam.release()>> test_camera.py

%PYTHON_EXE% test_camera.py

echo ============================================
echo Running MongoDB Connectivity Test...
echo ============================================

REM Create a temporary test script for MongoDB
echo from pymongo import MongoClient> test_mongo.py
echo try:>> test_mongo.py
echo ^    client = MongoClient("mongodb://localhost:27017/")>> test_mongo.py
echo ^    db = client["school_db"]>> test_mongo.py
echo ^    print("MongoDB connected, DB name:", db.name)>> test_mongo.py
echo except Exception as e:>> test_mongo.py
echo ^    print("MongoDB connection failed:", e)>> test_mongo.py

%PYTHON_EXE% test_mongo.py

echo ============================================
echo All tests complete!
echo ============================================

pause

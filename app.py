from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from ultralytics import YOLO
import os
import cv2
import random

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory data storage
signals_data = []
congestion_data = [
    {"name": "Downtown", "level": "High"},
    {"name": "Uptown", "level": "Moderate"},
    {"name": "Suburbs", "level": "Low"}
]
reported_issues = []

model = YOLO("yolov8n.pt")  # Load the YOLO model

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/signals', methods=['GET', 'POST'])
def signals():
    if request.method == 'POST':
        location = request.form['location']
        status = request.form['status']
        signals_data.append({'id': len(signals_data), 'location': location, 'status': status})
    return render_template('signals.html', signals=signals_data)

@app.route('/delete_signal/<int:signal_id>')
def delete_signal(signal_id):
    global signals_data
    signals_data = [s for s in signals_data if s['id'] != signal_id]
    return redirect(url_for('signals'))

@app.route('/congestion')
def congestion():
    return render_template('congestion.html', congestion=congestion_data)

@app.route('/simulate')
def simulate():
    return render_template('simulate.html')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        issue = request.form['issue']
        location = request.form['location']
        reported_issues.append({"issue": issue, "location": location})
        return redirect(url_for('dashboard'))
    return render_template('report.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        video_file = request.files['video']
        if video_file:
            filename = secure_filename(video_file.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video_file.save(video_path)

            results = analyze_video(video_path)

            return render_template('results.html', incoming=results['incoming'], outgoing=results['outgoing'], results=results)
    return render_template('upload.html')

def analyze_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    incoming = 0
    outgoing = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)
        vehicle_count = sum([len(r.boxes) for r in results])

        # Dummy logic: Randomly split detected vehicles
        incoming += vehicle_count // 2
        outgoing += vehicle_count - (vehicle_count // 2)

        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()

    total = incoming + outgoing
    congestion_status = "High" if total/frame_count > 10 else "Low"

    return {
        'incoming': incoming,
        'outgoing': outgoing,
        'vehicle_count': total,
        'average_vehicle_count': total/frame_count if frame_count else 0,
        'congestion_status': congestion_status
    }

@app.route('/results')
def results():
    incoming_count = 5
    outgoing_count = 3
    vehicle_count = incoming_count + outgoing_count
    results = {
        'vehicle_count': vehicle_count
    }
    return render_template('results.html', incoming=incoming_count, outgoing=outgoing_count, results=results)

@app.route('/upload-image', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        file = request.files.get('image')
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            congestion_level = analyze_image(filepath)
            return render_template('image_result.html', filename=filename, congestion=congestion_level)
    return render_template('upload_image.html')

def analyze_image(image_path):
    results = model(image_path)
    count = sum([len(r.boxes) for r in results])
    if count < 5:
        return "Low"
    elif count < 15:
        return "Medium"
    else:
        return "High"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
import threading

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        video_file = request.files['video']
        if video_file:
            filename = secure_filename(video_file.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video_file.save(video_path)

            # Clear old data before new processing
            live_data['timestamps'].clear()
            live_data['incoming_counts'].clear()
            live_data['outgoing_counts'].clear()
            live_data['congestion_levels'].clear()

            # Start processing in a new thread
            threading.Thread(target=process_video, args=(video_path,)).start()

            # Redirect to results page immediately
            return redirect(url_for('results'))

    return render_template('upload.html')

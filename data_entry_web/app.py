import os, logging
import httpx
import time
import uuid
import json,yaml
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for

# Initialize Flask App
app = Flask(__name__)

# --- Configuration Loading ---
try:
    with open('./app_conf.yml', 'r') as f:
        app_config = yaml.safe_load(f.read()) 
except FileNotFoundError:
    print("FATAL: app_conf.yml not found. Exiting.")
    exit(1)

STORAGE_HOST = app_config['storage']['host']
STORAGE_PORT = app_config['storage']['port']
# --- Microservice Configuration ---
STORAGE_SERVICE_URL = f'http://{STORAGE_HOST}:{STORAGE_PORT}' # Storage Service Base URL
PORT = 8071 # Data Entry Web App running port

# --- Helper Functions ---

def generate_base_payload(form_data):
    """Generates common fields required by the Storage Service API from form data and current time"""
    now = datetime.now()
    return {
        "school_id": form_data.get("school_id"),
        "school_name": form_data.get("school_name", "Unspecified School"), 
        "reporting_date": datetime.now().strftime("%Y-%m-%d"), 
        "student_id": form_data.get("student_id"),
        "student_name": form_data.get("student_name"),
        "timestamp": now.isoformat(),
        "trace_id": str(uuid.uuid4())
    }

# --- HTML Template (Functional Design) ---

DATA_ENTRY_HTML = """
<!doctype html>
<html>
<head>
    <title>Student Data Entry</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f9; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #ccc; padding-bottom: 10px; }
        form { margin-top: 20px; }
        label { display: block; margin-top: 10px; font-weight: bold; }
        input[type="text"], input[type="number"] { width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        input[type="submit"] { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; margin-top: 20px; }
        input[type="submit"]:hover { background-color: #0056b3; }
        .message { padding: 10px; margin-bottom: 15px; border-radius: 4px; }
        .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .toggle-btn { cursor: pointer; text-decoration: underline; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Student Data Entry Web App</h1>
        <p><a href="/">Home</a> | <a href="/dashboard">Dashboard</a> | <a href="/logout">Logout</a></p>

        {% if status %}
            <div class="message {% if 'failed' in status or 'unavailable' in status or 'Error' in status %}error{% else %}success{% endif %}">
                <strong>Status:</strong> {{ status }}
            </div>
        {% endif %}

        <h2>Submit Data</h2>
        
        <p>Switch between: <span class="toggle-btn" onclick="toggleForm('grade')">Grade Scores</span> | <span class="toggle-btn" onclick="toggleForm('activity')">Extracurricular Activity</span></p>

        <!-- Grade Score Form -->
        <form method="POST" action="{{ url_for('submit_data') }}" id="grade-form">
            <input type="hidden" name="data_type" value="grade">
            <h3>Grade Score Submission</h3>
            
            <label for="school_id_g">School ID:</label>
            <input type="text" id="school_id_g" name="school_id" required value="S001">

            <label for="student_id_g">Student ID:</label>
            <input type="text" id="student_id_g" name="student_id" required value="STU001">
            
            <label for="student_name_g">Student Name:</label>
            <input type="text" id="student_name_g" name="student_name" required value="Alex B">

            <label for="course">Course Name:</label>
            <input type="text" id="course" name="course" required value="Maths">
            
            <label for="assignment">Assignment Name:</label>
            <input type="text" id="assignment" name="assignment" required value="Midterm Exam">

            <label for="score">Score (0-100):</label>
            <input type="number" id="score" name="score" min="0" max="100" required value="85">

            <input type="submit" value="Submit Grade Score">
        </form>

        <!-- Activity Form (Initially Hidden) -->
        <form method="POST" action="{{ url_for('submit_data') }}" id="activity-form" style="display: none;">
            <input type="hidden" name="data_type" value="activity">
            <h3>Activity Submission</h3>

            <label for="school_id_a">School ID:</label>
            <input type="text" id="school_id_a" name="school_id" required value="S001">

            <label for="student_id_a">Student ID:</label>
            <input type="text" id="student_id_a" name="student_id" required value="STU001">
            
            <label for="student_name_a">Student Name:</label>
            <input type="text" id="student_name_a" name="student_name" required value="Alex B">
            
            <label for="activity_type">Activity Type:</label>
            <input type="text" id="activity_type" name="activity_type" required value="Sports">

            <label for="activity_name">Activity Name:</label>
            <input type="text" id="activity_name" name="activity_name" required value="Basketball">
            
            <label for="hours">Hours Spent:</label>
            <input type="number" id="hours" name="hours" min="0" step="0.5" required value="10.5">

            <input type="submit" value="Submit Activity">
        </form>

    </div>

    <script>
        // Form toggle logic
        function toggleForm(type) {
            const gradeForm = document.getElementById('grade-form');
            const activityForm = document.getElementById('activity-form');
            if (type === 'grade') {
                gradeForm.style.display = 'block';
                activityForm.style.display = 'none';
            } else if (type === 'activity') {
                gradeForm.style.display = 'none';
                activityForm.style.display = 'block';
            }
        }
    </script>
</body>
</html>
"""

# --- Routes ---

@app.route('/', methods=['GET'])
def data_entry_home():
    """Renders the main data entry form page."""
    status_message = request.args.get('status')
    return render_template_string(DATA_ENTRY_HTML, status=status_message)


@app.route('/submit', methods=['POST'])
def submit_data():
    """Handles form submission, constructs payload, and calls Storage Service."""
    form_data = request.form
    data_type = form_data.get('data_type')
    
    # 1. Prepare base payload (common fields)
    payload = generate_base_payload(form_data)
    api_path = None
    
    # 2. Add data-type specific fields
    if data_type == 'grade':
        # Corrected keys to match Storage Service (course and assignment)
        try:
            score = float(form_data.get('score'))
        except ValueError:
             return redirect(url_for('data_entry_home', status="Error: Score must be a number."))

        payload.update({
            "course": form_data.get('course'),
            "assignment": form_data.get('assignment'), 
            "score": score
        })
        api_path = '/store/grade' 
        
    elif data_type == 'activity':
        try:
            hours = float(form_data.get('hours'))
        except ValueError:
            return redirect(url_for('data_entry_home', status="Error: Hours must be a number."))

        payload.update({
            "activity_type": form_data.get('activity_type'),
            "activity_name": form_data.get('activity_name'),
            "hours": hours
        })
        api_path = '/store/activity' 
        
    else:
        return redirect(url_for('data_entry_home', status=f"Error: Invalid data type: {data_type}")) 
        
    # 3. Call Storage Service
    try:
        url = f"{STORAGE_SERVICE_URL}{api_path}"
        response = httpx.post(url, json=payload, timeout=10)
        
        if response.status_code == 201:
            message = f"{data_type.capitalize()} data submitted successfully! Trace ID: {payload['trace_id']}"
            return redirect(url_for('data_entry_home', status=message))
        else:
            print(f"Storage Service Error ({response.status_code}): {response.text}")
            error_details = response.text[:200]
            message = f"Storage Service failed ({response.status_code}). Details: {error_details}..."
            return redirect(url_for('data_entry_home', status=message))
            
    except httpx.RequestError as e:
        print(f"Connection Error to Storage Service: {e}")
        message = "Connection Error: Storage service is unavailable. Please check the 8090 port and service status."
        return redirect(url_for('data_entry_home', status=message))

if __name__ == '__main__':
    print(f"Running Data Entry Web App on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
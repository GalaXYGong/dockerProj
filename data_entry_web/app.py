import os
import httpx
import time
import uuid
import json,yaml
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for

# Initialize Flask App
app = Flask(__name__)

with open('./app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

STORAGE_HOST = app_config['storage']['host']
STORAGE_PORT = app_config['storage']['port']
# --- Microservice Configuration ---
STORAGE_SERVICE_URL = f'http://{STORAGE_HOST}:{STORAGE_PORT}' # Storage Service Base URL
PORT = 8071 # Data Entry Web App running port

# --- Helper Functions ---

def generate_base_payload(form_data):
    """Generates common fields required by the Storage Service API from form data and current time"""
    now = datetime.now()
    # Attempt to get common fields from the form
    return {
        "school_id": form_data.get("school_id"),
        "school_name": form_data.get("school_name"),
        "reporting_date": datetime.now().strftime("%Y-%m-%d"), # Use current date
        "student_id": form_data.get("student_id"),
        "student_name": form_data.get("student_name"),
        "timestamp": now.isoformat(), # ISO 8601 format
        "trace_id": str(uuid.uuid4()) # Generate unique trace_id
    }

# --- HTML Template (English and Tailwind CSS) ---

DATA_ENTRY_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Entry - Direct Mode</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style> 
        body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }
        .form-card {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s;
        }
        .form-card:hover {
            transform: translateY(-2px);
        }
        label { font-weight: 600; }
        input[type="text"], input[type="number"], input[type="password"] {
            padding: 0.5rem 0.75rem;
            border-radius: 0.5rem;
            border: 1px solid #d1d5db;
            width: 100%;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
            transition: border-color 0.15s, box-shadow 0.15s;
        }
        input:focus {
            outline: none;
            border-color: #4f46e5;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.5);
        }
    </style>
</head>
<body class="flex items-start justify-center p-8 min-h-screen">
    <div class="max-w-4xl w-full">
        
        <header class="mb-8 p-6 bg-white rounded-xl shadow-xl border-b-4 border-indigo-500 text-center">
            <h1 class="text-3xl font-extrabold text-gray-800 mb-2">Data Entry Service (Direct Mode)</h1>
            <p class="text-gray-600">Current User: <strong class="text-indigo-600">{{ username }}</strong> (Authentication Skipped)</p>
        </header>
        
        {% if status_message %}
            <div class="mb-6 p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg font-medium text-center">
                {{ status_message }}
            </div>
        {% endif %}

        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            <!-- 1. Enter Grade Data -->
            <div class="form-card bg-white p-6 rounded-xl border-t-4 border-green-500">
                <h2 class="text-xl font-bold text-gray-800 mb-4 pb-2 border-b">1. Enter Grade Data</h2>
                <form method="post" action="/data_entry_service/data_submit/grade" class="space-y-4">
                    <div class="grid grid-cols-2 gap-4">
                        <div><label for="school_id_g" class="block text-sm text-gray-700">School ID:</label><input type="text" id="school_id_g" name="school_id" required value="SC142"></div>
                        <div><label for="school_name_g" class="block text-sm text-gray-700">School Name:</label><input type="text" id="school_name_g" name="school_name" required value="BCIT Comp"></div>
                        <div><label for="student_id_g" class="block text-sm text-gray-700">Student ID:</label><input type="text" id="student_id_g" name="student_id" required value="S001"></div>
                        <div><label for="student_name_g" class="block text-sm text-gray-700">Student Name:</label><input type="text" id="student_name_g" name="student_name" required value="Alex B"></div>
                    </div>

                    <div><label for="course" class="block text-sm text-gray-700">Course:</label><input type="text" id="course" name="course" required value="BTECH-4000"></div>
                    <div><label for="assignment" class="block text-sm text-gray-700">Assignment Name:</label><input type="text" id="assignment" name="assignment" required value="Final Exam"></div>
                    <div><label for="score" class="block text-sm text-gray-700">Score (0-100):</label><input type="number" id="score" name="score" required min="0" max="100"></div>
                    
                    <button type="submit" class="w-full mt-4 py-2 px-4 bg-green-500 text-white font-semibold rounded-lg hover:bg-green-600 transition shadow-md">
                        Submit Grade
                    </button>
                </form>
            </div>

            <!-- 2. Enter Activity Data -->
            <div class="form-card bg-white p-6 rounded-xl border-t-4 border-blue-500">
                <h2 class="text-xl font-bold text-gray-800 mb-4 pb-2 border-b">2. Enter Activity Data</h2>
                <form method="post" action="/data_entry_service/data_submit/activity" class="space-y-4">
                     <div class="grid grid-cols-2 gap-4">
                        <div><label for="school_id_a" class="block text-sm text-gray-700">School ID:</label><input type="text" id="school_id_a" name="school_id" required value="SC142"></div>
                        <div><label for="school_name_a" class="block text-sm text-gray-700">School Name:</label><input type="text" id="school_name_a" name="school_name" required value="BCIT Comp"></div>
                        <div><label for="student_id_a" class="block text-sm text-gray-700">Student ID:</label><input type="text" id="student_id_a" name="student_id" required value="S001"></div>
                        <div><label for="student_name_a" class="block text-sm text-gray-700">Student Name:</label><input type="text" id="student_name_a" name="student_name" required value="Alex B"></div>
                    </div>
                    
                    <div><label for="activity_type" class="block text-sm text-gray-700">Activity Type:</label><input type="text" id="activity_type" name="activity_type" required value="Sports"></div>
                    <div><label for="activity_name" class="block text-sm text-gray-700">Activity Name:</label><input type="text" id="activity_name" name="activity_name" required value="Basketball"></div>
                    <div><label for="hours" class="block text-sm text-gray-700">Activity Hours:</label><input type="number" id="hours" name="hours" required min="0"></div>
                    
                    <button type="submit" class="w-full mt-4 py-2 px-4 bg-blue-500 text-white font-semibold rounded-lg hover:bg-blue-600 transition shadow-md">
                        Submit Activity
                    </button>
                </form>
            </div>

        </div>
        <p class="mt-8 text-xs text-gray-400 text-center">Data submitted directly to Storage Service (8090)</p>
    </div>
</body>
</html>
"""

# --- Flask Routes (All prefixed with /data_entry_service) ---

@app.route('/data_entry_service', methods=['GET']) 
def data_entry_home(): 
    """
    Home route: Displays the data entry page directly (login check removed).
    """
    # Since we removed the login logic, we set a fixed username for display
    fixed_username = "Direct-Access-User" 
    return render_template_string(DATA_ENTRY_HTML, 
                                  username=fixed_username, 
                                  status_message=request.args.get('status'))


@app.route('/data_entry_service/data_submit/<data_type>', methods=['POST'])
def data_submit(data_type):
    """
    Processes data entry. Calls Storage Service (8090).
    """
    form_data = request.form
    
    # 1. Construct base payload
    payload = generate_base_payload(form_data)
    
    # Define fields required for Grade and Activity data, used for validation
    common_fields = ['school_id', 'school_name', 'student_id', 'student_name']

    # 2. Construct specific data type payload
    if data_type == 'grade':
        specific_fields = ['course', 'assignment', 'score']
        required_fields = common_fields + specific_fields
        if not all(form_data.get(field) for field in required_fields):
            return redirect(url_for('data_entry_home', status="Missing required grade data fields."))
            
        payload.update({
            "course": form_data.get('course'),
            "assignment": form_data.get('assignment'),
            "score": float(form_data.get('score'))
        })
        api_path = '/store/grade' 
        
    elif data_type == 'activity':
        specific_fields = ['activity_type', 'activity_name', 'hours']
        required_fields = common_fields + specific_fields
        if not all(form_data.get(field) for field in required_fields):
            return redirect(url_for('data_entry_home', status="Missing required activity data fields."))
            
        # Note: We only update activity related fields here, common fields were generated above
        payload.update({
            "activity_type": form_data.get('activity_type'),
            "activity_name": form_data.get('activity_name'),
            "hours": float(form_data.get('hours'))
        })
        api_path = '/store/activity' 
        
    else:
        return redirect(url_for('data_entry_home', status=f"Invalid data type: {data_type}")) 
        
    # 3. Call Storage Service
    try:
        url = f"{STORAGE_SERVICE_URL}{api_path}"
        # Note: Auth Token is no longer passed here
        response = httpx.post(url, json=payload, timeout=10)
        
        if response.status_code == 201:
            message = f"{data_type.capitalize()} data submitted successfully! Trace ID: {payload['trace_id']}"
            return redirect(url_for('data_entry_home', status=message))
        else:
            print(f"Storage Service Error ({response.status_code}): {response.text}")
            message = f"Storage Service failed ({response.status_code}). Response: {response.text[:100]}..."
            return redirect(url_for('data_entry_home', status=message))
            
    except httpx.RequestError as e:
        print(f"Connection Error to Storage Service: {e}")
        message = "Storage service is unavailable. Please check the 8090 port."
        return redirect(url_for('data_entry_home', status=message))

if __name__ == '__main__':
    print(f"Starting Enter Data Web App on http://0.0.0.0:{PORT}/data_entry_service")
    app.run(host='0.0.0.0', port=PORT, debug=True)

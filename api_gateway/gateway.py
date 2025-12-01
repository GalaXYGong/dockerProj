import connexion, yaml, logging, logging.config, json
from flask import render_template_string
import httpx 
from flask import request, Response, redirect, session, url_for, g 
from urllib.parse import urljoin 

# --- Configuration Loading and Logging Setup ---
try:
    with open('./app_conf.yml', 'r') as f:
        app_config = yaml.safe_load(f.read())
except FileNotFoundError:
    print("FATAL: app_conf.yml not found. Exiting.")
    exit(1)

try:
    with open("log_conf.yml", "r") as f:
        LOG_CONFIG = yaml.safe_load(f.read())
        logging.config.dictConfig(LOG_CONFIG)
except FileNotFoundError:
    print("WARNING: log_conf.yml not found. Using default logging.")
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('basicLogger')

# Service configuration details for proxying
ANALYTICS_HOST = app_config['analytics_service']['host']
ANALYTICS_PORT = app_config['analytics_service']['port']

# Data Entry Web App Configuration
DATA_ENTRY_HOST = app_config['data_entry_service']['host']
DATA_ENTRY_PORT = app_config['data_entry_service']['port']
AUTH_SERVICE_HOST = app_config['auth_service']['host']
AUTH_SERVICE_PORT = app_config['auth_service']['port']

# URL construction
AUTH_SERVICE_URL = f'http://{AUTH_SERVICE_HOST}:{AUTH_SERVICE_PORT}'
DATA_ENTRY_WEB_URL = f'http://{DATA_ENTRY_HOST}:{DATA_ENTRY_PORT}'
ANALYTICS_SERVICE_URL = f'http://{ANALYTICS_HOST}:{ANALYTICS_PORT}'


# --- Dashboard HTML Content (Restored) ---
DASHBOARD_HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real-time Statistics Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
        .stat-card {
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            border-radius: 12px; /* Consistent rounding */
        }
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.15);
        }
    </style>
</head>
<body class="p-4 md:p-8">

    <div class="max-w-6xl mx-auto">
        
        <header class="mb-8 p-6 bg-white rounded-xl shadow-xl border-b-4 border-teal-500">
            <div class="flex justify-between items-center">
                <h1 class="text-3xl md:text-4xl font-extrabold text-gray-800">Real-time System Statistics Dashboard</h1>
                <a href="/" class="py-2 px-4 bg-gray-100 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-200 transition shadow-md">Back to Selection</a>
            </div>
            <p class="text-gray-600 mt-2">Data proxied from Analytics Service via API Gateway.</p>
        </header>

        <div id="loading" class="text-center p-8 text-xl font-semibold text-teal-600 animate-pulse">
            Loading data...
        </div>
        <div id="error-message" class="hidden text-center p-4 bg-red-100 text-red-700 rounded-xl shadow-md font-medium border border-red-300">
            Could not fetch statistics from the Gateway. Please check the Analytics Service connection.
        </div>

        <!-- UPDATED: Added avg fields and changed grid to 4 columns -->
        <div id="stats-container" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 hidden">

            <!-- Grade Stats -->
            <div class="stat-card bg-white p-6 shadow-md border-l-4 border-green-500">
                <p class="text-sm font-medium text-gray-500">Total Grade Readings</p>
                <p id="grade-count" class="mt-2 text-4xl font-bold text-green-600">--</p>
            </div>
            
            <div class="stat-card bg-white p-6 shadow-md border-l-4 border-green-500">
                <p class="text-sm font-medium text-gray-500">Average Score</p>
                <p id="avg-grade" class="mt-2 text-4xl font-bold text-green-600">--</p>
            </div>

            <div class="stat-card bg-white p-6 shadow-md border-l-4 border-green-500">
                <p class="text-sm font-medium text-gray-500">Minimum Score</p>
                <p id="min-grade" class="mt-2 text-4xl font-bold text-gray-900">--</p>
            </div>

            <div class="stat-card bg-white p-6 shadow-md border-l-4 border-green-500">
                <p class="text-sm font-medium text-gray-500">Maximum Score</p>
                <p id="max-grade" class="mt-2 text-4xl font-bold text-gray-900">--</p>
            </div>

            <!-- Activity Stats -->
            <div class="stat-card bg-white p-6 shadow-md border-l-4 border-blue-500">
                <p class="text-sm font-medium text-gray-500">Total Activity Readings</p>
                <p id="activity-count" class="mt-2 text-4xl font-bold text-blue-600">--</p>
            </div>
            
            <div class="stat-card bg-white p-6 shadow-md border-l-4 border-blue-500">
                <p class="text-sm font-medium text-gray-500">Average Activity Hours</p>
                <p id="avg-activity" class="mt-2 text-4xl font-bold text-blue-600">--</p>
            </div>
            
            <div class="stat-card bg-white p-6 shadow-md border-l-4 border-blue-500">
                <p class="text-sm font-medium text-gray-500">Minimum Activity Hours</p>
                <p id="min-activity" class="mt-2 text-4xl font-bold text-gray-900">--</p>
            </div>

            <div class="stat-card bg-white p-6 shadow-md border-l-4 border-blue-500">
                <p class="text-sm font-medium text-gray-500">Maximum Activity Hours</p>
                <p id="max-activity" class="mt-2 text-4xl font-bold text-gray-900">--</p>
            </div>
        </div>
        
        <footer class="mt-8 p-6 bg-white rounded-xl shadow-xl">
            <h2 class="text-xl font-bold text-gray-700 mb-4 border-b pb-2">Update Information</h2>
            <div class="flex flex-col md:flex-row md:justify-between text-gray-600 text-sm space-y-2 md:space-y-0">
                <p class="font-medium">Last Checkpoint Update Time: <span id="last-updated-time" class="font-semibold text-gray-800 ml-2">--</span></p>
                <p class="font-medium">Next Automatic Refresh: <span id="next-refresh" class="font-semibold text-teal-600 ml-2">--</span></p>
            </div>
        </footer>

    </div>

    <script>
        // API Gateway Proxy Route
        const API_URL = '/analytics/stats'; 
        const REFRESH_INTERVAL_MS = 10000; // 10 seconds refresh interval
        
        function formatTimestamp(ms) {
            if (ms === 0) return 'No data processed yet';
            const date = new Date(ms);
            // Use English localized format
            return date.toLocaleString('en-US', {
                year: 'numeric', month: '2-digit', day: '2-digit', 
                hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
            });
        }

        async function fetchAndDisplayStats() {
            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('error-message').classList.add('hidden');
            document.getElementById('stats-container').classList.add('hidden');

            const MAX_RETRIES = 5;
            let success = false;

            for (let i = 0; i < MAX_RETRIES; i++) {
                try {
                    // Fetching data from gateway proxy path
                    const response = await fetch(API_URL); 
                    if (!response.ok) {
                        // If gateway returns 401/403 (unauthorized), stop retrying and show error.
                        if (response.status === 401 || response.status === 403) {
                             document.getElementById('error-message').innerHTML = 'Access denied. Please log in to the Gateway.';
                             i = MAX_RETRIES; // Stop loop
                             break;
                        }
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const stats = await response.json();
                    
                    // Populate data cards
                    document.getElementById('grade-count').textContent = stats.num_grade_readings;
                    document.getElementById('avg-grade').textContent = stats.avg_grade_readings !== undefined ? stats.avg_grade_readings.toFixed(2) : '--';
                    document.getElementById('min-grade').textContent = stats.min_grade_readings !== undefined ? stats.min_grade_readings.toFixed(1) : '--';
                    document.getElementById('max-grade').textContent = stats.max_grade_readings !== undefined ? stats.max_grade_readings.toFixed(1) : '--';
                    
                    document.getElementById('activity-count').textContent = stats.num_activity_readings;
                    document.getElementById('avg-activity').textContent = stats.avg_activity_hours !== undefined ? stats.avg_activity_hours.toFixed(2) : '--';
                    document.getElementById('min-activity').textContent = stats.min_activity_hours !== undefined ? stats.min_activity_hours.toFixed(1) : '--';
                    document.getElementById('max-activity').textContent = stats.max_activity_hours !== undefined ? stats.max_activity_hours.toFixed(1) : '--';

                    // Populate footer information
                    document.getElementById('last-updated-time').textContent = formatTimestamp(stats.last_updated);
                    
                    document.getElementById('loading').classList.add('hidden');
                    document.getElementById('stats-container').classList.remove('hidden');
                    
                    success = true;
                    break; 

                } catch (error) {
                    console.error("Fetch attempt failed:", error);
                    if (i < MAX_RETRIES - 1) {
                        const delay = Math.pow(2, i) * 1000; 
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }
                }
            }
            
            if (!success) {
                document.getElementById('loading').classList.add('hidden');
                document.getElementById('stats-container').classList.add('hidden');
                document.getElementById('error-message').classList.remove('hidden');
            }
        }
        
        function startAutoRefresh() {
            fetchAndDisplayStats(); 
            
            setInterval(() => {
                fetchAndDisplayStats();
                updateNextRefreshTime();
            }, REFRESH_INTERVAL_MS);

            updateNextRefreshTime(); 
        }

        function updateNextRefreshTime() {
            const nextRefreshElement = document.getElementById('next-refresh');
            let remaining = REFRESH_INTERVAL_MS / 1000;
            
            nextRefreshElement.textContent = `Countdown ${remaining} seconds`;
            
            const countdownInterval = setInterval(() => {
                remaining--;
                if (remaining <= 0) {
                    clearInterval(countdownInterval);
                    nextRefreshElement.textContent = 'Refreshing';
                } else {
                    nextRefreshElement.textContent = `Countdown ${remaining} seconds`;
                }
            }, 1000);
        }

        window.onload = startAutoRefresh;

    </script>
</body>
</html>
"""


# --- Utility Functions ---

def is_authenticated():
    """Checks if the user session has a valid token."""
    return 'auth_token' in session

def login_required(f):
    """Decorator to protect routes."""
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            logger.warning("Access denied: User not logged in. Redirecting to login.")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__ # Preserve original function name
    return wrapper

# --- UI/Frontend Routes ---

@login_required
def get_selection_page():
    """Renders the main service selection page (e.g., after login)."""
    logger.info("Serving selection page to user.")
    return render_template_string("""
        <!doctype html>
        <html lang="en">
        <head>
            <title>Microservice Selector</title>
            <style>
                body { font-family: sans-serif; margin: 20px; text-align: center; background-color: #f4f4f9; }
                .container { max-width: 400px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 6px 10px rgba(0,0,0,0.15); }
                h1 { color: #007bff; }
                .link-btn { display: block; padding: 15px; margin: 15px 0; background-color: #007bff; color: white; text-decoration: none; border-radius: 8px; font-size: 1.2em; transition: background-color 0.3s; }
                .link-btn:hover { background-color: #0056b3; }
                .logout-link { display: block; margin-top: 30px; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Service Access Portal</h1>
                <a href="/data_entry_web" class="link-btn">Data Entry Web App</a>
                <a href="/dashboard" class="link-btn">Analytics Dashboard</a>
                <a href="/logout" class="logout-link">Logout</a>
            </div>
        </body>
        </html>
    """)

@login_required
def get_dashboard_page():
    """Renders the dashboard page by returning the full HTML content with embedded JS."""
    return render_template_string(DASHBOARD_HTML_CONTENT)


def login():
    """Handles user login."""
    # List of expected token keys from Auth Service
    TOKEN_KEYS = ['token', 'mock_token', 'access_token'] 

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            auth_response = httpx.post(f"{AUTH_SERVICE_URL}/authenticate", 
                                        json={'username': username, 'password': password}, 
                                        timeout=5)
            
            if auth_response.status_code == 200:
                try:
                    token_data = auth_response.json()
                except json.JSONDecodeError:
                    # Case 1: 200 OK but response is not valid JSON
                    logger.error(f"AUTH DEBUG: 200 OK but response is not valid JSON. RAW Response: {auth_response.text}")
                    return render_template_string(LOGIN_HTML, error="Authentication response invalid (not JSON). Check Auth Service logs.")
                
                # Case 2: 200 OK and valid JSON, attempt to find a token
                found_token = None
                used_key = None
                for key in TOKEN_KEYS:
                    if key in token_data:
                        found_token = token_data[key]
                        used_key = key
                        break
                
                if found_token:
                    session['auth_token'] = found_token
                    session['username'] = username
                    logger.info(f"User {username} logged in successfully to Gateway using key '{used_key}'.")
                    
                    next_url = request.args.get('next') or url_for('get_selection_page')
                    return redirect(next_url)
                else:
                    # CRITICAL LOGGING: Log the received data when 'token' is missing
                    logger.error(f"AUTH DEBUG: 200 OK but NO expected token key found. Keys checked: {TOKEN_KEYS}. Received JSON: {json.dumps(token_data)}")
                    error_message = f"Authentication succeeded (200 OK), but Auth Service did not return an expected Token key ({', '.join(TOKEN_KEYS)}). Check Auth Service response body."
                    return render_template_string(LOGIN_HTML, error=error_message)
            else:
                # Authentication failed (e.g., HTTP 401)
                logger.warning(f"Login failed for user {username}: {auth_response.status_code}. Response: {auth_response.text}")
                try:
                    error_message = auth_response.json().get('message', f"Authentication failed with status {auth_response.status_code}.")
                except json.JSONDecodeError:
                    error_message = f"Authentication failed, status code {auth_response.status_code}."
                return render_template_string(LOGIN_HTML, error=error_message)

        except httpx.RequestError as e:
            logger.error(f"Authentication service connection error: {e}")
            return render_template_string(LOGIN_HTML, error="Authentication service unavailable.")
            
    return render_template_string(LOGIN_HTML, error=None)

def logout():
    """Handles user logout."""
    session.pop('auth_token', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# HTML template for login (using English for all display elements)
LOGIN_HTML = """
<!doctype html>
<html>
<head>
    <title>Login</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f9; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-box { width: 300px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #333; margin-bottom: 20px; }
        label { display: block; text-align: left; margin-top: 10px; font-weight: bold; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        input[type="submit"] { background-color: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; margin-top: 20px; width: 100%; }
        input[type="submit"]:hover { background-color: #0056b3; }
        .error { color: red; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>Login</h1>
        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST" action="{{ url_for('login') }}">
            <label for="username">Username (e.g., user1):</label>
            <input type="text" id="username" name="username" required>
            
            <label for="password">Password (e.g., pass1):</label>
            <input type="password" id="password" name="password" required>
            
            <input type="submit" value="Log In">
        </form>
    </div>
</body>
</html>
"""

# --- Proxy Functions ---

@login_required
def proxy_data_entry_web(path):
    """Proxies requests for the Data Entry Web App."""
    
    # 1. Construct Target URL
    target_url = urljoin(DATA_ENTRY_WEB_URL, path)
    
    # Preserve original query string
    if request.query_string:
        target_url += '?' + request.query_string.decode()
        
    logger.info(f"Proxying Data Entry Web request ({request.method}) from {request.path} to TARGET: {target_url}")
    
    try:
        # 2. Request Preparation
        headers = {}
        if is_authenticated():
            # Pass the token in the Authorization header
            headers['Authorization'] = f"Bearer {session.get('auth_token')}"
            
        
        # 3. Send Request
        if request.method == 'GET':
            response = httpx.get(target_url, headers=headers, timeout=10)
        elif request.method == 'POST':
            # Use content=request.get_data() and pass the original content type
            response = httpx.post(target_url, content=request.get_data(), headers={**headers, 'Content-Type': request.content_type}, timeout=10)
        else:
            return Response("Method not allowed", status=405)

        logger.info(f"Proxy received status {response.status_code} from Data Entry Web for path '{path}'. Content length: {len(response.content)}.")

        # 4. Handle Redirects (Status 3xx)
        location = response.headers.get('location')
        if location and response.status_code in (301, 302, 303, 307, 308):
            
            # Web App typically redirects POST /submit to GET /?status=... (its own root path /)
            
            # Case A: Redirect to internal root path '/' (Data Entry Web App's root)
            if location.startswith('/'):
                
                if location == '/' or location.startswith('/?'):
                    # The redirect is going to the web app's homepage.
                    
                    # Remove leading slash from location to avoid double slashes 
                    # when joining with the gateway's base path /data_entry_web/
                    if location.startswith('/'):
                        location = location[1:] 

                    redirect_path = f"/data_entry_web/{location}" # e.g. /data_entry_web/?status=...
                    
                    logger.info(f"Internal redirect to Web App Root ('/') detected. Correcting client redirect path to: {redirect_path}")
                    return redirect(redirect_path, code=response.status_code)
                    
                # Case B: Redirect to other internal Web App path (e.g., /favicon.ico, /submit?...)
                elif location.startswith('/'):
                    # This handles /submit?__debugger__ and any other internal path
                    redirect_path = f"/data_entry_web{location}"
                    logger.info(f"Internal path redirect to {location} detected. Correcting client redirect path to: {redirect_path}")
                    return redirect(redirect_path, code=response.status_code)
            
            # Case C: External URL, keep as is (no correction needed)
            
        # 5. Return Response
        
        # Filter out hop-by-hop headers
        response_headers = [(name, value) for name, value in response.headers.items() 
                            if name.lower() not in ('content-encoding', 'transfer-encoding', 'content-length', 'connection')]
        
        return Response(response.content, response.status_code, response_headers)

    except httpx.RequestError as e:
        logger.error(f"Failed to proxy request to Data Entry Web: {e}")
        return Response(f"Service Unavailable: Data Entry Web is currently unreachable at {DATA_ENTRY_WEB_URL}.", 
                        status=503, 
                        mimetype='text/plain')

@login_required
def proxy_analytics_stats():
    """Proxies GET requests for the Analytics Service /stats endpoint."""
    target_url = f"{ANALYTICS_SERVICE_URL}/stats"
    logger.info(f"Proxying Analytics Service request (GET) to TARGET: {target_url}")

    try:
        # CRITICAL: Prepare headers to pass the token to downstream services
        headers = {}
        if is_authenticated():
            # Pass the token in the Authorization header
            headers['Authorization'] = f"Bearer {session.get('auth_token')}"

        response = httpx.get(target_url, headers=headers, timeout=10)
        
        # NOTE: Do NOT use response.json() here. Proxy raw content.
        
        if response.status_code == 200:
            logger.info(f"Analytics Service response status 200. Content length: {len(response.content)}.")
            return Response(response.content, response.status_code, response.headers)
        else:
            logger.error(f"Analytics Service returned status {response.status_code}. Response: {response.text}")
            return Response(response.content, response.status_code, response.headers)

    except httpx.RequestError as e:
        logger.error(f"Failed to proxy request to Analytics Service: {e}")
        # Return a 503 JSON response for the frontend to handle gracefully
        return Response(json.dumps({"message": "Service Unavailable: Analytics Service"}), 503, {'Content-Type': 'application/json'})

# --- SHIM FUNCTION FOR /submit POST ---

@login_required
def proxy_submit_shim():
    """
    Shim function to catch POST requests coming to the root /submit path.
    This is necessary because the Data Entry Web App's HTML form action is hardcoded to "/submit".
    It redirects the request internally to the correct Data Entry Web App's '/submit' path.
    """
    # The 'submit' argument is the path component for the downstream service
    return proxy_data_entry_web('submit') 


# --- Main App Execution ---

app = connexion.FlaskApp(__name__, specification_dir='')

# CRITICAL: Set secret key for session management on the underlying Flask app
app.app.secret_key = 'a_very_secure_secret_key_for_api_gateway_456789' 

# Manually add UI/Frontend routes using app.app.add_url_rule()
app.app.add_url_rule('/', 'get_selection_page', get_selection_page, methods=['GET'])
app.app.add_url_rule('/login', 'login', login, methods=['GET', 'POST'])
app.app.add_url_rule('/logout', 'logout', logout, methods=['GET'])

# Dashboard route restored to serve the full HTML with embedded JS
app.app.add_url_rule('/dashboard', 'get_dashboard_page', get_dashboard_page, methods=['GET'])

# Proxy route for the dashboard's internal API call
app.app.add_url_rule('/analytics/stats', 'proxy_analytics_stats', proxy_analytics_stats, methods=['GET'])

# --- DATA ENTRY WEB APP PROXY ROUTES ---

# 1. Base /data_entry_web GET/POST (handles the main page itself, path='')
app.app.add_url_rule('/data_entry_web', 'proxy_data_entry_web_base', login_required(proxy_data_entry_web), methods=['GET', 'POST'], defaults={'path': ''})

# 1.5. CRITICAL FIX: Add base path with trailing slash for redirects with query strings.
# This fixes the 404 seen when the client follows the redirect to /data_entry_web/?status=...
app.app.add_url_rule('/data_entry_web/', 'proxy_data_entry_web_base_slash', login_required(proxy_data_entry_web), methods=['GET', 'POST'], defaults={'path': ''})


# 2. Paths under /data_entry_web/<path:path> 
app.app.add_url_rule('/data_entry_web/<path:path>', 'proxy_data_entry_web_path', login_required(proxy_data_entry_web), methods=['GET', 'POST'])

# 3. CRITICAL SHIM: Route for POST /submit
# This catches the hardcoded form action from the Data Entry Web App and proxies it.
app.app.add_url_rule('/submit', 'proxy_submit_shim', proxy_submit_shim, methods=['POST']) 


if __name__ == '__main__':
    # Uvicorn (Connexion's underlying server) does not accept 'debug' argument.
    app.run(port=8099, host='0.0.0.0')
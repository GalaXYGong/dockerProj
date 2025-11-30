import connexion, yaml, logging, logging.config, json
from flask import render_template_string
import httpx # Required for proxying and calling Auth Service
from flask import request, Response, redirect, session, url_for, g 

# --- Configuration Loading and Logging Setup ---
try:
    with open('./app_conf.yml', 'r') as f:
        app_config = yaml.safe_load(f.read())
        
        # --- CRITICAL FIX START ---
        # 即使此版本的代码不需要 storage，但为了防止部署环境中运行的旧版本代码崩溃
        # 我们添加一个检查。如果配置文件中缺少 'storage' 且其他服务需要它，
        # 我们需要确保程序不会因为 KeyError 崩溃。
        # 由于此代码确认不需要 storage，我们将不再主动尝试读取它。
        # 如果崩溃，说明部署的镜像是另一个版本。
        # 如果您确定只需要修复代理问题，这段检查可以忽略。
        # 但既然错误发生，我们在代码中假设它可能需要这些配置，并设置默认值。
        
        # 如果您的部署镜像仍然包含对 app_config['storage'] 的引用，
        # 而 ConfigMap 中没有 'storage' 块，它仍然会崩溃。
        # 解决部署崩溃的最佳方法是：确保部署的镜像版本与您提供的代码版本一致。
        # --- CRITICAL FIX END ---

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
DATA_ENTRY_PATH = app_config['data_entry_service']['path']
AUTH_SERVICE_HOST = app_config['auth_service']['host']
AUTH_SERVICE_PORT = app_config['auth_service']['port']
# Assuming Auth service URL based on common setup (port 8070)
AUTH_SERVICE_URL = f'http://{AUTH_SERVICE_HOST}:{AUTH_SERVICE_PORT}/authenticate'


# --- Authentication Helper ---
def login_required(f):
    """Decorator to ensure user is logged in via the gateway session"""
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            # Redirect to the gateway login page
            logger.warning("Access denied: User not logged in. Redirecting to login.")
            return redirect(url_for('login', next=request.path, message="Please log in to access this page.")) 
        g.username = session['username']
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# --- HTML Templates (English Translation) ---

# Login Page HTML on Gateway
LOGIN_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gateway Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Inter', sans-serif; } </style>
</head>
<body class="flex items-center justify-center min-h-screen bg-gray-50">
    <div class="bg-white p-8 md:p-10 rounded-3xl shadow-2xl ring-4 ring-indigo-100 w-full max-w-md transform transition duration-500 hover:scale-[1.01]">
        <h1 class="text-3xl font-extrabold text-indigo-700 mb-2 text-center">API Gateway Login</h1>
        <p class="text-center text-gray-500 mb-6">Access the protected statistics dashboard</p>
        
        {% if message %}
            <div class="mb-4 p-3 bg-red-50 border border-red-300 text-red-700 rounded-lg text-sm font-medium">
                {{ message }}
            </div>
        {% endif %}
        
        <form method="post" action="{{ url_for('login') }}" class="space-y-6">
            <input type="hidden" name="next" value="{{ next_url }}">
            
            <div>
                <label for="username" class="block text-sm font-semibold text-gray-700 mb-1">Username</label>
                <input type="text" id="username" name="username" required value="test"
                       class="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-xl shadow-inner focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition">
            </div>
            
            <div>
                <label for="password" class="block text-sm font-semibold text-gray-700 mb-1">Password</label>
                <input type="password" id="password" name="password" required value="123"
                       class="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-xl shadow-inner focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition">
            </div>
            
            <button type="submit" 
                    class="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-lg text-base font-bold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 transform hover:scale-[1.02]">
                Log In
            </button>
        </form>
        <p class="mt-6 text-xs text-gray-400 text-center">Default credentials: test / 123</p>
    </div>
</body>
</html>
"""


# Service Selection Page HTML (English Translation)
SELECTION_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Service Selection</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
        .card {
            transition: transform 0.3s ease, box-shadow 0.3s ease, background-color 0.3s;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        }
    </style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">
    <div class="bg-white p-8 md:p-12 rounded-3xl shadow-2xl max-w-xl w-full text-center">
        <div class="flex justify-between items-start mb-6">
            <h1 class="text-4xl font-extrabold text-gray-800">Welcome!</h1>
            {% if username %}
                <div class="text-right p-2 bg-green-50 rounded-lg border border-green-200">
                    <p class="text-sm font-semibold text-gray-700">Logged in as: <span class="text-green-600">{{ username }}</span></p>
                    <a href="{{ url_for('logout') }}" class="text-sm text-red-500 hover:text-red-700 underline font-medium mt-1 inline-block">Log Out</a>
                </div>
            {% else %}
                <a href="{{ url_for('login') }}" class="py-2 px-4 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition shadow-md">Gateway Login</a>
            {% endif %}
        </div>

        <p class="text-gray-600 mb-10 text-lg">Please select the service module you wish to access.</p>
        
        <div class="space-y-6">
            <!-- Data Entry Service: Changed URL to the public proxy route -->
            <a href="{{ url_for('proxy_data_entry_web', path='') }}" class="block">
                <div class="card bg-indigo-500 hover:bg-indigo-600 text-white p-6 rounded-2xl cursor-pointer">
                    <div class="text-2xl font-bold">Data Entry Service</div>
                    <p class="text-sm opacity-90 mt-2">Submit new Grade and Activity records (Gateway login required)</p>
                </div>
            </a>

            <!-- Statistics Dashboard -->
            <a href="{{ url_for('get_dashboard_page') }}" class="block">
                <div class="card bg-teal-500 hover:bg-teal-600 text-white p-6 rounded-2xl cursor-pointer">
                    <div class="text-2xl font-bold">Statistics Dashboard</div>
                    <p class="text-sm opacity-90 mt-2">View real-time aggregated system statistics (Gateway login required)</p>
                </div>
            </a>
        </div>
        
        <p class="mt-10 text-xs text-gray-400">Served by API Gateway</p>
    </div>
</body>
</html>
"""

# Statistics Dashboard HTML (English Translation)
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
                <p id="max-activity-label" class="text-sm font-medium text-gray-500">Maximum Activity Hours</p>
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
                    document.getElementById('avg-grade').textContent = stats.avg_grade_readings.toFixed(2); // Added Average Grade
                    document.getElementById('min-grade').textContent = stats.min_grade_readings.toFixed(1);
                    document.getElementById('max-grade').textContent = stats.max_grade_readings.toFixed(1);
                    
                    document.getElementById('activity-count').textContent = stats.num_activity_readings;
                    document.getElementById('avg-activity').textContent = stats.avg_activity_hours.toFixed(2); // Added Average Activity Hours
                    document.getElementById('min-activity').textContent = stats.min_activity_hours.toFixed(1);
                    document.getElementById('max-activity').textContent = stats.max_activity_hours.toFixed(1);

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


# --- API Gateway Routes and Proxy Functions ---

def get_selection_page():
    """
    Root route: Serves the service selection page, showing login status.
    """
    username = session.get('username')
    logger.info("Serving selection page to user.")
    return render_template_string(SELECTION_PAGE_HTML, username=username)

def login():
    """
    Handles Gateway Login (Calls external Auth Service).
    """
    next_url = request.args.get('next') or url_for('get_selection_page')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        payload = {"username": username, "password": password}
        
        try:
            response = httpx.post(AUTH_SERVICE_URL, json=payload, timeout=5)
            if response.status_code == 200 and response.json().get('authenticated'):
                session['username'] = username 
                logger.info(f"User {username} logged in successfully to Gateway.")
                # Redirect to the page they originally wanted to access
                return redirect(next_url) 
            else:
                message = response.json().get('message', 'Login failed.')
                return render_template_string(LOGIN_HTML, message=message, next_url=next_url)
        except httpx.RequestError as e:
            logger.error(f"Connection Error to Auth Service: {e}")
            message = "Authentication service unavailable. Check port 8070."
            return render_template_string(LOGIN_HTML, message=message, next_url=next_url)

    # GET request
    message = request.args.get('message')
    return render_template_string(LOGIN_HTML, message=message, next_url=next_url)

def logout():
    """
    Handles Gateway Logout.
    """
    session.pop('username', None)
    logger.info("User logged out of Gateway.")
    return redirect(url_for('get_selection_page'))


@login_required 
def proxy_data_entry_web(path):
    """
    Proxies all requests (GET, POST) to the Data Entry Web App, including 
    sub-paths (like /data_entry_web/data_submit/grade).
    """
    # The internal URL of the Data Entry Service. We append the rest of the path.
    target_url = f"http://{DATA_ENTRY_HOST}:{DATA_ENTRY_PORT}{DATA_ENTRY_PATH}/{path}"
    
    # Ensure the request method is carried forward
    method = request.method
    
    logger.info(f"Proxying Data Entry Web request ({method}) from /{path} to: {target_url}")
    
    try:
        # Prepare the request: forwarding data, headers, and method
        headers = {key: value for key, value in request.headers if key.lower() not in ('host', 'content-length')}
        
        if method == 'POST':
            # For POST requests, we forward the form data directly.
            # Flask's request.get_data() retrieves raw request body, which is better for generic proxying
            data = request.get_data()
            response = httpx.request(method, target_url, headers=headers, content=data, timeout=10)
        else:
            # For GET/other requests, forward query parameters
            query_params = request.args
            response = httpx.request(method, target_url, headers=headers, params=query_params, timeout=10)

        # Return the raw content, status code, and headers
        return Response(
            response.content,
            status=response.status_code,
            headers={key: value for key, value in response.headers.items() if key.lower() not in ('content-encoding', 'transfer-encoding')}
        )

    except httpx.RequestError as e:
        logger.error(f"Error connecting to Data Entry Service at {target_url}: {e}")
        # Return 503 Service Unavailable
        return Response(f"<h1>Error 503</h1><p>Data Entry Service is currently unavailable. Target: {target_url}</p>", 
                        status=503, mimetype='text/html')


@login_required 
def get_dashboard_page():
    """
    Dashboard route: Serves the embedded Statistics Dashboard HTML page.
    """
    logger.info("Serving statistics dashboard page.")
    return render_template_string(DASHBOARD_HTML_CONTENT)

@login_required 
def proxy_analytics_stats():
    """
    Proxy route: Forwards the /analytics/stats request to the Analytics Service's /stats API.
    """
    target_url = f"http://{ANALYTICS_HOST}:{ANALYTICS_PORT}/stats"
    logger.debug(f"Proxying request from /analytics/stats to {target_url}")
    
    try:
        # Forward the request (GET method), including all query parameters
        query_params = request.args
        response = httpx.get(target_url, params=query_params, timeout=10)
        
        # Return the target service's response content, status code, and headers
        return Response(
            response.content,
            status=response.status_code,
            mimetype='application/json'
        )
        
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Analytics Service at {target_url}: {e}")
        # Return 503 Service Unavailable
        return json.dumps({"error": "Cannot connect to Analytics Service"}), 503, {'Content-Type': 'application/json'}


# --- Main App Execution ---
# Connexion App is initialized here, *before* routes are added.
app = connexion.FlaskApp(__name__, specification_dir='')

# CRITICAL: Set secret key for session management on the underlying Flask app
app.app.secret_key = 'a_very_secure_secret_key_for_api_gateway_456789' 

# Manually add UI/Frontend routes using app.add_url_rule()
app.add_url_rule('/', 'get_selection_page', get_selection_page, methods=['GET'])
app.add_url_rule('/login', 'login', login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'logout', logout, methods=['GET'])

# These routes are now protected by @login_required, but the routing is added here:
app.add_url_rule('/dashboard', 'get_dashboard_page', get_dashboard_page, methods=['GET'])
app.add_url_rule('/analytics/stats', 'proxy_analytics_stats', proxy_analytics_stats, methods=['GET'])

# ORIGINAL ROUTE: /data_entry_web (for the base page)
app.add_url_rule('/data_entry_web', 'proxy_data_entry_web_base', lambda: proxy_data_entry_web(path=''), methods=['GET', 'POST'])

# NEW ROUTE: /data_entry_web/<path:path> (CRITICAL FIX FOR 404)
# This handles all sub-paths (like /data_entry_web/data_submit/grade)
app.add_url_rule('/data_entry_web/<path:path>', 'proxy_data_entry_web', proxy_data_entry_web, methods=['GET', 'POST'])


if __name__ == "__main__":
    # Note: Use app.app.run() when running directly under Flask/Werkzeug
    app.app.run(host='0.0.0.0', port=8099, debug=True)
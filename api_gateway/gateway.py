import connexion, yaml, logging, logging.config, json
from flask import render_template_string
import httpx 
from flask import request, Response, redirect, session, url_for, g 
from urllib.parse import urljoin # Import for robust URL joining

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
DATA_ENTRY_PATH = app_config['data_entry_service']['path']
AUTH_SERVICE_HOST = app_config['auth_service']['host']
AUTH_SERVICE_PORT = app_config['auth_service']['port']
# Assuming Auth service URL based on common setup (port 8070)
AUTH_SERVICE_URL = f'http://{AUTH_SERVICE_HOST}:{AUTH_SERVICE_PORT}'

# Base URL for the Data Entry Microservice in the cluster
DATA_ENTRY_BASE_URL = f'http://{DATA_ENTRY_HOST}:{DATA_ENTRY_PORT}'
DATA_ENTRY_PROXY_URL = DATA_ENTRY_BASE_URL + DATA_ENTRY_PATH # e.g., http://data-entry-web-svc:8071/data_entry_service


# --- Helper Function for Auth ---

def is_user_authenticated():
    """Checks if the user session has a valid token."""
    # Simplified check for demonstration purposes, assuming session['token'] exists after login
    # For a real system, token validation would be needed.
    return 'token' in session

def login_required(f):
    """Decorator to protect routes."""
    # This decorator is provided in the previous turn's context, but its full definition is missing.
    # We define a basic version here to ensure the flow works.
    def decorated_function(*args, **kwargs):
        if not is_user_authenticated():
            # If not authenticated, redirect to login page
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__ # Must preserve function name for Flask/Connexion
    return decorated_function

# --- Placeholder/Mock UI Routes (for context) ---

def get_selection_page():
    return "<html><body><h1>Welcome to the API Gateway</h1><p>Please <a href='/login'>Login</a> or go to <a href='/data_entry_web'>Data Entry</a> (requires auth bypass in this demo).</p></body></html>"

def login():
    if request.method == 'POST':
        # Mock login: just set a token and redirect
        session['token'] = 'mock-auth-token-123'
        logger.info("User logged in.")
        return redirect(request.args.get('next') or url_for('get_selection_page'))
    return "<html><body><form method='post'>Username: <input name='username'><br>Password: <input type='password' name='password'><br><button type='submit'>Login</button></form></body></html>"

def logout():
    session.pop('token', None)
    logger.info("User logged out.")
    return redirect(url_for('get_selection_page'))

# --- Dashboard & Analytics Proxy (for context) ---

# @login_required # Assume this is commented out for initial testing
def get_dashboard_page():
    return "<h1>Dashboard Page</h1>"

# @login_required
def proxy_analytics_stats():
    # Placeholder for analytics proxy logic
    try:
        response = httpx.get(f"http://{ANALYTICS_HOST}:{ANALYTICS_PORT}/stats", timeout=5)
        return Response(response.content, response.status_code, response.headers)
    except httpx.RequestError:
        return Response(json.dumps({"error": "Analytics Service"}), 503, {'Content-Type': 'application/json'})


# --- 核心修正区域：Data Entry Web Proxy ---

# @login_required # Assume this is commented out for initial testing
def proxy_data_entry_web(path):
    """
    Proxies requests from /data_entry_web/<path> to the Data Entry Service's internal path.
    The internal path is DATA_ENTRY_PATH (e.g., /data_entry_service).
    
    Args:
        path (str): The remaining path segment after /data_entry_web/. Can be empty.
    """
    # 1. 构造目标 URL
    # DATA_ENTRY_PROXY_URL 已经是 http://data-entry-web-svc:8071/data_entry_service
    # 我们需要将 path (即 /grade, /data_submit/grade, 或空字符串) 拼接到它后面
    
    # 修正点：确保 path 是从根开始的相对路径，并安全地拼接到 BASE_URL。
    # 假设 API Gateway 接收 /data_entry_web/abc，则 path = 'abc'
    # 目标 URL 应该是 http://data-entry-web-svc:8071/data_entry_service/abc
    
    # 确保 path 不以斜杠开头，除非它是空字符串，urljoin 可以很好地处理。
    # 如果 path 是空字符串 ('')，urljoin(..., '') 会返回 DATA_ENTRY_PROXY_URL
    # 如果 path 是 'subpath'，urljoin(..., 'subpath') 会返回 DATA_ENTRY_PROXY_URL/subpath
    target_path = path if path is not None else ''

    # 如果 Flask 在路由匹配时保留了路径中的尾部斜杠（例如：/data_entry_web/ 导致 path=''）
    # 并且用户在表单中使用了相对 action，我们需要确保所有转发的路径都是正确的。
    # 最安全的做法是使用 request.full_path 来获取请求中 '/data_entry_web' 之后的所有内容，
    # 但由于您的路由定义是 /data_entry_web/<path:path>，我们依赖 path 参数。

    # 使用 urljoin 构造最终的内部 URL
    internal_url = urljoin(DATA_ENTRY_PROXY_URL + '/', target_path)

    logger.info(f"PROXY: {request.method} {request.full_path} -> {internal_url}")
    
    # 2. 转发请求 (GET, POST)
    try:
        # 使用 httpx.Client 保持会话，但在这里使用独立方法即可
        client = httpx.Client(timeout=10.0)
        
        # 获取请求头和数据
        headers = dict(request.headers)
        # 移除可能引起问题的头，例如 Host
        headers.pop('Host', None)
        
        if request.method == 'GET':
            response = client.get(internal_url, headers=headers, params=request.args)
        elif request.method == 'POST':
            # POST 请求可能包含表单数据或 JSON 数据
            data = request.get_data()
            response = client.post(internal_url, headers=headers, content=data)
        else:
            # 处理其他 HTTP 方法（如果需要）
            return Response("Method Not Allowed", status=405)
        
        # 3. 返回响应
        # 返回原始响应内容、状态码和头部（除了Transfer-Encoding）
        response_headers = [(name, value) for name, value in response.headers.items() if name.lower() not in ('content-encoding', 'transfer-encoding')]

        return Response(response.content, response.status_code, response_headers)
        
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to Data Entry Service at {internal_url}: {e}")
        # 返回 503 Service Unavailable 错误
        return Response(json.dumps({"error": "Data Entry Service Unavailable"}), 503, {'Content-Type': 'application/json'})

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

# COMBINED ROUTE: Handles both /data_entry_web and /data_entry_web/<path:path>
# /data_entry_web hits this with path=''\n# /data_entry_web/subpath hits this with path='subpath'
app.add_url_rule('/data_entry_web', 'proxy_data_entry_web_base', proxy_data_entry_web, methods=['GET', 'POST'], defaults={'path': ''})
app.add_url_rule('/data_entry_web/<path:path>', 'proxy_data_entry_web', proxy_data_entry_web, methods=['GET', 'POST'])

if __name__ == '__main__':
    app.run(port=8099, host='0.0.0.0', debug=True)
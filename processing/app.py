import connexion, os, json, yaml, logging, logging.config, time
from datetime import datetime
from connexion import NoContent
from apscheduler.schedulers.background import BackgroundScheduler
# 引入 MongoDB 驱动
from pymongo import MongoClient
# 引入 MySQL 驱动
import mysql.connector 

# --- Configuration Loading and Logging Setup ---
# 假设 app_conf.yml 和 log_conf.yml 位于同一目录

with open('./app_conf.yml','r') as f:
    app_config = yaml.safe_load(f.read())


with open("log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)


logger = logging.getLogger('basicLogger')

# --- MongoDB Initialization ---
MONGO_CONF = app_config['mongodb']
MONGO_URL = f"mongodb://{MONGO_CONF['hostname']}:{MONGO_CONF['port']}/"

# 建立 MongoDB 连接
# 这里使用了一个循环重试机制来等待 MongoDB 启动
MAX_RETRIES = 10
RETRY_DELAY = 5
client = None
db = None

for i in range(MAX_RETRIES):
    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster') 
        db = client[MONGO_CONF['db']]
        stats_collection = db[MONGO_CONF['collection']]
        logger.info(f"Successfully connected to MongoDB at {MONGO_URL} | DB: {MONGO_CONF['db']}")
        break
    except Exception as e:
        logger.warning(f"Connection to MongoDB failed (Attempt {i+1}/{MAX_RETRIES}). Retrying in {RETRY_DELAY} seconds: {e}")
        time.sleep(RETRY_DELAY)
else:
    logger.error("FATAL: Failed to connect to MongoDB after multiple retries. Exiting.")
    # 如果无法连接，则退出或设置一个标志阻止进一步操作
    exit(1)


# --- MySQL Configuration (假设 app_conf.yml 中有此配置) ---
# 确保在 app_conf.yml 中添加了 host, user, password, database 等信息
MYSQL_CONF = app_config.get('mysql', {})
if not MYSQL_CONF:
    logger.error("MySQL configuration not found in app_conf.yml. Cannot proceed with direct DB read.")


def get_latest_stats():
    """
    从 MongoDB 获取最新的统计数据。
    同时初始化所有新增的平均值和总和字段。
    
    初始化最小值需要设置为无限大，最大值需要设置为无限小，以保证第一次计算正确。
    """
    initial_stats = {
        "num_grade_readings": 0, 
        "min_grade_readings": float('inf'), 
        "max_grade_readings": float('-inf'), 
        "sum_grade_readings": 0.0, "avg_grade_readings": 0.0, 
        
        "num_activity_readings": 0, 
        "max_activity_hours": float('-inf'), 
        "min_activity_hours": float('inf'),
        "sum_activity_hours": 0.0, "avg_activity_hours": 0.0, 
        "last_updated": 0 # last_updated 使用毫秒级时间戳
    }
    
    try:
        # 查询最新的一个文档
        latest_doc = stats_collection.find_one(
            {}, 
            sort=[('_id', -1)]
        )
        
        if latest_doc:
            del latest_doc['_id']
            logger.debug(f"Latest stats found. Last updated timestamp (ms): {latest_doc.get('last_updated')}")
            
            # 使用 .get() 确保旧文档结构兼容性，如果字段不存在，则使用初始值
            for key, default_val in initial_stats.items():
                if key not in latest_doc:
                    latest_doc[key] = default_val
            return latest_doc
            
        else:
            logger.warning("No previous stats found in MongoDB. Initializing stats with inf/neg_inf.")
            return initial_stats
            
    except Exception as e:
        logger.error(f"Error accessing MongoDB for latest stats: {e}")
        return initial_stats


def get_events_from_mysql(event_type, start_timestamp_ms):
    """
    直接查询 MySQL 数据库，获取自指定时间戳以来的新事件。
    """
    conn = None
    cursor = None
    events = []
    
    table_name_map = {
        'grade': 'grades',
        'activity': 'activities'
    }
    table_name = table_name_map.get(event_type)

    if not table_name:
        logger.error(f"Invalid event type: {event_type}")
        return []

    TIME_COLUMN_NAME = 'date_created' 
    start_value_for_query = start_timestamp_ms

    query = f"""
        SELECT * FROM {table_name} 
        WHERE {TIME_COLUMN_NAME} >= {start_value_for_query}
        ORDER BY {TIME_COLUMN_NAME} ASC
    """
    
    logger.debug(f"MySQL Query for {event_type}: {query}")

    try:
        # 强制将 password 转换为字符串，以防 YAML 误解析为 int
        password_str = str(MYSQL_CONF.get('password')) 
        
        conn = mysql.connector.connect(
            host=MYSQL_CONF.get('host'),
            user=MYSQL_CONF.get('user'),
            password=password_str, 
            database=MYSQL_CONF.get('database')
        )
        cursor = conn.cursor(dictionary=True) 
        cursor.execute(query)
        events = cursor.fetchall()
        logger.info(f"Successfully fetched {len(events)} new {event_type} events from MySQL.")

        processed_events = []
        for event in events:
            # 查找并处理实际的时间列。
            if 'timestamp' in event and isinstance(event['timestamp'], datetime):
                event['timestamp'] = event['timestamp'].isoformat()
            
            processed_events.append(event)
            
        return processed_events

    except mysql.connector.Error as err:
        logger.error(f"MySQL Error fetching {event_type} data: {err}")
        return []

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


def calculate_and_store_stats(stats, content_activity, content_grade, end):
    """
    计算新的统计数据（包括平均值）并将其存储到 MongoDB。
    
    此函数增加了逻辑来修复旧版本中 min 值被错误存储为 0.0 的历史数据腐败问题。
    """
    logger.debug(f"Calculating stats based on {len(content_grade)} raw grade records and {len(content_activity)} raw activity records.")
    
    # 历史记录中的最小/大值和计数
    hist_min_grade = stats.get('min_grade_readings', float('inf'))
    hist_max_grade = stats.get('max_grade_readings', float('-inf'))
    hist_num_grade = stats.get('num_grade_readings', 0)
    
    hist_min_activity = stats.get('min_activity_hours', float('inf'))
    hist_max_activity = stats.get('max_activity_hours', float('-inf'))
    hist_num_activity = stats.get('num_activity_readings', 0)

    # 1. 初始化新的统计数据结构
    new_stats = {
        "last_updated": end, 
        # 获取上次的累积总和和计数
        "num_grade_readings": hist_num_grade,
        "sum_grade_readings": stats.get('sum_grade_readings', 0.0),
        "min_grade_readings": hist_min_grade,
        "max_grade_readings": hist_max_grade,
        
        "num_activity_readings": hist_num_activity,
        "sum_activity_hours": stats.get('sum_activity_hours', 0.0),
        "min_activity_hours": hist_min_activity,
        "max_activity_hours": hist_max_activity,
    }
    
    # --- 2. 计算分数统计 (Grade Stats) ---
    list_grade_readings = [item.get("score") for item in content_grade if isinstance(item.get("score"), (int, float))]
    
    # 修复逻辑：检查历史最小分是否为腐败的 0.0
    # 如果历史总数大于 0，且历史最小分是 0.0，且新数据中没有 0.0，则临时重置为 inf
    if hist_num_grade > 0 and hist_min_grade == 0.0 and 0.0 not in list_grade_readings:
        new_stats["min_grade_readings"] = float('inf')
        logger.warning("Historical min_grade_readings was 0.0 but no 0.0 in new data. Resetting min calculation base to inf.")
    
    # 更新总数和总和
    new_stats["num_grade_readings"] += len(list_grade_readings)
    new_grade_sum_increment = sum(list_grade_readings)
    new_stats["sum_grade_readings"] += new_grade_sum_increment

    # 更新 Min/Max
    if list_grade_readings:
        # 这里的 new_stats["min_grade_readings"] 现在要么是正确的历史值，要么是 inf (如果被重置了)
        new_stats["min_grade_readings"] = min(new_stats["min_grade_readings"], min(list_grade_readings))
        new_stats["max_grade_readings"] = max(new_stats["max_grade_readings"], max(list_grade_readings))

    # 计算平均值
    if new_stats["num_grade_readings"] > 0:
        new_stats["avg_grade_readings"] = new_stats["sum_grade_readings"] / new_stats["num_grade_readings"]
    else:
        new_stats["avg_grade_readings"] = 0.0

    # --- 3. 计算活动统计 (Activity Stats) ---
    list_activity_readings = [item.get("hours") for item in content_activity if isinstance(item.get("hours"), (int, float))]
    
    # 修复逻辑：检查历史最小活动小时数是否为腐败的 0.0
    if hist_num_activity > 0 and hist_min_activity == 0.0 and 0.0 not in list_activity_readings:
        new_stats["min_activity_hours"] = float('inf')
        logger.warning("Historical min_activity_hours was 0.0 but no 0.0 in new data. Resetting min calculation base to inf.")
        
    # 更新总数和总和
    new_stats["num_activity_readings"] += len(list_activity_readings)
    new_activity_sum_increment = sum(list_activity_readings)
    new_stats["sum_activity_hours"] += new_activity_sum_increment

    # 更新 Min/Max
    if list_activity_readings:
        new_stats["min_activity_hours"] = min(new_stats["min_activity_hours"], min(list_activity_readings))
        new_stats["max_activity_hours"] = max(new_stats["max_activity_hours"], max(list_activity_readings))

    # 计算平均值
    if new_stats["num_activity_readings"] > 0:
        new_stats["avg_activity_hours"] = new_stats["sum_activity_hours"] / new_stats["num_activity_readings"]
    else:
        new_stats["avg_activity_hours"] = 0.0

    # --- 4. 最终数据结构和存储 ---
    # 确保 Min/Max 在没有数据时显示为 0.0
    final_min_grade = new_stats["min_grade_readings"] if new_stats["min_grade_readings"] != float('inf') else 0.0
    final_max_grade = new_stats["max_grade_readings"] if new_stats["max_grade_readings"] != float('-inf') else 0.0
    final_min_activity = new_stats["min_activity_hours"] if new_stats["min_activity_hours"] != float('inf') else 0.0
    final_max_activity = new_stats["max_activity_hours"] if new_stats["max_activity_hours"] != float('-inf') else 0.0

    final_stats_doc = {
        "num_grade_readings": new_stats["num_grade_readings"],
        "min_grade_readings": final_min_grade,
        "max_grade_readings": final_max_grade,
        "avg_grade_readings": round(new_stats["avg_grade_readings"], 2), # 四舍五入到两位小数
        
        "num_activity_readings": new_stats["num_activity_readings"],
        "min_activity_hours": final_min_activity,
        "max_activity_hours": final_max_activity,
        "avg_activity_hours": round(new_stats["avg_activity_hours"], 2), # 四舍五入到两位小数
        
        # 存储运行总和和检查点时间
        "sum_grade_readings": new_stats["sum_grade_readings"],
        "sum_activity_hours": new_stats["sum_activity_hours"],
        "last_updated": new_stats["last_updated"],
    }

    try:
        stats_collection.insert_one(final_stats_doc)
        logger.debug("New statistics stored to MongoDB: %s", final_stats_doc)
    except Exception as e:
        logger.error(f"Failed to write new stats to MongoDB: {e}")

    # 返回给日志记录，不包含内部的总和字段
    return {k: v for k, v in final_stats_doc.items() if not k.startswith('sum_')}


def get_stats():
    """
    API Endpoint: 返回最新的统计数据。
    """
    logger.info("Request received for latest statistics.")
    
    latest_stats = get_latest_stats()

    # 如果 last_updated 还是 0，说明还没有任何数据被处理过，返回 200，内容为初始化的 0 值
    if latest_stats["last_updated"] == 0:
        logger.warning("Statistics collection is empty.")
        # 返回 200，只返回面向用户/API 的字段
        return {k: v for k, v in latest_stats.items() if not k.startswith('sum_')}, 200

    # 过滤掉内部的 sum_ 字段，只返回 API 需要的字段
    api_response = {k: v for k, v in latest_stats.items() if not k.startswith('sum_')}
    
    # 确保在 API 响应中，如果 min 值是 inf/neg_inf，显示为 0.0 (以防 get_latest_stats 返回了 inf/neg_inf)
    if api_response.get("min_grade_readings") == float('inf'):
        api_response["min_grade_readings"] = 0.0
    if api_response.get("min_activity_hours") == float('inf'):
        api_response["min_activity_hours"] = 0.0
        
    if api_response.get("max_grade_readings") == float('-inf'):
        api_response["max_grade_readings"] = 0.0
    if api_response.get("max_activity_hours") == float('-inf'):
        api_response["max_activity_hours"] = 0.0

    logger.debug("Returning latest stats: %s", api_response)
    logger.info("The request has been completed.")
    return api_response, 200
    

def populate_stats():
    """
    调度器任务：从 MySQL 获取新数据，计算统计并存储。
    """
    logger.info("Scheduler started populating stats!")
    
    try:
        # 1. 获取上次处理的最新时间戳 (毫秒)
        stats = get_latest_stats()
        most_recent_event_ts = stats["last_updated"] # 毫秒级时间戳作为起点

        # 2. 从 MySQL 获取新数据
        content_grade = get_events_from_mysql('grade', most_recent_event_ts)
        content_activity = get_events_from_mysql('activity', most_recent_event_ts)
        
        logger.debug(f"Scheduler fetched: {len(content_grade)} new grade readings, {len(content_activity)} new activity readings.")


        # 3. 设置新的结束时间戳 (毫秒)
        end = int(time.time() * 1000) 

        # 4. 只有在接收到新数据时才进行计算和存储
        if not content_activity and not content_grade and end == most_recent_event_ts:
            logger.info("No new readings found and no time change since last update. Skipping calculation.")
            return
            
        calculate_and_store_stats(stats, content_activity, content_grade, end)
        
    except Exception as e:
        logger.error(f"FATAL: Unhandled exception during populate_stats execution: {e}", exc_info=True)
    

def init_scheduler():
    """
    初始化并启动后台调度器。
    """
    # 1. 检查配置是否存在
    if 'scheduler' not in app_config or 'interval' not in app_config['scheduler']:
        logger.error("Scheduler configuration missing 'interval' in app_conf.yml. Scheduler not started.")
        return
        
    interval = app_config['scheduler']['interval']
    
    try:
        sched = BackgroundScheduler(daemon=True)
        sched.add_job(populate_stats, 'interval', seconds=interval)
        sched.start()
        logger.info(f"Scheduler initialized and started to run every {interval} seconds.")
    except Exception as e:
        # 如果启动失败，打印详细的错误信息
        logger.error(f"Failed to start scheduler: {e}")
        

# --- Main App Execution ---
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("OpenAPI_processing.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler() 
    app.run(port=8100, host='0.0.0.0') 

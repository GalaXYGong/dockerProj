import connexion,os,json,yaml,logging, logging.config,time
from datetime import datetime
from connexion import NoContent
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
import functools
from models import GradeReading, ActivityReading
from dateutil import parser

with open('./app_conf.yml','r') as f:
    app_config = yaml.safe_load(f.read())

user = app_config["datastore"]['user']
password = app_config["datastore"]['password']
hostname = app_config["datastore"]['hostname']
port = app_config["datastore"]['port']
db = app_config["datastore"]['db']

ENGINE=create_engine(f"mysql+mysqlconnector://{user}:{password}@{hostname}:{port}/{db}",echo=True)
def make_session():
    return sessionmaker(bind=ENGINE)()

with open("log_conf.yml", "r") as f:
  LOG_CONFIG = yaml.safe_load(f.read())
  logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

# Stored event snow_report with a trace id of 123456789
def logging_debug(event_name,trace_id):
    msg = f"Stored event {event_name} with a trace id of {trace_id}"
    logger.debug(msg)


# def user_db_session(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         session = make_session()
#         try:
#             return func(session, *args, **kwargs)
#         finally:
#             session.close()
#     return wrapper

def user_db_session(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with make_session() as session:
            return func(session, *args, **kwargs)
    return wrapper
# MAX_BATCH_EVENTS = 5
# GRADES_FILE = "grades.json"
# ACTIVITIES_FILE = "activities.json"


@user_db_session
def report_grade(session,body):
    event_name = "grade"
    seconds_since_epoch = time.time()
    ms_since_epoch = int(seconds_since_epoch * 1000)
    timestamp_obj = parser.isoparse(body['timestamp'])
    reporting_date = datetime.strptime(body['reporting_date'], "%Y-%m-%d")
    grade = GradeReading(
        school_id = body["school_id"],
        school_name = body['school_name'],
        reporting_date = reporting_date,
        student_id = body['student_id'],
        student_name = body['student_name'],
        course = body['course'],
        assignment = body['assignment'],
        score = body['score'],
        timestamp = timestamp_obj,
        date_created = ms_since_epoch,
        trace_id = body['trace_id']
    )
    session.add(grade)
    session.commit()
    logging_debug(event_name,body['trace_id'])
    # print("Successfully committed grade to database.")
    return NoContent, 201

@user_db_session
def get_grades(session,start_timestamp,end_timestamp):
    start = start_timestamp
    end = end_timestamp
    statement = select(GradeReading).where(GradeReading.date_created >= start).where(GradeReading.date_created < end)
    # results = [ result.to_dict() for result in session.execute(statement).scalars().all()]
    results = []
    for result in session.execute(statement).scalars().all():
        results.append(result.to_dict())
        
    logger.debug(f"Found {len(results)} grade readings (start: {start}, end {end}")
    return results,200
# http://localhost:8090/store/grade?start_timestamp=1759690422296&end_timestamp=1759690433310

@user_db_session
def report_activity(session,body):
    event_name = "activity"
    seconds_since_epoch = time.time()
    ms_since_epoch = int(seconds_since_epoch * 1000)
    timestamp_obj = parser.isoparse(body['timestamp'])
    reporting_date = datetime.strptime(body['reporting_date'], "%Y-%m-%d")
    activity = ActivityReading(
        school_id = body["school_id"],
        school_name = body['school_name'],
        reporting_date = reporting_date,
        student_id = body['student_id'],
        student_name = body['student_name'],
        activity_type = body['activity_type'],
        activity_name = body['activity_name'],
        hours = body['hours'],
        timestamp = timestamp_obj,
        date_created = ms_since_epoch,
        trace_id = body['trace_id']
    )
    session.add(activity)
    session.commit()
    logging_debug(event_name,body['trace_id'])
    # print("Successfully committed activity to database.")
    return NoContent, 201

@user_db_session
def get_activities(session,start_timestamp,end_timestamp):
    # return {"status": "Route is working!", "start": start_timestamp,"end":end_timestamp}
    start = start_timestamp
    end = end_timestamp
    statement = select(ActivityReading).where(ActivityReading.date_created >= start).where(ActivityReading.date_created < end)
    # results = [ result.to_dict() for result in session.execute(statement).scalars().all()]
    results = []
    for result in session.execute(statement).scalars().all():
        results.append(result.to_dict())
        
    logger.debug(f"Found {len(results)} activity readings (start: {start}, end {end}")
    return results,200
# http://localhost:8090/store/activity?start_timestamp=1759689552678&end_timestamp=1759690433310

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api('bcit-142-student_reports_storage_api-1.0.0-swagger.yaml',strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8090,host='0.0.0.0')

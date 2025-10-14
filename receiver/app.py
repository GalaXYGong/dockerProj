import connexion,os,json,httpx,yaml,logging, logging.config
from datetime import datetime
from connexion import NoContent
import uuid

with open('./app_conf.yml','r') as f:
    app_config = yaml.safe_load(f.read())
with open("log_conf.yml", "r") as f:
  LOG_CONFIG = yaml.safe_load(f.read())
  logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

def logging_info_receive(event_name,trace_id):
    msg = f"Received event {event_name} with a trace id of {trace_id}"
    # Received event snow_report with a trace id of 123456789
    logger.info(msg)
def logging_info_response(event_name,trace_id,status_code):
    # Response for event snow_report (id: 123456789) has status 201
    msg = f"Response for {event_name} (id: {trace_id}) has status {status_code}"
    logger.info(msg)

# MAX_BATCH_EVENTS = 5
GRADE_URL = app_config["grade"]["url"]
ACTIVITY_URL = app_config["activity"]["url"]

# GRADES_FILE = "grades.json"
# ACTIVITIES_FILE = "activities.json"


def report_grades(body):
    event_name = "grade_report"
    #read body
    raw_reports = body['reports']
    # loop all of grades under report batch
    trace_id = str(uuid.uuid4())
    logging_info_receive(event_name,trace_id)
    # print(f"Trace id: {trace_id}")
    for report in raw_reports:
        #create a new dictionary to store the data
        data = {
            "school_id": body["school_id"],
            "school_name": body["school_name"],
            "reporting_date": body["reporting_date"],
            "student_id": report["student_id"],
            "student_name": report["student_name"],
            "course": report["course"],
            "assignment": report["assignment"],
            "score": report["score"],
            "timestamp": report["timestamp"],
            "trace_id": trace_id
        }
        #print(data)
        response = httpx.post(GRADE_URL, json=data)
        status_code = response.status_code
        logging_info_response(event_name,trace_id,status_code)
    return NoContent, status_code

def report_activities(body):
    event_name = "activity_report"
    #read body
    raw_reports = body['reports']
    # loop all of grades under report batch
    trace_id = str(uuid.uuid4())
    logging_info_receive(event_name,trace_id)
    for report in raw_reports:
        #create a new dictionary to store the data
        data = {
            "school_id": body["school_id"],
            "school_name": body["school_name"],
            "reporting_date": body["reporting_date"],
            "student_id": report["student_id"],
            "student_name": report["student_name"],
            "activity_type": report["activity_type"],
            "activity_name": report["activity_name"],
            "hours": report["hours"],
            "timestamp": report["timestamp"],
            "trace_id": trace_id
        }
        # print(data)
        response = httpx.post(ACTIVITY_URL, json=data)
        status_code = response.status_code
        logging_info_response(event_name,trace_id,status_code)
    return NoContent, status_code


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("bcit-142-student_data_collection_system-1.0.0-swagger.yaml",strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)



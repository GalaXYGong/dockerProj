import connexion,os,json,httpx
from datetime import datetime
from connexion import NoContent



MAX_BATCH_EVENTS = 5
GRADES_FILE = "grades.json"
ACTIVITIES_FILE = "activities.json"


def report_grades(body):
    #create a new dictionary to store the data
    report_summary = {}
    #read body
    raw_reports = body['reports']
    score = 0
    num_score_readings = len(raw_reports)
    for report in raw_reports:
        score_in_question = report['score']
        score += score_in_question
    # handle the case of no score readings
    if num_score_readings == 0:
        report_summary["grade_average"] = 0
        report_summary["num_score_readings"] = 0
        report_summary['received_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        return NoContent, 201
    # calculate average
    report_summary["grade_average"] = score/num_score_readings
    report_summary["num_score_readings"] = num_score_readings
    
    # timestamp
    received_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    report_summary['received_timestamp'] = received_timestamp 
    # read Json File
    new=False
    if not os.path.exists(GRADES_FILE):
        grade_dict={}
        new=True
        print("it is the first batch")
    else:
        with open(GRADES_FILE,'r',encoding='utf-8') as f:
            grade_dict = json.load(f)
            print("it is not the first batch")
            # try:
            #     grade_dict = json.load(f)
            #     print("it is not the first batch")
            # except json.decoder.JSONDecodeError:
            #     new=True
            #     #os.remove(GRADES_FILE)
            #     grade_dict={}
            #     print(f"deleting wrong json file {GRADES_FILE}")
            
    if new:
        # counter: num_grade_batches
        grade_dict["num_grade_batches"] = 1
        # last five batch collection
        grade_dict['recent_batch_data'] = [report_summary]
    else:
        # counter: num_grade_batches
        grade_dict["num_grade_batches"] += 1
        # last five batch collection
        grade_dict['recent_batch_data'].insert(0,report_summary)
        if len(grade_dict['recent_batch_data']) > MAX_BATCH_EVENTS:
            grade_dict['recent_batch_data'] = grade_dict['recent_batch_data'][0:MAX_BATCH_EVENTS]
    with open(GRADES_FILE,"w") as f:
       json.dump(grade_dict,f,indent=4)
    return NoContent, 201


def report_activities(body):
    #create a new dictionary to store the data
    activity_report_summary = {}
    #read body
    raw_reports = body['reports']
    total_hours = 0
    num_activity_readings = len(raw_reports)
    for report in raw_reports:
        hours_in_question = report['hours']
        total_hours += hours_in_question
    # handle the case of no score readings
    if num_activity_readings == 0:
        activity_report_summary["hours_average"] = 0
        activity_report_summary["num_score_readings"] = 0
        activity_report_summary['received_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        return NoContent, 201
    # calculate average
    activity_report_summary["hours_average"] = total_hours/num_activity_readings
    activity_report_summary["num_activity_readings"] = num_activity_readings
    
    # timestamp
    received_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    activity_report_summary['received_timestamp'] = received_timestamp 
    #print(activity_report_summary)
    # read Json File
    new=False
    if not os.path.exists(ACTIVITIES_FILE):
        activity_dict={}
        new=True
        print("it is the first batch")
    else:
        with open(ACTIVITIES_FILE,'r',encoding='utf-8') as f:
            activity_dict = json.load(f)
            print("it is not the first batch")
            # try:
            #     activity_dict = json.load(f)
            #     print("it is not the first batch")
            # except json.decoder.JSONDecodeError:
            #     new=True
            #     os.remove(ACTIVITIES_FILE)
            #     activity_dict={}
            #     print(f"deleting wrong json file {ACTIVITIES_FILE}")
            
    if new:
        # counter: num_activity_batches
        activity_dict["num_activity_batches"] = 1
        # last five batch collection
        activity_dict['recent_batch_data'] = [activity_report_summary]
    else:
        # counter: num_activity_batches
        activity_dict["num_activity_batches"] += 1
        # last five batch collection
        activity_dict['recent_batch_data'].insert(0,activity_report_summary)
        if len(activity_dict['recent_batch_data']) > MAX_BATCH_EVENTS:
            activity_dict['recent_batch_data'] = activity_dict['recent_batch_data'][0:MAX_BATCH_EVENTS]
    with open(ACTIVITIES_FILE,"w") as f:
       json.dump(activity_dict,f,indent=4)
    return NoContent, 201

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("bcit-142-student_data_collection_system-1.0.0-swagger.yaml",strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)

"""
{
  "school_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "school_name": "BCIT",
  "reporting_date": "2016-08-29T09:12:33.001Z",
  "reports": [
    {
      "student_id": "A01384150",
      "student_name": "Xinyu Gong",
      "course": "ACIT3855 Service Based Architecture",
      "assignment": "string",
      "score": "string",
      "timestamp": "2016-08-29T09:12:33.001Z"
    }
  ]
}
"""


"""
{
  "school_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
  "school_name": "BCIT",
  "reporting_date": "2016-08-29T09:12:33.001Z",
  "reports": [
    {
      "student_id": "A01384150",
      "student_name": "Xinyu Gong",
      "activity_type": "volunteering",
      "activity_name": "Digital Coffee",
      "hours": 0.5,
      "timestamp": "2016-08-29T09:12:33.001Z"
    }
  ]
}
"""
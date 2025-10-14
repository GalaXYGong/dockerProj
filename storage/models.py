from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String, DateTime, func, Float,BigInteger

class Base(DeclarativeBase):
    pass

class GradeReading(Base):
    __tablename__ = "grades"
    id = mapped_column(Integer, primary_key=True)
    school_id = mapped_column(String(250),nullable=False)
    school_name = mapped_column(String(250),nullable=False)
    reporting_date= mapped_column(DateTime,nullable=False)
    student_id = mapped_column(String(250), nullable=False)
    student_name = mapped_column(String(250), nullable=False)
    course= mapped_column(String(250), nullable=False)
    assignment = mapped_column(String(250), nullable=False)
    score = mapped_column(Float, nullable=False)
    timestamp = mapped_column(DateTime,nullable=False)
    # date_created = mapped_column(BigInteger, server_default=func.round(func.unix_timestamp(func.now()) * 1000))
    date_created = mapped_column(BigInteger, nullable=False)
    trace_id = mapped_column(String(250),nullable=False)
    def to_dict(self):
        return {
            'id': self.id,
            'school_id': self.school_id,
            'school_name': self.school_name,
            'reporting_date': self.reporting_date,
            'student_id': self.student_id,
            'student_name': self.student_name,
            'course': self.course,
            'assignment': self.assignment,
            'score': self.score,
            'timestamp': self.timestamp,
            'date_created': self.date_created,
            'trace_id': self.trace_id
        }



class ActivityReading(Base):
    __tablename__ = "activities" # Changed table name to plural for convention
    id = mapped_column(Integer, primary_key=True)
    school_id = mapped_column(String(250), nullable=False)
    school_name = mapped_column(String(250), nullable=False)
    reporting_date = mapped_column(DateTime, nullable=False)
    student_id = mapped_column(String(250), nullable=False)
    student_name = mapped_column(String(250), nullable=False)
    activity_type = mapped_column(String(250), nullable=False)
    activity_name = mapped_column(String(250), nullable=False)
    hours = mapped_column(Float, nullable=False)
    timestamp = mapped_column(DateTime, nullable=False)
    # date_created= mapped_column(DateTime, server_default=func.now())
    date_created = mapped_column(BigInteger, nullable=False)
    trace_id = mapped_column(String(250),nullable=False)
    def to_dict(self):
        return {
            'id': self.id,
            'school_id': self.school_id,
            'school_name': self.school_name,
            'reporting_date': self.reporting_date,
            'student_id': self.student_id,
            'student_name': self.student_name,
            'activity_type': self.activity_type,
            'activity_name': self.activity_name,
            'hours': self.hours,
            'timestamp': self.timestamp,
            'date_created': self.date_created,
            'trace_id': self.trace_id
        }
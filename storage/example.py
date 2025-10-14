from sqlalchemy import create_engine, Integer, String, DateTime, Float, func
from sqlalchemy.orm import DeclarativeBase, mapped_column

# Define the database connection string.
# Using a simple SQLite database file for this example.
# Replace with your actual database URL (e.g., 'postgresql://user:password@host/dbname')
DATABASE_URL = "sqlite:///student_data.db"
engine = create_engine(DATABASE_URL)

# Define the base class for declarative models
class Base(DeclarativeBase):
    pass

# --- Your models go here ---
# Re-defining the models for completeness in this file
class GradeReading(Base):
    __tablename__ = "grades"  # Changed table name to plural for convention
    id = mapped_column(Integer, primary_key=True)
    school_id = mapped_column(String(250), nullable=False)
    school_name = mapped_column(String(250), nullable=False)
    student_id = mapped_column(String(250), nullable=False)
    student_name = mapped_column(String(250), nullable=False)
    course = mapped_column(String(250), nullable=False)
    assignment = mapped_column(String(250), nullable=False)
    score = mapped_column(Float, nullable=False)
    reporting_timestamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())
    
class ActivityReading(Base):
    __tablename__ = "activities" # Changed table name to plural for convention
    id = mapped_column(Integer, primary_key=True)
    school_id = mapped_column(String(250), nullable=False)
    school_name = mapped_column(String(250), nullable=False)
    student_id = mapped_column(String(250), nullable=False)
    student_name = mapped_column(String(250), nullable=False)
    activity_type = mapped_column(String(250), nullable=False)
    activity_name = mapped_column(String(250), nullable=False)
    hours = mapped_column(Float, nullable=False)
    reporting_timestamp = mapped_column(DateTime, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())
# --- End of models ---


def create_all_tables():
    """Creates all tables defined in the Base.metadata."""
    print("Creating all tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully!")

def drop_all_tables():
    """Drops all tables defined in the Base.metadata."""
    print("Dropping all tables...")
    Base.metadata.drop_all(engine)
    print("Tables dropped successfully!")

if __name__ == "__main__":
    import sys
    
    # Simple command-line argument parsing
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'drop':
        # To drop tables, run: python manage_tables.py drop
        drop_all_tables()
    else:
        # By default, create all tables.
        # To create tables, run: python manage_tables.py
        create_all_tables()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from models import Base, GradeReading
import yaml
with open('./app_conf.yml','r') as f:
    app_config = yaml.safe_load(f.read())

user = app_config["datastore"]['user']
password = app_config["datastore"]['password']
hostname = app_config["datastore"]['hostname']
port = app_config["datastore"]['port']
db = app_config["datastore"]['db']

ENGINE=create_engine(f"mysql+mysqlconnector://{user}:{password}@{hostname}:{port}/{db}",echo=True)
Base.metadata.drop_all(ENGINE)

def drop_all_tables():
    print("Dropping tables...")
    Base.metadata.drop_all(ENGINE)
    print("Tables dropped successfully!")

if __name__ == "__main__":
    drop_all_tables()
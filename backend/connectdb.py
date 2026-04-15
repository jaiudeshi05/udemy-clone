from dotenv import load_dotenv
import os
from sqlmodel import SQLModel, create_engine

load_dotenv()

db_url=os.getenv("POSTGRES_DATABASE_URL")

engine = create_engine(db_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    print("Database and tables created.")
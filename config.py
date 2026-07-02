from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/work_hours_db")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")

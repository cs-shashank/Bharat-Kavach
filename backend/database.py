from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# SQLite for local production-grade development
SQLALCHEMY_DATABASE_URL = "sqlite:///./bharat_kavach.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class CaseReport(Base):
    __tablename__ = "case_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    transcript = Column(String)
    risk_score = Column(Float)
    stage = Column(String)
    verdict = Column(String)
    legal_citations = Column(JSON)
    interventions = Column(JSON)
    city = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class ForensicDocument(Base):
    __tablename__ = "forensic_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    verdict = Column(String)
    confidence = Column(Float)
    signals = Column(JSON)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Startup migration guard: add city column if it doesn't exist yet
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE case_reports ADD COLUMN city VARCHAR"))
        conn.commit()
except Exception:
    pass  # Column already exists

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

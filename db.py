import os
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# =========================
# BASE
# =========================
Base = declarative_base()


# =========================
# MODELS
# =========================
class CHO(Base):
    __tablename__ = "chos"

    id = Column(Integer, primary_key=True)
    custom_id = Column(String, unique=True)
    title = Column(String)


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True)
    custom_id = Column(String, unique=True)
    title = Column(String)
    text = Column(Text)
    file_path = Column(String)


# =========================
# PATH SETUP ✅ UPDATED
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Use memory_files instead of memories
MEMORY_DIR = os.path.join(BASE_DIR, "memory_files")

# ✅ Ensure folder exists
os.makedirs(MEMORY_DIR, exist_ok=True)

DB_PATH = os.path.join(MEMORY_DIR, "000_cordhisk.db")


# =========================
# ENGINE
# =========================
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


# =========================
# CREATE TABLES
# =========================
Base.metadata.create_all(engine)


# =========================
# SESSION
# =========================
Session = sessionmaker(bind=engine)
session = Session()
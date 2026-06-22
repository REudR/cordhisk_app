from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

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

engine = create_engine("sqlite:///cordhisk.db")
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
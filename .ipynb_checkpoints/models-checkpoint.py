from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class CHO(Base):
    __tablename__ = "chos"

    id = Column(Integer, primary_key=True)
    title = Column(String)

    memories = relationship("Memory", back_populates="cho")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    text = Column(Text)

    cho_id = Column(Integer, ForeignKey("chos.id"))
    cho = relationship("CHO", back_populates="memories")


class MetadataRecord(Base):
    __tablename__ = "metadata"

    id = Column(Integer, primary_key=True)
    memory_id = Column(Integer, ForeignKey("memories.id"))
    cho_id = Column(Integer, ForeignKey("chos.id"))

    data = Column(Text)
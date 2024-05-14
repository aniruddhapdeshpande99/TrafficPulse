# coding: utf-8
from sqlalchemy import Column, DateTime, Float, Index, Integer, LargeBinary, String, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Image(Base):
    __tablename__ = 'images'
    __table_args__ = (
        Index('ix_images_camera_id_timestamp', 'camera_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('images_id_seq'::regclass)"))
    timestamp = Column(DateTime, nullable=False)
    image = Column(LargeBinary, nullable=False)
    image_url = Column(String(200), nullable=False)
    latitude = Column(Float(53), nullable=False)
    longitude = Column(Float(53), nullable=False)
    camera_id = Column(String(50), nullable=False)
    height = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    md5 = Column(String(32), nullable=False, index=True)
    num_vehicles = Column(Integer)

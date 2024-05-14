from datetime import datetime, timedelta
from orm import Image as ImageTable
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, and_
import os
import json


def generate_datetimes(start_datetime, end_datetime, frequency_seconds):
    """
    Generate a list of datetimes between start and end, separated by the given
    frequency in seconds.
    """
    current_datetime = start_datetime
    datetimes = []

    while current_datetime <= end_datetime:
        datetimes.append(current_datetime)
        current_datetime += timedelta(seconds=frequency_seconds)

    return datetimes


def get_db_session():
    """
    Create a new db session
    """
    db_engine = create_engine(os.getenv("DB_CONN_STR"))
    db_engine.connect()

    session_maker = sessionmaker(bind=db_engine)
    db_session = session_maker()

    return db_session

def get_new_md5(md5_hashes, db_session):
    existing_hashes = (
        db_session
            .query(ImageTable.md5)
            .filter(ImageTable.md5.in_(md5_hashes))
            .all()
    )
    # Extracts and returns a list of existing MD5 hashes
    return set(md5_hashes) - {md5[0] for md5 in existing_hashes}


def get_latest_camera_data(db_session):
    latest_images_query = (
        db_session.query(
            ImageTable.camera_id,
            func.max(ImageTable.timestamp).label('latest_timestamp')
        )
        .group_by(ImageTable.camera_id)
        .subquery()
    )

    latest_images = (
        db_session.query(ImageTable)
        .join(
            latest_images_query,
            (ImageTable.camera_id == latest_images_query.c.camera_id) &
            (ImageTable.timestamp == latest_images_query.c.latest_timestamp)
        )
        .order_by(ImageTable.camera_id)
    ).all()

    return [
        {
            "camera_id": img.camera_id,
            "timestamp": img.timestamp,
            "image": img.image,
            "image_url": img.image_url,
            "latitude": img.latitude,
            "longitude": img.longitude,
        }
        for img in latest_images
    ]

def get_selected_time_camera_data(db_session, selected_time):
    selected_images = (
        db_session.query(
            ImageTable
        ).filter(ImageTable.timestamp == selected_time)
    ).all()

    return [
        {
            "camera_id": img.camera_id,
            "timestamp": img.timestamp,
            "image": img.image,
            "image_url": img.image_url,
            "latitude": img.latitude,
            "longitude": img.longitude,
            "num_vehicles": img.num_vehicles,
        }
        for img in selected_images
    ]


def get_all_timestamps(db_session):
    START_TIMESTAMP = datetime(2023, 11, 7, 0, 0, 0)
    END_TIMESTAMP = datetime(2023, 11, 7, 2, 0, 0)

    timestamps = (
        db_session.query(ImageTable.timestamp)
        .filter(and_(
            ImageTable.timestamp >= START_TIMESTAMP,
            ImageTable.timestamp <= END_TIMESTAMP,
        ))
        .distinct().order_by(ImageTable.timestamp)
        .all()
    )

    # Extract the timestamps from the result
    timestamps_list = [
        timestamp[0].strftime("%Y-%m-%d %H:%M:%S")
        for timestamp in timestamps
    ]

    return timestamps_list


def fetch_unfilled_vehicles_data(db_session, num_points, latest=False):
    """
    Get `num_points` number of data points from the database which have the
    column `num_vehicles` empty. If latest=True then we fetch the latest data
    inserted in the database, else the most historic data.
    """
    query = (
        db_session
            .query(ImageTable.id, ImageTable.image)
            .filter(ImageTable.num_vehicles.is_(None))
    )
    if latest:
        query = query.order_by(ImageTable.id.desc())
    query = query.limit(num_points)

    raw_data = query.all()
    return raw_data


def return_loc(latitudes, longitudes):
    with open('./metadata/lat_long_place.json', 'r') as data_file:
        json_data = data_file.read()

    data = json.loads(json_data)

    locations = []
    for i in range(0, len(latitudes)):
        curr_lat = latitudes[i]
        curr_long = longitudes[i]

        for entry in data:
            if entry['latitude'] == curr_lat and entry['longitude'] == curr_long:
                locations.append(entry['Address'])

    return locations


def return_day_timestamp(timestamp):
    date_format = '%Y-%m-%d %H:%M:%S'
    selected_time_obj = datetime.strptime(timestamp, date_format)
    return selected_time_obj.date()

def convert_date(dt_timestamp):
    return dt_timestamp.strftime("%d %B %Y")
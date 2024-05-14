from datetime import datetime, timedelta
from orm import Image as ImageTable
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, and_, distinct
import os
import json
from pytz import timezone


SGP_TZ = timezone('Asia/Singapore')
UTC_TZ = timezone('UTC')


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
            "timestamp": UTC_TZ.localize(img.timestamp).astimezone(SGP_TZ),
            "image": img.image,
            "image_url": img.image_url,
            "latitude": img.latitude,
            "longitude": img.longitude,
        }
        for img in latest_images
    ]


def get_camera_metadata(db_session):
    camera_data = db_session.query(
        distinct(ImageTable.camera_id),
        ImageTable.latitude, ImageTable.longitude
    ).all()

    return {
        cd[0]: {
            "latitude": cd[1],
            "longitude": cd[2],
        }
        for cd in camera_data
    }


def get_selected_time_camera_data(db_session, selected_time):
    """
    Here `selected_time` is in Singapore Time.
    """
    selected_time_utc = SGP_TZ.localize(selected_time).astimezone(UTC_TZ)
    selected_images = (
        db_session.query(
            ImageTable
        ).filter(and_(
            ImageTable.timestamp == selected_time_utc,
            ImageTable.num_vehicles != None,
        ))
    ).all()

    return [
        {
            "camera_id": img.camera_id,
            "timestamp": UTC_TZ.localize(img.timestamp).astimezone(SGP_TZ),
            "image": img.image,
            "image_url": img.image_url,
            "latitude": img.latitude,
            "longitude": img.longitude,
            "num_vehicles": img.num_vehicles,
        }
        for img in selected_images
    ]


def get_all_timestamps(db_session):
    START_TIMESTAMP = SGP_TZ.localize(datetime(2023, 11, 7, 0, 0, 0))
    END_TIMESTAMP = SGP_TZ.localize(datetime(2023, 11, 10, 23, 59, 59))

    start_time_utc = START_TIMESTAMP.astimezone(UTC_TZ)
    end_time_utc = END_TIMESTAMP.astimezone(UTC_TZ)

    timestamps = (
        db_session.query(ImageTable.timestamp)
        .filter(and_(
            ImageTable.timestamp >= start_time_utc,
            ImageTable.timestamp <= end_time_utc,
            ImageTable.num_vehicles != None
        ))
        .distinct().order_by(ImageTable.timestamp)
        .all()
    )

    # Extract the timestamps from the result
    timestamps_list = [
        UTC_TZ.localize(timestamp[0]).astimezone(SGP_TZ).strftime("%Y-%m-%d %H:%M:%S")
        for timestamp in timestamps
    ]

    return timestamps_list

def update_live_timestamps(db_session, count):
    START_TIMESTAMP = SGP_TZ.localize(datetime(2023, 11, 7, 0, 0, 0))
    END_TIMESTAMP = SGP_TZ.localize(datetime(2023, 11, 11, 0, 0, 0)) + timedelta(minutes=count*5)

    start_time_utc = START_TIMESTAMP.astimezone(UTC_TZ)
    end_time_utc = END_TIMESTAMP.astimezone(UTC_TZ)

    timestamps = (
        db_session.query(ImageTable.timestamp)
        .filter(and_(
            ImageTable.timestamp >= start_time_utc,
            ImageTable.timestamp <= end_time_utc,
            ImageTable.num_vehicles != None
        ))
        .distinct().order_by(ImageTable.timestamp)
        .all()
    )

    # Extract the timestamps from the result
    timestamps_list = [
        UTC_TZ.localize(timestamp[0]).astimezone(SGP_TZ).strftime("%Y-%m-%d %H:%M:%S")
        for timestamp in timestamps
    ]

    count += 1

    return timestamps_list, count

def get_future_timestamps(db_session):
    START_TIMESTAMP = SGP_TZ.localize(datetime(2023, 11, 13, 0, 0, 0))
    END_TIMESTAMP = SGP_TZ.localize(datetime(2023, 11, 17, 23, 59, 59))

    start_time_utc = START_TIMESTAMP.astimezone(UTC_TZ)
    end_time_utc = END_TIMESTAMP.astimezone(UTC_TZ)

    timestamps = (
        db_session.query(ImageTable.timestamp)
        .filter(and_(
            ImageTable.timestamp >= start_time_utc,
            ImageTable.timestamp <= end_time_utc,
            ImageTable.num_vehicles != None
        ))
        .distinct().order_by(ImageTable.timestamp)
        .all()
    )

    # Extract the timestamps from the result
    timestamps_list = [
        UTC_TZ.localize(timestamp[0]).astimezone(SGP_TZ).strftime("%Y-%m-%d %H:%M:%S")
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
    return selected_time_obj.date().strftime("%Y-%m-%d")


def convert_date(dt_timestamp):
    return datetime.strptime(dt_timestamp, "%Y-%m-%d").strftime("%d %B %Y")


def get_available_times(search_date, timestamps):
    search_datetime = datetime.strptime(search_date, "%Y-%m-%d")

    # Check if the search date exists in the list of timestamps
    found_timestamps = [
        timestamp
        for timestamp in timestamps
        if search_datetime.date() == datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").date()
    ]

    return found_timestamps

def segregate_timestamps_by_hour(timestamps):
    # Create a dictionary to store timestamps for each hour
    hourly_timestamps = {}

    # Iterate through the timestamps
    for timestamp in timestamps:
        # Convert timestamp string to datetime object
        dt_object = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

        # Extract hour from datetime object and convert it to a string
        hour_str = str(dt_object.hour)

        hour_start_str = hour_str+":00:00"
        hour_end_str = ""
        if hour_str == '23':
            hour_end_str = "23:59:59"
        elif int(hour_str)+1 < 10:
            hour_end_str = '0'+str(int(hour_str)+1)+":00:00"
            hour_start_str = '0'+str(int(hour_str))+":00:00"
        else:
            hour_end_str = str(int(hour_str)+1)+":00:00"
        

        # If the hour is not in the dictionary, create a new list for that hour
        if hour_start_str + " - " + hour_end_str not in hourly_timestamps:
            hourly_timestamps[hour_start_str + " - " + hour_end_str] = []

        # Append the timestamp to the corresponding hour
        hourly_timestamps[hour_start_str + " - " + hour_end_str].append(timestamp)

    return hourly_timestamps

def extract_time(timestamps):
    hours_minutes_list = []
    for timestamp in timestamps:
        dt_object = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        hours_minutes_str = dt_object.strftime("%H:%M:%S")
        hours_minutes_list.append(hours_minutes_str)

    return hours_minutes_list

def init_plotly_components(db_session):
    timestamps = get_all_timestamps(db_session)
    dates = list(sorted(set([return_day_timestamp(timestamp) for timestamp in timestamps])))
    date_strings = [convert_date(date) for date in dates]
    datewise_avail_times = [{date: get_available_times(date, timestamps)} for date in dates]

    date_dropdown_options = [{'value': dates[i], 'label': date_strings[i]} for i in range(0,len(dates))]

    daywise_hour_options = []
    daywise_hour_slider = []
    for date_val in datewise_avail_times:
        date_key = list(date_val.keys())[0]
        hour_options = []
        hourly_slider_options = []
        hourly_segments = segregate_timestamps_by_hour(date_val[date_key])

        for key in hourly_segments:
            start_hr = key.split("-")[0].strip()
            end_hr = key.split("-")[1].strip()
            label = ""
            if end_hr != '23:59:59':
                label = datetime.strptime(start_hr, "%H:%M:%S").strftime("%I %p") + " - " + datetime.strptime(end_hr, "%H:%M:%S").strftime("%I %p")
            else:
                label = datetime.strptime(start_hr, "%H:%M:%S").strftime("%I %p") + " - " + datetime.strptime("00:00:00", "%H:%M:%S").strftime("%I %p")

            slider_labels = extract_time(hourly_segments[key])
            hour_options.append({'value': key, "label": label})
            hourly_slider_options.append({'hour': key, "slider_values": hourly_segments[key], "slider_labels": slider_labels, 'int_values': list(range(0, len(slider_labels)))})

        daywise_hour_options.append(hour_options)
        daywise_hour_slider.append(hourly_slider_options)

    slider_options = []

    for i in range(0, len(daywise_hour_slider[-1][-1]['slider_values'])):
        slider_options.append({'value': daywise_hour_slider[-1][-1]['int_values'][i], 'label': daywise_hour_slider[-1][-1]['slider_labels'][i]})

    slider_marks = {}
    for slider_val in slider_options:
        slider_marks[slider_val['value']] = {'label': slider_val['label'], 'style':{"transform": "rotate(45deg)"}}

    return dates, date_dropdown_options, daywise_hour_options, slider_options, slider_marks, daywise_hour_slider


def get_hourly_options():
    hours_options = []

    for hour in range(24):
        start_time = f"{hour:02}:00:00"
        end_time = f"{(hour + 1) % 24:02}:00:00"
        label = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'} - {(hour + 1) % 12 or 12} {'AM' if (hour + 1) % 24 < 12 else 'PM'}"
        value = f"{start_time} - {end_time}"
        hours_options.append({'label': label, 'value': value})

    hours_options[-1]['value'] = "23:00:00 - 23:59:59"

    return hours_options

def init_plotly_forecast(db_session):
    timestamps = get_future_timestamps(db_session)
    dates = list(sorted(set([return_day_timestamp(timestamp) for timestamp in timestamps])))
    date_strings = [convert_date(date) for date in dates]
    datewise_avail_times = [{date: get_available_times(date, timestamps)} for date in dates]

    date_dropdown_options = [{'value': dates[i], 'label': date_strings[i]} for i in range(0,len(dates))]

    return dates, date_dropdown_options, get_hourly_options()

def realtime_update(timestamps):
    dates = list(sorted(set([return_day_timestamp(timestamp) for timestamp in timestamps])))
    date_strings = [convert_date(date) for date in dates]
    datewise_avail_times = [{date: get_available_times(date, timestamps)} for date in dates]

    date_dropdown_options = [{'value': dates[i], 'label': date_strings[i]} for i in range(0,len(dates))]

    daywise_hour_options = []
    daywise_hour_slider = []
    for date_val in datewise_avail_times:
        date_key = list(date_val.keys())[0]
        hour_options = []
        hourly_slider_options = []
        hourly_segments = segregate_timestamps_by_hour(date_val[date_key])

        for key in hourly_segments:
            start_hr = key.split("-")[0].strip()
            end_hr = key.split("-")[1].strip()
            label = ""
            if end_hr != '23:59:59':
                label = datetime.strptime(start_hr, "%H:%M:%S").strftime("%I %p") + " - " + datetime.strptime(end_hr, "%H:%M:%S").strftime("%I %p")
            else:
                label = datetime.strptime(start_hr, "%H:%M:%S").strftime("%I %p") + " - " + datetime.strptime("00:00:00", "%H:%M:%S").strftime("%I %p")

            slider_labels = extract_time(hourly_segments[key])
            hour_options.append({'value': key, "label": label})
            hourly_slider_options.append({'hour': key, "slider_values": hourly_segments[key], "slider_labels": slider_labels, 'int_values': list(range(0, len(slider_labels)))})

        daywise_hour_options.append(hour_options)
        daywise_hour_slider.append(hourly_slider_options)


    return dates, date_dropdown_options, daywise_hour_options, daywise_hour_slider

def get_selected_time_forecast_data(db_session, selected_start_time_obj, selected_end_time_obj):
    # Your hourly forecast function

    raise NotImplementedError
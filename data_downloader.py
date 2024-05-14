from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import time
import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import alembic.config
import logging

from orm import Image as ImageTable
from utils import get_new_md5


NUM_WORKERS = 50


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
)


def download_image(camera_data):
    img_url = camera_data["image"]

    try:
        response = requests.get(img_url)
        # Raise an error for bad responses
        response.raise_for_status()

        return {
            "image_content": response.content,
            "camera_data": camera_data
        }
    except Exception as e:
        raise Exception(f"Error downloading image: {img_url} - {e}")


def fetch_latest_metadata():
    try:
        headers = {
            'authority': 'api.data.gov.sg',
            'accept': '/',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'origin': 'https://beta.data.gov.sg/',
            'referer': 'https://beta.data.gov.sg/',
            'sec-ch-ua': '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
        }
        url = "https://api.data.gov.sg/v1/transport/traffic-images"

        response = requests.get(url, headers=headers)
        return response
    except Exception as e:
        raise Exception(f"{url} - Error: {e}")


def fetch_live_data(frequency_seconds, db_session):
    while True:
        logging.info(f"Fetching traffic data at time: {datetime.now()}")
        try:
            response = fetch_latest_metadata()
        except Exception as e:
            logging.error(e)

        response_json = response.json()
        logging.debug(response.status_code)
        if response.status_code != 200:
            logging.error("Incorrect response obtained: {response.status_code}")
            logging.debug(response.json())
        cameras_data = response_json['items'][0]['cameras']

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            future_to_data = {}

            md5_to_cameras_data = {
                camera_data['image_metadata']['md5']: camera_data
                for camera_data in cameras_data
            }
            new_md5 = get_new_md5(list(md5_to_cameras_data.keys()), db_session)

            cameras_data = [
                md5_to_cameras_data[md5]
                for md5 in new_md5
            ]

            for camera_data in cameras_data:
                future_to_data[executor.submit(download_image, camera_data)] = camera_data

        data_to_insert = []

        # Wait for all submitted tasks to be completed
        for future in as_completed(future_to_data):
            try:
                # This will re-raise any exceptions caught during the task execution
                result = future.result()
            except Exception as e:
                logging.error(e)

            if result is not None:
                timestamp = datetime.strptime(result['camera_data']['timestamp'], "%Y-%m-%dT%H:%M:%S%z")
                data_to_insert.append({
                    "timestamp": timestamp,
                    "image": result['image_content'],
                    "image_url": result['camera_data']['image'],
                    "latitude": result['camera_data']['location']['latitude'],
                    "longitude": result['camera_data']['location']['longitude'],
                    "camera_id": result['camera_data']['camera_id'],
                    "height": result['camera_data']['image_metadata']['height'],
                    "width": result['camera_data']['image_metadata']['width'],
                    "md5": result['camera_data']['image_metadata']['md5']
                })

        if data_to_insert:
            db_session.bulk_insert_mappings(ImageTable, data_to_insert)
            db_session.commit()

        logging.info(f"Finished fetching traffic data at time: {datetime.now()}")

        time.sleep(frequency_seconds)


def init_db_session():
    """
    Create a new db session
    """
    db_engine = create_engine(os.getenv("DB_CONN_STR"))
    db_engine.connect()

    session_maker = sessionmaker(bind=db_engine)
    db_session = session_maker()

    logging.getLogger('alembic').setLevel(logging.INFO)
    alembic_cfg = alembic.config.Config('alembic.ini')
    alembic.command.upgrade(alembic_cfg, 'head')

    return db_engine, db_session


def main():
    db_engine, db_session = init_db_session()
    fetch_live_data(120, db_session)


if __name__ == "__main__":
    main()

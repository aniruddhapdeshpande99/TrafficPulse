import torch
from transformers import AutoImageProcessor, AutoModelForObjectDetection
from PIL import Image

import os
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, update
import logging
from io import BytesIO

from orm import Image as ImageTable
from utils import fetch_unfilled_vehicles_data


BATCH_SIZE = 100
INTERESTED_VEHICLES = {'car', 'truck', 'bus', 'van', 'scooty', 'scooter', 'bike', 'lorry'}

image_processor = AutoImageProcessor.from_pretrained("hustvl/yolos-small")
model = AutoModelForObjectDetection.from_pretrained("hustvl/yolos-small")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
)


def find_number_vehicles(image_bytes):
    image = Image.open(BytesIO(image_bytes))
    inputs = image_processor(images=image, return_tensors="pt")
    outputs = model(**inputs)

    target_sizes = torch.tensor([image.size[::-1]])
    results = image_processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)[0]

    # print(f"Number of vehicles: {len(results['boxes'])}")
    # for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    #     box = [round(i, 2) for i in box.tolist()]
    #     print(
    #             f"Detected {model.config.id2label[label.item()]} with confidence "
    #             f"{round(score.item(), 3)} at location {box}"
    #     )

    found_objects = [model.config.id2label[label.item()] for label in results["labels"]]

    return found_objects


def init_db_session():
    """
    Create a new db session
    """
    db_engine = create_engine(os.getenv("DB_CONN_STR"))
    db_engine.connect()

    session_maker = sessionmaker(bind=db_engine)
    db_session = session_maker()

    return db_engine, db_session


def fill_num_vehicles(db_session):
    FETCH_LATEST_IDS = bool(int(os.getenv('FETCH_LATEST_IDS', '0')))

    while True:
        logging.info(f"Fetching traffic data at time: {datetime.now()}")
        data_points = fetch_unfilled_vehicles_data(db_session, BATCH_SIZE, FETCH_LATEST_IDS)
        results = {}
        for point in data_points:
            objects = find_number_vehicles(point.image)
            vehicles = [
                object
                for object in objects
                if object.lower() in INTERESTED_VEHICLES
            ]
            results[point.id] = len(vehicles)

        # Now batch update the database.
        for point_id, num_vehicles in results.items():
            stmt = (
                update(ImageTable).
                where(ImageTable.id == point_id).
                values(num_vehicles=num_vehicles)
            )
            db_session.execute(stmt)        
        db_session.commit()


def main():
    db_engine, db_session = init_db_session()
    fill_num_vehicles(db_session)


if __name__ == "__main__":
    main()

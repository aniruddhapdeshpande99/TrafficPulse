


import torch
from transformers import AutoImageProcessor, AutoModelForObjectDetection
from PIL import Image
import requests
import time

# url = "http://images.cocodataset.org/val2017/000000039769.jpg"
url = "https://images.data.gov.sg/api/traffic-images/2023/11/8c3eebc7-955a-4a1f-9816-ba841f64f921.jpg"
image = Image.open(requests.get(url, stream=True).raw)

def run_small_model():
    image_processor = AutoImageProcessor.from_pretrained("hustvl/yolos-small")
    model = AutoModelForObjectDetection.from_pretrained("hustvl/yolos-small")

    start = time.time()
    inputs = image_processor(images=image, return_tensors="pt")
    outputs = model(**inputs)

    target_sizes = torch.tensor([image.size[::-1]])
    results = image_processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)[0]

    end = time.time()

    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        box = [round(i, 2) for i in box.tolist()]
        print(
                f"Detected {model.config.id2label[label.item()]} with confidence "
                f"{round(score.item(), 3)} at location {box}"
        )

    print(f"Small Model - Time taken: {end - start}s")
    print()
    print()


def run_base_model():
    image_processor = AutoImageProcessor.from_pretrained("hustvl/yolos-base")
    model = AutoModelForObjectDetection.from_pretrained("hustvl/yolos-base")

    start = time.time()
    inputs = image_processor(images=image, return_tensors="pt")
    outputs = model(**inputs)

    target_sizes = torch.tensor([image.size[::-1]])
    results = image_processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)[0]

    end = time.time()

    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        box = [round(i, 2) for i in box.tolist()]
        print(
                f"Detected {model.config.id2label[label.item()]} with confidence "
                f"{round(score.item(), 3)} at location {box}"
        )

    print(f"Base Model - Time taken: {end - start}s")
    print()
    print()

run_small_model()
run_base_model()

# 1. Fetch 100 datapoints from the database. If no data is found, then do an exponential backoff.
# 2. Sequentially pass the data points to the predict model
# 3. Update the database again, by using the `id` column.

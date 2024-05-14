

import torch
from transformers import AutoImageProcessor, AutoModelForObjectDetection
from PIL import Image
import requests
import time

url = "http://images.cocodataset.org/val2017/000000039769.jpg"
image = Image.open(requests.get(url, stream=True).raw)

image_processor_small = AutoImageProcessor.from_pretrained("facebook/detr-resnet-50")
model_small = AutoModelForObjectDetection.from_pretrained("facebook/detr-resnet-50")

start = time.time()
inputs = image_processor_small(images=image, return_tensors="pt")
outputs = model_small(**inputs)

# convert outputs (bounding boxes and class logits) to COCO API

target_sizes = torch.tensor([image.size[::-1]])
results = image_processor_small.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)[0]

end = time.time()

for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
    box = [round(i, 2) for i in box.tolist()]
    print(
            f"Detected {model_small.config.id2label[label.item()]} with confidence "
            f"{round(score.item(), 3)} at location {box}"
    )

print(f"Time taken: {end - start}s")



# 1. Fetch 100 datapoints from the database.
# 2. Sequentially 



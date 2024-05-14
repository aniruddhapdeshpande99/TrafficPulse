import torch
from transformers import AutoImageProcessor, AutoModelForObjectDetection
from PIL import Image
import requests
import time

# Function to process and print results
def process_and_print_results(results, model):
    for result in results:
        for score, label, box in zip(result["scores"], result["labels"], result["boxes"]):
            box = [round(i, 2) for i in box.tolist()]
            print(
                f"Detected {model.config.id2label[label.item()]} with confidence "
                f"{round(score.item(), 3)} at location {box}"
            )

def batch_processing():
    url = 'http://images.cocodataset.org/val2017/000000039769.jpg'
    image = Image.open(requests.get(url, stream=True).raw)

    image_processor_small = AutoImageProcessor.from_pretrained("facebook/detr-resnet-50")
    model_small = AutoModelForObjectDetection.from_pretrained("facebook/detr-resnet-50")

    start = time.time()

    # Replicate the image 5 times to create a batch
    images = [image for _ in range(50)]
    inputs = image_processor_small(images=images, return_tensors="pt")
    outputs = model_small(**inputs)

    # convert outputs (bounding boxes and class logits) to COCO API for each image in the batch
    target_sizes = torch.tensor([image.size[::-1]] * 50)  # Replicate target size for batch
    results = image_processor_small.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)

    end = time.time()

    # Process results for each image in the batch
    # for result in results:
    #     process_and_print_results([result], model_small)

    print(f"Batch Processing for 50 images took {end - start}s")


def sequential_processing():
    url = 'http://images.cocodataset.org/val2017/000000039769.jpg'
    image = Image.open(requests.get(url, stream=True).raw)

    image_processor_small = AutoImageProcessor.from_pretrained("facebook/detr-resnet-50")
    model_small = AutoModelForObjectDetection.from_pretrained("facebook/detr-resnet-50")

    start = time.time()

    for _ in range(50):
        inputs = image_processor_small(images=image, return_tensors="pt")
        outputs = model_small(**inputs)

        # convert outputs (bounding boxes and class logits) to COCO API for each image in the batch
        target_sizes = torch.tensor([image.size[::-1]])
        results = image_processor_small.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)

    end = time.time()

    print(f"Sequential Processing for 50 images took {end - start}s")

batch_processing()
sequential_processing()

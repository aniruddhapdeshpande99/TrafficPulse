from concurrent.futures import ThreadPoolExecutor
import requests
from datetime import datetime, timedelta

from utils import generate_datetimes


NUM_WORKERS = 300


def download_image(img_url, save_path="./images/"):
    try:
        response = requests.get(img_url, stream=True)
        response.raise_for_status()  # Raise an error for bad responses

        img_id = (img_url.split('/')[-1]).split('.')[0]
        with open(f"{save_path}{img_id}", 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return True
    except Exception as e:
        print(f"Error downloading image: {img_url} - {e}")
        return False


def fetch_historical_data_at_datetime(datetime):
    """
    Function to fetch historical data at a particular datetime.
    """
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
        url = f"https://api.data.gov.sg/v1/transport/traffic-images?date_time={datetime.strftime('%Y-%m-%dT%H:%M:%S')}"

        response = requests.get(url, headers=headers)
        response_json = response.json()
        cameras_data = response_json['items'][0]['cameras']
        for camera_data in cameras_data:
            download_image(camera_data['image'])

        print(response)
        return response
    except Exception as e:
        print(e)
        return f"{url} - Error: {e}"


def fetch_historical_data(start_datetime, end_datetime, frequency_seconds):
    """
    Function to fetch historical data between two datetimes at the specified
    frequency in seconds.
    """
    req_datetimes = generate_datetimes(start_datetime, end_datetime, frequency_seconds)

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        executor.map(fetch_historical_data_at_datetime, req_datetimes)


def main():
    start = datetime.strptime("2023-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S")
    end = datetime.strptime("2023-01-05T00:00:00", "%Y-%m-%dT%H:%M:%S")
    fetch_historical_data(start, end, 30)


if __name__ == "__main__":
    main()

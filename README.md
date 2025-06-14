# Traffic-Pulse

**Interactive Real-Time Traffic Jam Analysis & Forecast System**

Aniruddha Prashant Deshpande · Bhargava Somu · Mahek Mishra · Tenzin Bhotia 

Georgia Institute of Technology (Course Project for CSE 6242 - Data and Visual Analytics)

---

<!-- Poster image linked to YouTube demo video -->

[![Traffic-Pulse Poster](./images/poster.png)](https://www.youtube.com/watch?v=lfnhp8xkoN8)
*Click to watch our poster video on YouTube.*

---

## 🚀 Overview

Traffic congestion is a major issue in many metropolitan areas. **Traffic-Pulse** provides:

* **Real-time**, **interactive** visualization of live traffic feeds
* **Forecasts** of traffic density at user-selected locations and future times
* A **visual + data-driven** approach to help city planners uncover hotspots and optimize traffic management

---

## 📐 System Architecture

![System Architecture](./images/architecture.png)

1. **Data Scraper**

   * Polls Singapore LTA DataMall API every 5 min
   * Downloads CCTV images + metadata (timestamp, lat/lon)

2. **Object Detector**

   * Runs YOLO-v5 on each frame to count vehicles
   * Labels and stores counts in Postgres

3. **Forecast Models**

   * Trains one AR/MA/ARIMA model per camera
   * Parallel grid-search tuning for parameters (p, d, q)

4. **UI (Plotly + Dash)**

   * Live map with heatmap overlay
   * Time slider & dropdowns to inspect history
   * “Forecast” button for future‐time predictions

---

## 🔧 Quickstart

### 1. Bring up the stack

```bash
docker compose build
docker compose up
```

* Spins up Postgres & scraping/detection services
* Scrapes new images every 5 min and populates the database

### 2. Run the dashboard

```bash
python visualize.py
```

### 3. (Optional) Database migrations

```bash
alembic init db-schemas
alembic revision -m "create traffic tables"
sqlacodegen postgresql+psycopg2://postgres:postgres@127.0.0.1:5434/traffic_pulse_db --outfile orm.py
```

---

## 🔍 Intuitive Explanation

1. **Why images?**
   CCTV snapshots are simple, cost-effective proxies for traffic flow—no need for GPS or expensive sensors.

2. **Counting vehicles = traffic density**
   YOLO-v5 classifies “car”, “truck”, “bus”, etc., and sums them to estimate congestion.

3. **ARIMA forecasting**

   * **AR**: leverages past counts (`p` lags)
   * **MA**: smooths out forecast errors (`q` window)
   * **I**: differences (`d`) to remove trends
   * We grid-search (p, d, q) in parallel across 90 cameras for sub-minute retraining.

4. **Interactive UX**

   * **Slider**: scrub through history
   * **Dropdowns**: select date/hour
   * **Forecast**: pick any future timestamp, hit “Forecast”, and watch the heatmap update instantly

---

## 📈 Key Results

|   Model   | Avg. RMSE (vehicles) |
| :-------: | :------------------: |
|     MA    |          3.1         |
|     AR    |          2.8         |
| **ARIMA** |        **2.5**       |

> **Interpretation**:
> On average, our ARIMA forecasts are within ±2.5 vehicles of the YOLO-measured “ground truth” per camera per 5-min interval.

---

## 💡 Highlights

* **GCP spend**: USD 253 of 300 free credits for 7 days of continuous scraping & detection
* **Data volume**: Collected 45 GB of imagery → 300 K+ database rows
* **Deployment**: Fully IaC via Terraform + GitHub Actions CI/CD
* **Performance**: Parallelized hyperparameter tuning (×4 speedup on 16 cores)

---

## 📂 Project Structure

```
.
├── poster.png               # Project poster (clickable link)
├── architecture.png         # System architecture diagram
├── docker-compose.yml       # Services: scraper, detector, Postgres
├── visualize.py             # Launches Plotly/Dash dashboard
├── orm.py                   # SQLAlchemy models (generated by sqlacodegen)
├── db-schemas/              # Alembic migration scripts
└── README.md  
```

---

## 🔧 Future Work

* **Deep learning forecasting**: explore LSTM/ConvLSTM for non-linear patterns
* **Vehicle differentiation**: distinguish buses, trucks, scooters
* **Lane-level analysis**: lane segmentation via computer vision
* **Human-in-the-loop**: RLHF to fine-tune detection in challenging conditions

---

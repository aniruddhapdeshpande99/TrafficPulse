# Traffic-Pulse

### Instructions to fetch live data
```
docker compose build
docker compose up
```
This will download the traffic image data and store it in the dockerized Postgres Database. It hits the API every 3 minutes, but we observe the images changing every 5 minutes.

### Visualization
```
python visualize.py
```

### Working with Alembic
* Initialize - `alembic init db-schemas`
* Create Revision - `alembic revision -m "create xyz table"`

### Generating the ORM
```
sqlacodegen postgresql+psycopg2://postgres:postgres@127.0.0.1:5434/traffic_pulse_db --outfile orm.py
```

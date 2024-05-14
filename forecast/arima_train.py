import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import numpy as np
import math
from multiprocessing import Pool
import json
import argparse
import pickle


TEST_DATA_SPLIT_RATIO = 0.8
START_DATETIME = '2023-11-07T00:00:00'
END_DATETIME = '2023-11-10T09:00:00'
DEFAULT_ORDER = {
    "AR": [2, 0, 0],
    "MA": [0, 0, 1],
    "ARMA": [1, 0, 1],
    "ARIMA": [2, 1, 1],
}
MAX_NUM_VEHICLES = 23


def init_db_session():
    """
    Create a new db session
    """
    db_engine = create_engine(os.getenv("DB_CONN_STR"))
    db_engine.connect()

    session_maker = sessionmaker(bind=db_engine)
    db_session = session_maker()

    return db_engine, db_session


def calculate_accuracy(forecast, actual, algorithm):
    mae  = round(mean_absolute_error(actual, forecast), 4)
    rmse = round(math.sqrt(mean_squared_error(actual, forecast)), 4)
    return ({'algorithm': algorithm, 'mae': mae, 'rmse': rmse})


def evaluate_arima_model(train, test, order):
    # feature Scaling
    stdsc = StandardScaler()
    train_std = stdsc.fit_transform(train.values.reshape(-1, 1))
    test_std = stdsc.transform(test.values.reshape(-1, 1))
    # prepare training dataset
    history = [x for x in train_std]
    # make predictions
    predictions = []
    # rolling forecasts
    for t in range(len(test_std)):
        # predict
        model = ARIMA(history, order=order)
        model_fit = model.fit()
        yhat = model_fit.forecast()[0]
        # invert transformed prediction
        predictions.append(yhat)
        # observation
        history.append(test_std[t])
    # inverse transform
    predictions = stdsc.inverse_transform(np.array(predictions).reshape((-1, 1)))
    # calculate mse
    mse = mean_squared_error(test, predictions)
    return model_fit, predictions, mse


def predict_arima_model(train, period, order):
    # Feature Scaling
    stdsc = StandardScaler()
    train_std = stdsc.fit_transform(train.values.reshape(-1, 1))
    # fit model
    model = ARIMA(train_std, order=order)
    model_fit = model.fit()
    # make prediction
    yhat = model_fit.predict(len(train), len(train) + period -1, typ='levels')
    # inverse transform
    yhat = stdsc.inverse_transform(np.array(yhat).flatten())
    return yhat


def process_camera_data(args):
    camera_id, camera_train_df, camera_test_df, model_type, order = args

    # Prepare the data
    camera_train_df['timestamp'] = pd.to_datetime(camera_train_df['timestamp'])
    camera_train_df.set_index('timestamp', inplace=True)
    camera_train_df.sort_index(inplace=True)

    # Remove the data with duplicate timestamps
    camera_train_df = camera_train_df[~camera_train_df.index.duplicated(keep='first')]
    # Remove the unnecessary columns apart from timestamp and num_vehicles.
    camera_train_df = camera_train_df.drop(['id', 'camera_id'], axis=1)

    if camera_train_df['num_vehicles'].empty or camera_test_df['num_vehicles'].empty:
        return (camera_id, {})

    # predict test period with best parameter
    model_fit, predictions, _ = evaluate_arima_model(
        camera_train_df['num_vehicles'],
        camera_test_df['num_vehicles'],
        order
    )

    # Save the model
    model_fit
    model_fit.save(f'models/{model_type}/model_camera_{camera_id}.pkl')

    # calculate performance metrics
    acc = calculate_accuracy(predictions, camera_test_df['num_vehicles'], "model")
    return (camera_id, acc)

class InverseNormalizedARIMA:
    """
    Wrapper over ARIMA model to convert the normalized output from [0, 1]
    to [0, MAX_NUM_VEHICLES]. We do this since we are passing normalized input
    to the ARIMA model. We also round the output to nearest integer.
    """
    def __init__(self, model_path):
        self.model_path = model_path
        with open(model_path, 'rb') as file:
            self.model = pickle.load(file)

    def forecast(self, steps=1):
        result = self.model.forecast(steps=steps)
        return np.round(result * MAX_NUM_VEHICLES)


def main():
    parser = argparse.ArgumentParser(description="Traffic Pulse")
    parser.add_argument(
        '--model_type',
        type=str,
        choices=['AR', 'MA', 'ARMA', 'ARIMA'],
        default='ARIMA',
        help='Type of model to train (AR, MA, ARMA, ARIMA)'
    )
    args = parser.parse_args()
    model_type = args.model_type

    print("Starting DB Session Init...")
    db_engine, db_session = init_db_session()
    print("Finished DB Session Init")

    query = (
        f"""
        SELECT id, timestamp, camera_id, num_vehicles
        FROM images
        WHERE num_vehicles IS NOT NULL
        AND timestamp >= '{START_DATETIME}' AND timestamp <= '{END_DATETIME}'
        ORDER BY timestamp
        """
    )
    df = pd.read_sql_query(query, db_engine)

    print(len(df))

    # Break the loop if no data is returned. This means that there is no more
    # data to be processed in our database.
    if df.empty:
        print("No Data Found. Exiting...")
        return

    split = int(TEST_DATA_SPLIT_RATIO * len(df))
    train_data, test_data = df[0: split], df[split: ]
    train_data['num_vehicles'] = (train_data['num_vehicles'] - train_data['num_vehicles'].min()) / (train_data['num_vehicles'].max() - train_data['num_vehicles'].min())

    camera_ids = df['camera_id'].unique()

    hyperparameters = None
    if os.path.exists('hyperparameters.json'):
        with open('hyperparameters.json', 'r') as fp:
            hyperparameters = json.load(fp)

    # Prepare arguments for parallel processing
    args = []
    for camera_id in camera_ids:
        order = DEFAULT_ORDER[model_type]
        if hyperparameters is not None:
            try:
                order = hyperparameters[camera_id][model_type]
            except:
                order = DEFAULT_ORDER[model_type]

        args.append((
            camera_id,
            train_data[train_data['camera_id'] == camera_id].copy(),
            test_data[test_data['camera_id'] == camera_id].copy(),
            model_type,
            order
        ))

    # Create models/ folder if not present.
    os.makedirs("models/AR", exist_ok=True)
    os.makedirs("models/MA", exist_ok=True)
    os.makedirs("models/ARMA", exist_ok=True)
    os.makedirs("models/ARIMA", exist_ok=True)

    # Use multiprocessing pool to process data in parallel
    with Pool() as pool:
        results = pool.map(process_camera_data, args)

    # Print results
    for camera_id, acc in results:
        print(f"Printing stats for camera id {camera_id}")
        print(acc)
        print("\n")


if __name__ == "__main__":
    main()

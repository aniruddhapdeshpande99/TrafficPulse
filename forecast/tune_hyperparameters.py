import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import numpy as np
import itertools
from multiprocessing import Pool
import json


TEST_DATA_SPLIT_RATIO = 0.8
START_DATETIME = '2023-11-07T00:00:00'
END_DATETIME = '2023-11-08T23:59:00'


def init_db_session():
    """
    Create a new db session
    """
    db_engine = create_engine(os.getenv("DB_CONN_STR"))
    db_engine.connect()

    session_maker = sessionmaker(bind=db_engine)
    db_session = session_maker()

    return db_engine, db_session


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
        # model_fit = model.fit(disp=0)
        yhat = model_fit.forecast()[0]
        # invert transformed prediction
        predictions.append(yhat)
        # observation
        history.append(test_std[t])
    # inverse transform
    predictions = stdsc.inverse_transform(np.array(predictions).reshape((-1, 1)))
    # calculate mse
    mse = mean_squared_error(test, predictions)
    return predictions, mse


def evaluate_arima_models(train, test, p_values, d_values, q_values):
    best_score = {
        "AR": float("inf"),
        "MA": float("inf"),
        "ARMA": float("inf"),
        "ARIMA": float("inf"),
    }
    best_cfg = {
        "AR": None,
        "MA": None,
        "ARMA": None,
        "ARIMA": None,
    }
    pdq = list(itertools.product(p_values, d_values, q_values))

    for order in pdq:
        p, d, q = order
        try:
            _, mse = evaluate_arima_model(train, test, order)
            model_name = "ARIMA"
            if d == 0 and q == 0:
                # AR Model
                model_name = "AR"
            elif p == 0 and d == 0:
                # MA Model
                model_name = "MA"
            elif d == 0:
                # ARMA Model
                model_name = "ARMA"

            if mse < best_score[model_name]:
                best_score[model_name], best_cfg[model_name] = mse, order

            # Any combination of p, d, q is also part of the ARIMA Models
            if mse < best_score["ARIMA"]:
                best_score["ARIMA"], best_cfg["ARIMA"] = mse, order

            if mse < best_score:
                best_score, best_cfg = mse, order

        except:
            continue

    return best_cfg


def tune_hyperparameters_per_camera(args):
    camera_id, camera_train_df, camera_test_df, p_values, q_values, d_values = args

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
    best_cfg = evaluate_arima_models(
        camera_train_df['num_vehicles'],
        camera_test_df['num_vehicles'],
        p_values, q_values, d_values
    )

    return (camera_id, best_cfg)


def find_hyperparameters():
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

    # Break the loop if no data is returned. This means that there is no more
    # data to be processed in our database.
    if df.empty:
        print("No Data Found. Exiting...")
        return

    split = int(TEST_DATA_SPLIT_RATIO * len(df))
    train_data, test_data = df[0: split], df[split: ]
    train_data['num_vehicles'] = (train_data['num_vehicles'] - train_data['num_vehicles'].min()) / (train_data['num_vehicles'].max() - train_data['num_vehicles'].min())

    camera_ids = df['camera_id'].unique()

    p_values = [0, 1, 2, 4, 6, 8, 10]
    q_values = range(3)
    d_values = range(3)

    # Prepare arguments for parallel processing
    args = [
        (
            camera_id,
            train_data[train_data['camera_id'] == camera_id].copy(),
            test_data[test_data['camera_id'] == camera_id].copy(),
            p_values, q_values, d_values
        )
        for camera_id in camera_ids
    ]

    # Use multiprocessing pool to process data in parallel
    with Pool() as pool:
        results = pool.map(tune_hyperparameters_per_camera, args)

    # Print results
    best_hyperparameters = {
        camera_id: best_cfg
        for camera_id, best_cfg in results
    }
    with open('hyperparameters.json', 'w') as fp:
        json.dump(best_hyperparameters, fp, indent=4)


if __name__ == "__main__":
    find_hyperparameters()

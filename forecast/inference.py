import pickle
import numpy as np
from arima_train import InverseNormalizedARIMA



def main():

    # Load the model
    # with open("models/ARIMA/model_camera_2701.pkl", 'rb') as file:
    #     model = pickle.load(file)

    model = InverseNormalizedARIMA("models/ARIMA/model_camera_2701.pkl")
    result = model.forecast(steps=756.0)

    print(result)


if __name__ == "__main__":
    main()

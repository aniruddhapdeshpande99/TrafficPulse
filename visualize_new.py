import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback, State, no_update, callback_context
from utils_new import get_db_session, get_selected_time_camera_data, return_loc, init_plotly_components, init_plotly_forecast, update_live_timestamps, realtime_update, get_camera_metadata
from datetime import datetime
import dash_bootstrap_components as dbc
from random import randint
import dash_mantine_components as dmc
import os
from forecast.arima_train import InverseNormalizedARIMA


MAPBOX_ACCESS_TOKEN = 'pk.eyJ1IjoiYnNvbXUzIiwiYSI6ImNsb2h2eXlsbDE5ZHcycW8zMzB5Nzl4cGkifQ.lDORDrMIDnDFqxbfS_qGtA'

DB_SESSION = get_db_session()

live_count = 1

camera_metadata = get_camera_metadata(DB_SESSION)

dates, date_dropdown_options, daywise_hour_options, slider_options, slider_marks, daywise_hour_slider = init_plotly_components(DB_SESSION)

dates_forecast, date_dropdown_options_forecast, daywise_hour_options_forecast = init_plotly_forecast(DB_SESSION)

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash("Traffic Pulse", external_stylesheets=external_stylesheets)
server = app.server
app.layout = html.Div([
    # Add the dropdown for model selection
    html.H3("Live Traffic Data", style={'width': '25%', 'display': 'inline-block'}),
    html.Div(
        className="row", children=[
            html.Div(className='six columns', children=[
                dcc.Dropdown(
                    id='day-dropdown',
                    options=date_dropdown_options,
                    value=date_dropdown_options[-1]['value']
                )],
            style=dict(width='33%')),
            html.Div(className='six columns', children=[
                dcc.Dropdown(
                    id='hour-dropdown',
                    options=daywise_hour_options[-1],
                    value=daywise_hour_options[-1][-1]['value']
                )],
            style=dict(width='33%')),
            html.Div(className='six columns', children=[
                html.Button('Go Live', id='go-live-button', n_clicks=0, style={'background-color': '#90EE90'})],
            style=dict(width='33%')),
        ],
        style=dict(display='flex')
    ),
    dcc.Graph(id="map-plot", clear_on_unhover=True, style={'width': '70%', 'height': '60vh', 'display': 'inline-block'}),

    html.Div([
                html.Img(id='hover-image', src='', style={'maxWidth': '300px', 'display': 'inline-block', "-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)"}),
                html.Div(id='vehicle-count', style={"-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)", "display": "inline-block", "position":"absolute", "left":"85%", "top":"20%"}),
                html.Div(id='latitude', style={"-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)", "display": "inline-block", "position":"absolute", "left":"85%", "top":"23%"}),
                html.Div(id='longitude', style={"-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)", "display": "inline-block", "position":"absolute", "left":"85%", "top":"25%"}),], 
            style={'width': '30%', 'display': 'inline-block'}
    ),

    # We want it initially hidden
    dcc.Slider(min(slider_options, key=lambda x: x["value"])['value'], max(slider_options, key=lambda x: x["value"])['value'], step=None,
                value=max(slider_options, key=lambda x: x["value"])['value'],
                marks=slider_marks,
                id='my-slider',
    ),
    dcc.Interval(
        id='interval-component',
        # in milliseconds
        interval=10*1000,
        n_intervals=0
    ),
    #
    # Forecasting side of things
    #
    html.Div([
        html.H3("Forecast", style={'width': '25%', 'display': 'inline-block','margin-top': '100px'}),  # Text title 'Forecast'

        # Dropdowns and Button in a row
        html.Div([
            dcc.Dropdown(
                id='forecast-model-dropdown',
                options=[
                    {'label': 'AR', 'value': 'AR'},
                    {'label': 'MA', 'value': 'MA'},
                    {'label': 'ARIMA', 'value': 'ARIMA'},
                ],
                value='ARIMA',  # Default value
                style={'width': '30%', 'display': 'inline-block'}
            ),
            dcc.Input(
                id='forecast-datetime-input',
                type='text',
                value="2023-11-13 00:00",
                style={'width': '10%', 'display': 'inline-block'}
            ),
            html.Button('Forecast', id='forecast-button', n_clicks=0, style={'width': '10%','display': 'inline-block', 'background-color': '#90EE90', "transform": "translate(40%, 0%)"}),
        ],
            style={'width': '100%'}
        ),
    ],
        style={'padding':20}
    ),
    dcc.Graph(id="forecast-map-plot", clear_on_unhover=True, style={'width': '70%', 'height': '60vh', 'display': 'inline-block'}),

    html.Div([
                html.Div(id='vehicle-count-forecast', style={"-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)", "display": "inline-block", "position":"absolute", "left":"85%", "top":"145%"}),
                html.Div(id='latitude-forecast', style={"-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)", "display": "inline-block", "position":"absolute", "left":"85%", "top":"148%"}),
                html.Div(id='longitude-forecast', style={"-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)", "display": "inline-block", "position":"absolute", "left":"85%", "top":"150%"})], 
            style={'width': '30%', 'display': 'inline-block', 'left': '85%', 'top': '60%'}
    ),
])

@app.callback(
        [
            Output('hour-dropdown', 'options'),
            Output('hour-dropdown', 'value'),
            Output('my-slider', 'min'),
            Output('my-slider','max'),
            Output('my-slider', 'value'),
            Output('my-slider', 'marks')
        ],
        [Input('day-dropdown', 'value')]
)
def day_change_updates(curr_date):
    global dates, daywise_hour_slider
    day_index = dates.index(curr_date)

    slider_day = daywise_hour_slider[day_index]
    slider_final_hr = slider_day[-1]

    updated_slider_options = []
    for i in range(0, len(slider_final_hr['slider_values'])):
        updated_slider_options.append({'value': slider_final_hr['int_values'][i], 'label': slider_final_hr['slider_labels'][i]})

    updated_slider_marks = {}
    for slider_val in updated_slider_options:
        updated_slider_marks[slider_val['value']] = {'label': slider_val['label'], 'style':{"transform": "rotate(45deg)"}}

    return daywise_hour_options[day_index], daywise_hour_options[day_index][-1]['value'], min(updated_slider_options, key=lambda x: x["value"])['value'], max(updated_slider_options, key=lambda x: x["value"])['value'], max(updated_slider_options, key=lambda x: x["value"])['value'], updated_slider_marks


@app.callback(
        [
            Output('my-slider', 'min', allow_duplicate=True),
            Output('my-slider','max', allow_duplicate=True),
            Output('my-slider', 'value', allow_duplicate=True),
            Output('my-slider', 'marks', allow_duplicate=True)
        ],
        [Input('day-dropdown', 'value'), Input('hour-dropdown', 'value')],
        prevent_initial_call=True
)
def day_hour_change_updates(curr_date, curr_hour):
    global dates, daywise_hour_slider
    day_index = dates.index(curr_date)

    slider_day = daywise_hour_slider[day_index]
    slider_final_hr = []

    for day_hour in slider_day:
        if day_hour['hour'] == curr_hour:
            slider_final_hr = day_hour

    updated_slider_options = []
    for i in range(0, len(slider_final_hr['slider_values'])):
        updated_slider_options.append({'value': slider_final_hr['int_values'][i], 'label': slider_final_hr['slider_labels'][i]})

    updated_slider_marks = {}
    for slider_val in updated_slider_options:
        updated_slider_marks[slider_val['value']] = {'label': slider_val['label'], 'style':{"transform": "rotate(45deg)"}}

    return min(updated_slider_options, key=lambda x: x["value"])['value'], max(updated_slider_options, key=lambda x: x["value"])['value'], max(updated_slider_options, key=lambda x: x["value"])['value'], updated_slider_marks



# Callback to update the image display based on hover data
@app.callback(
    Output('hover-image', 'src'),
    Output('hover-image', 'style'),
    Output('vehicle-count', 'children'),
    Output('latitude', 'children'),
    Output('longitude', 'children'),
    [Input("map-plot", "hoverData")]
)
def display_hover_image(hoverData):
    if hoverData and hoverData['points']:
        print(hoverData)
        custom_data = hoverData['points'][0]['customdata']
        image_url = custom_data['url']
        vehicle_count = custom_data['vehicle_count']
        latitude = custom_data['latitude']
        longitude = custom_data['longitude']

        # If there is a valid image URL, update the source and display the image
        if image_url:
            return (
                image_url,
                {'maxWidth': '300px', 'display': 'inline-block', "position":"absolute", "left":"85%", "top":"32%", "-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)"},
                f"Number of Vehicles: {vehicle_count}",
                f"Latitude: {latitude}",
                f"Longitude: {longitude}",
            )

    return '', {'display': 'none'}, '', '', ''


@app.callback(
    [Output("map-plot", "figure")],
    [Input('my-slider', 'value'), Input('my-slider', 'marks'), Input('day-dropdown', 'value')])
def update_map(slider_value, marks, curr_date):

    selected_time = curr_date + " " + marks[str(slider_value)]['label']
    date_format = '%Y-%m-%d %H:%M:%S'
    selected_time_obj = datetime.strptime(selected_time, date_format)
    selected_cameras_data = get_selected_time_camera_data(DB_SESSION, selected_time_obj)
    latitudes = [camera_data['latitude'] for camera_data in selected_cameras_data]
    longitudes = [camera_data['longitude'] for camera_data in selected_cameras_data]

    traffic_data = [camera_data['num_vehicles'] for camera_data in selected_cameras_data]

    locations = return_loc(latitudes, longitudes)

    custom_data = [
        {
            'url': camera_data['image_url'],
            'vehicle_count': traffic_data[index],
            'latitude': camera_data['latitude'],
            'longitude': camera_data['longitude'],
        }
        for index, camera_data in enumerate(selected_cameras_data)
    ]

    if traffic_data is None or len(traffic_data) == 0:
        return no_update

    fig = go.Figure()

    # Heatmap layer
    fig.add_trace(
        go.Densitymapbox(
            lat=latitudes,
            lon=longitudes,
            z=traffic_data,
            radius=20,
            colorscale='Hot', zmin=0, zmax=max(traffic_data),
            opacity=0.6,
            customdata=custom_data,
            hoverinfo='none',
            below=''
        )
    )

    # Circle markers layer
    for lat, lon, data, custom, place in zip(latitudes, longitudes, traffic_data, custom_data, locations):
        fig.add_trace(
            go.Scattermapbox(
                lat=[lat],
                lon=[lon],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=7,
                    color='green',
                    opacity=1.0
                ),
                customdata=[custom],
                hovertext=[place],
                hoverinfo='text',
                name="",
                below=''
            )
        )

    fig.update_layout(
        mapbox_style="streets",
        mapbox_accesstoken=MAPBOX_ACCESS_TOKEN,
        # Zoom level
        mapbox_zoom=10,
        # Center on Singapore
        mapbox_center={"lat": 1.3521, "lon": 103.8198},
    )

    return [fig]

@app.callback(
        [
            Output("day-dropdown", "options"),
            Output("hour-dropdown", "options", allow_duplicate=True),
            Output('my-slider', 'min', allow_duplicate=True),
            Output('my-slider','max', allow_duplicate=True),
            Output('my-slider', 'marks', allow_duplicate=True)
        ],
        [
            Input("interval-component", "n_intervals"),
            State("day-dropdown", "value"),
            State("hour-dropdown", "value"),
            State("my-slider", "value")
        ],
        prevent_initial_call=True
    )
def update_global_variables(n, curr_day_val, curr_hr_val, curr_slider_val):
    global dates, date_dropdown_options, daywise_hour_options, daywise_hour_slider, live_count
    timestamps, live_count = update_live_timestamps(DB_SESSION, live_count)
    dates, date_dropdown_options, daywise_hour_options, daywise_hour_slider = realtime_update(timestamps)

    if curr_day_val != date_dropdown_options[-1]['value']:
        return date_dropdown_options, no_update, no_update, no_update, no_update
    else:
        if curr_hr_val != daywise_hour_options[-1][-1]['value']:
            return date_dropdown_options, daywise_hour_options[-1], no_update, no_update, no_update
        else:
            live_slider_options = []

            for i in range(0, len(daywise_hour_slider[-1][-1]['slider_values'])):
                live_slider_options.append({'value': daywise_hour_slider[-1][-1]['int_values'][i], 'label': daywise_hour_slider[-1][-1]['slider_labels'][i]})

            live_slider_marks = {}
            for slider_val in live_slider_options:
                live_slider_marks[slider_val['value']] = {'label': slider_val['label'], 'style':{"transform": "rotate(45deg)"}}

            return date_dropdown_options, daywise_hour_options[-1], min(live_slider_options, key=lambda x: x["value"])['value'], max(live_slider_options, key=lambda x: x["value"])['value'], live_slider_marks


@app.callback(
    [Output('day-dropdown', 'value', allow_duplicate=True),
     Output('hour-dropdown', 'value', allow_duplicate=True),
     Output('my-slider', 'value', allow_duplicate=True)],
    [Input('go-live-button', 'n_clicks')],
    prevent_initial_call=True
)
def go_live(n_clicks):
    if n_clicks > 0:
        # Assuming date_dropdown_options and daywise_hour_options are updated with the latest data
        latest_date = date_dropdown_options[-1]['value']
        latest_hour = daywise_hour_options[-1][-1]['value']
        latest_slider_value = max(daywise_hour_slider[-1][-1]['int_values'])

        return latest_date, latest_hour, latest_slider_value
    else:
        # Return no update if the button hasn't been clicked
        return no_update, no_update, no_update
    


#
# Forecast side of things
#

@app.callback(
    [Output("forecast-map-plot", "figure")],
    [State('forecast-model-dropdown', 'value'), State('forecast-datetime-input', 'value'), Input("forecast-button", "n_clicks")])
def update_forecast_map(model_type, curr_datetime, button_click):
    if callback_context.triggered_id != "forecast-button":
        return no_update

    TRAINING_END_TIME = datetime(2023, 11, 10, 9, 0, 0)

    selected_datetime = datetime.strptime(curr_datetime, "%Y-%m-%d %H:%M")

    num_steps = int((selected_datetime - TRAINING_END_TIME).total_seconds() // 300)

    # Iterate over all the models in forecast/models/{model_type}
    forecasted_num_vehicles = {}
    directory = f"forecast/models/{model_type}"
    for filename in os.listdir(directory):
        camera_id = filename.split('.')[0].split('_')[-1]
        model_path = os.path.join(directory, filename)
        forecasted_val = InverseNormalizedARIMA(model_path).forecast(steps=num_steps)[-1]
        if forecasted_val < 0 or forecasted_val > 100:
            # Ignore impractical values
            continue
        forecasted_num_vehicles[camera_id] = forecasted_val

    camera_ids = list(forecasted_num_vehicles.keys())

    latitudes = [
        camera_metadata[camera_id]['latitude']
        for camera_id in camera_ids
    ]
    longitudes = [
        camera_metadata[camera_id]['longitude']
        for camera_id in camera_ids
    ]
    traffic_data = [forecasted_num_vehicles[camera_id] for camera_id in camera_ids]

    locations = return_loc(latitudes, longitudes)

    custom_data = [
        {
            'vehicle_count': traffic_data[index],
            'latitude': latitudes[index],
            'longitude': longitudes[index],
        }
        for index in range(len(camera_ids))
    ]

    fig = go.Figure()

    # Heatmap layer
    fig.add_trace(
        go.Densitymapbox(
            lat=latitudes,
            lon=longitudes,
            z=traffic_data,
            radius=20,
            colorscale='Hot', zmin=0, zmax=max(traffic_data),
            opacity=0.6,
            customdata=custom_data,
            hoverinfo='none',
            below=''
        )
    )

    # Circle markers layer
    for lat, lon, data, custom, place in zip(latitudes, longitudes, traffic_data, custom_data, locations):
        fig.add_trace(
            go.Scattermapbox(
                lat=[lat],
                lon=[lon],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=7,
                    color='green',
                    opacity=1.0
                ),
                customdata=[custom],
                hovertext=[place],
                hoverinfo='text',
                name="",
                below=''
            )
        )

    fig.update_layout(
        mapbox_style="streets",
        mapbox_accesstoken=MAPBOX_ACCESS_TOKEN,
        # Zoom level
        mapbox_zoom=10,
        # Center on Singapore
        mapbox_center={"lat": 1.3521, "lon": 103.8198},
    )

    return [fig]

# Callback to update the image display based on hover data
@app.callback(
    Output('vehicle-count-forecast', 'children'),
    Output('latitude-forecast', 'children'),
    Output('longitude-forecast', 'children'),
    [Input("forecast-map-plot", "hoverData")]
)
def display_hover_image_forecast(hoverData):
    if hoverData and hoverData['points']:
        custom_data = hoverData['points'][0]['customdata']
        vehicle_count = custom_data['vehicle_count']
        latitude = custom_data['latitude']
        longitude = custom_data['longitude']

        print(vehicle_count)
        print(latitude)
        print(longitude)

        return (
            f"Number of Vehicles: {vehicle_count}",
            f"Latitude: {latitude}",
            f"Longitude: {longitude}",
        )

    return '', '', ''


if __name__ == '__main__':
    app.run_server(debug=True)

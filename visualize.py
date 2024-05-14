import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback, State
from utils import get_latest_camera_data, get_db_session, get_all_timestamps, get_selected_time_camera_data, return_loc, return_day_timestamp, convert_date
from datetime import datetime
import dash_bootstrap_components as dbc


MAPBOX_ACCESS_TOKEN = 'pk.eyJ1IjoiYnNvbXUzIiwiYSI6ImNsb2h2eXlsbDE5ZHcycW8zMzB5Nzl4cGkifQ.lDORDrMIDnDFqxbfS_qGtA'

DB_SESSION = get_db_session()

timestamps = get_all_timestamps(DB_SESSION)
dates = list(sorted(set([return_day_timestamp(timestamp) for timestamp in timestamps])))
date_strings = [convert_date(date) for date in dates]

date_drop_down_options = [{'label': date_strings[i], 'value': dates[i]} for i in range(len(date_strings))] 
slider_options = dict((d_key, d_val) for d_key, d_val in enumerate(timestamps))

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
                    id='model-dropdown',
                    options=[
                        {'label': 'AR', 'value': 'AR'},
                        {'label': 'MA', 'value': 'MA'},
                        {'label': 'ARMA', 'value': 'ARMA'},
                        {'label': 'ARIMA', 'value': 'ARIMA'},
                    ],
                    value='ARIMA'
                )], 
            style=dict(width='33%')),
            html.Div(className='six columns', children=[
                dcc.Dropdown(
                    id='day-dropdown',
                    options=date_drop_down_options,
                    value=date_drop_down_options[-1]['value']
                )], 
            style=dict(width='33%')),
            html.Div(className='six columns', children=[
                dcc.Dropdown(
                    id='test-dropdown',
                    options=date_drop_down_options,
                    value=date_drop_down_options[-1]['value']
                )], 
            style=dict(width='33%'))
        ], 
        style=dict(display='flex')
    ),
    dcc.Graph(id="map-plot", clear_on_unhover=True, style={'width': '200vh', 'height': '60vh'}),
    # We want it initially hidden
    dcc.Slider(min(slider_options.keys()), max(slider_options.keys()), step=None,
                value=max(slider_options.keys()),
                marks={i: {'label': str(slider_options[i]), 'style':{"transform": "rotate(45deg)"}} for i in slider_options},
                id='my-slider',
    ),
    html.Img(id='hover-image', src='', style={'maxWidth': '300px', 'display': 'none', "position":"absolute", "left":"50%", "top":"70%", "-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)"}),
    html.Div(id='vehicle-count', style={"position":"absolute", "left":"40%", "top":"70%", "-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)"}),
    html.Div(id='latitude', style={"position":"absolute", "left":"40%", "top":"75%", "-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)"}),
    html.Div(id='longitude', style={"position":"absolute", "left":"40%", "top":"80%", "-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)"}),
    html.Div(id='model-selection-output', style={'display': 'none'}),
    dcc.Interval(
        id='interval-component',
        # in milliseconds
        interval=10*1000,
        n_intervals=0
    ),
    html.Div([
        html.H3("Forecast", style={'width': '25%', 'display': 'inline-block','margin-top': '100px'}),  # Text title 'Forecast'

        # Dropdowns and Button in a row
        html.Div([
            dcc.Dropdown(
                id='forecast-model-dropdown',
                options=[
                    {'label': 'AR', 'value': 'AR'},
                    {'label': 'MA', 'value': 'MA'},
                    {'label': 'ARMA', 'value': 'ARMA'},
                    {'label': 'ARIMA', 'value': 'ARIMA'},
                ],
                value='ARIMA',  # Default value
                style={'width': '30%', 'display': 'inline-block'}
            ),

            dcc.Dropdown(
                id='forecast-date-dropdown',
                options=date_drop_down_options,
                value=date_drop_down_options[-1]['value'],
                style={'width': '30%', 'display': 'inline-block'}
            ),
            dcc.Dropdown(
                id='additional-dropdown-2',
                options=[
                    {'label': 'Choice A', 'value': 'ChoiceA'},
                    {'label': 'Choice B', 'value': 'ChoiceB'},
                    {'label': 'Choice C', 'value': 'ChoiceC'},
                ],
                value='ChoiceA',  # Default value
                style={'width': '30%', 'display': 'inline-block'}
            ),

            html.Button('Forecast', id='forecast-button', n_clicks=0, style={'width': '10%','display': 'inline-block'}),
        ], 
            style={'width': '100%'}
        ),
    ],
        style={'padding':20}
    )
])


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
        custom_data = hoverData['points'][0]['customdata']
        image_url = custom_data['url']
        vehicle_count = custom_data['vehicle_count']
        latitude = custom_data['latitude']
        longitude = custom_data['longitude']

        # If there is a valid image URL, update the source and display the image
        if image_url:
            return (
                image_url,
                {'maxWidth': '300px', 'display': 'block', "position":"absolute", "left":"50%", "top":"70%", "-ms-transform": "translate(-50%, 0%)", "transform": "translate(-50%, 0%)"},
                f"Number of Vehicles: {vehicle_count}",
                f"Latitude: {latitude}",
                f"Longitude: {longitude}",
            )

    return '', {'display': 'none'}, '', '', ''


@app.callback(
    [Output("my-slider", "min"), Output("my-slider", "max"), Output("my-slider", "marks"), Output("map-plot", "figure")],
    [Input('my-slider', 'value')]
)
def update_map(slider_value):

    timestamps = get_all_timestamps(DB_SESSION)
    slider_options = dict((d_key, d_val) for d_key, d_val in enumerate(timestamps))
    selected_time = slider_options[slider_value]
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

    return min(slider_options.keys()), max(slider_options.keys()), {i: {'label': str(slider_options[i]), 'style':{"transform": "rotate(45deg)"}} for i in slider_options}, fig


@app.callback([Output("my-slider", "min", allow_duplicate=True), Output("my-slider", "max", allow_duplicate=True), Output("my-slider", "marks", allow_duplicate=True)], [Input("interval-component", "n_intervals")], prevent_initial_call=True)
def update_slider_with_time(n):

    timestamps = get_all_timestamps(DB_SESSION)
    slider_options = dict((d_key, d_val) for d_key, d_val in enumerate(timestamps))

    return min(slider_options.keys()), max(slider_options.keys()), {i: {'label': str(slider_options[i]), 'style':{"transform": "rotate(45deg)"}} for i in slider_options}


if __name__ == '__main__':
    app.run_server(debug=True)

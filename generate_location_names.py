import json
from geopy.geocoders import Photon
geolocator = Photon(user_agent="singapore_loc")

with open('./metadata/lat_long.json', 'r') as data_file:
    json_data = data_file.read()

data = json.loads(json_data)
 
for entry in data:
    entry["Address"] = str(geolocator.reverse(str(entry['latitude'])+","+str(entry['longitude'])))
    print(entry["Address"])

with open('./metadata/lat_long_place.json', 'w') as fout:
    json.dump(data , fout)

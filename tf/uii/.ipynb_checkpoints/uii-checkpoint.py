import json
import pathlib
import webbrowser

import osmutils

import responses
import pandas as pd
import googlemaps

from googlemaps.maps import StaticMapMarker
from googlemaps.maps import StaticMapPath

import matplotlib.pyplot as plt
import matplotlib.image as mpimg


def _get_clean_train_filepaths(train_data_dir):
    clean_train_files = []
    main_train_dir_path = pathlib.Path(
        pathlib.PurePath(pathlib.Path.cwd()).parent, pathlib.Path('train'))
    
    for train_dir in [x for x in main_train_dir_path.iterdir()
                      if x.is_dir() and '.' not in x.name]:
        clean_dir = train_dir / str(train_data_dir)
        for clean_train_file in [x for x in clean_dir.iterdir() 
                                 if not x.is_dir()]:
            clean_train_files.append(str(clean_train_file))
    
    return clean_train_files


def get_pd_dataframe_from_dir(train_data_dir):
    clean_train_files = _get_clean_train_filepaths(train_data_dir)

    # setup pandas dataframe
    df = pd.concat([pd.read_csv(x) for x in clean_train_files], sort=False)

    return df


gmaps = googlemaps.Client(key='AIzaSyB7a_Qna33F555_IaO7209uE7K46mZaEug')

path = StaticMapPath(
            points=[{"lat": -33.867486, "lng": 151.206990}, "Sydney"],
            weight=5, color="red", geodesic=True, fillcolor="Red"
        )
print(path)

def gmaps_test(ue_logs):
    # url = 'https://maps.googleapis.com/maps/api/staticmap'
    # responses.add(responses.GET, url, status=200)

    path = StaticMapPath(
                points=[(62.107733,-145.541936), 'Delta+Junction,AK'],
                weight=5, color="red"
            )

    m1 = StaticMapMarker(
        locations=[(62.107733,-145.541936)],
        color="blue", label="S"
    )

    m2 = StaticMapMarker(
        locations=['Delta+Junction,AK'],
        size="tiny", color="green"
    )

    m3 = StaticMapMarker(
        locations=["Tok,AK"],
        size="mid", color="0xFFFF00", label="C"
    )

    # locations = []
    # for ue_log in ue_logs:
    #     locations.append((ue_log['gps']['lat'], ue_log['gps']['lon']))
    #     # print(ue_log['gps']['lat'])
    # markers = StaticMapMarker(locations=locations, size='tiny')
    loca = [(ue_log['gps']['lat'], ue_log['gps']['lon']) for ue_log in ue_logs]
    markers = StaticMapMarker(locations=loca)
    # response = gmaps.static_map(
    #     size=(400, 400), zoom=17, center=(24.7877303,120.9961515),
    #     maptype="hybrid", format="png", scale=2, visible=["Tok,AK"],
    #     path=path, markers=[m1, m2, m3]
    # )
    response = gmaps.static_map(
        size=(640, 640), zoom=16, center=(24.7877303,120.9961515),
        maptype='roadmap', format="png", scale=2, markers=markers 
    )


    f = open('map.png', 'wb')
    i = 0
    for chunk in response:
        if chunk:
            f.write(chunk)
            i +=1
    f.close()
    print(i)

    img = plt.imread('map.png')
    plt.imshow(img)
    plt.show()
    input('done')
    pathlib.Path('map.png').unlink()


def main():
    osmutils.processUELocation(24.782652, 120.998300, 10)


if __name__ == '__main__':
    main()

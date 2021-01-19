import math
import itertools
import json
import subprocess

import pandas as pd
import shapely
import geopandas

_EARTH_RADIUS = 6371007.2


def steps_to_meter(steps):
    return steps * 0.8128


def getDistanceBetweenPoints(lat1, lon1, lat2, lon2):
    deltaLat = math.radians(lat2 - lat1)
    deltaLon = math.radians(lon2 - lon1)
    a = math.sin(deltaLat / 2) * math.sin(deltaLat / 2) + math.cos(
        math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(
            deltaLon / 2) * math.sin(deltaLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS * c


def getBearingBetweenPoints(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    deltaLon = lon2 - lon1
    y = math.sin(deltaLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
        lat2) * math.cos(deltaLon)
    return math.degrees(math.atan2(y, x))


def getPointFromPointDistanceAndBearing(lat, lon, dist, bearing):
    lat = math.radians(lat)
    lon = math.radians(lon)
    bearing = math.radians(bearing)
    dr = dist / _EARTH_RADIUS

    dest_lat = math.asin(
        math.sin(lat) * math.cos(dr) +
        math.cos(lat) * math.sin(dr) * math.cos(bearing))
    atan2_y = math.sin(bearing) * math.sin(dr) * math.cos(lat)
    atan2_x = math.cos(dr) - math.sin(lat) * math.sin(dest_lat)
    dest_lon = lon + math.atan2(atan2_y, atan2_x)
    return (math.degrees(dest_lat), (math.degrees(dest_lon) + 540) % 360 - 180)


def getRoadCircleIntersection(ueLat, ueLon, radius, lat1, lon1, lat2, lon2):
    intersections = []

    cosC0 = math.cos(math.radians(ueLat))
    A0 = math.radians(lat1) * _EARTH_RADIUS
    A1 = math.radians(lon1) * cosC0 * _EARTH_RADIUS
    B0 = math.radians(lat2) * _EARTH_RADIUS
    B1 = math.radians(lon2) * cosC0 * _EARTH_RADIUS
    C0 = math.radians(ueLat) * _EARTH_RADIUS
    C1 = math.radians(ueLon) * cosC0 * _EARTH_RADIUS

    v0 = A0 - C0
    v1 = A1 - C1
    u0 = B0 - A0
    u1 = B1 - A1
    alpha = math.pow(u0, 2) + math.pow(u1, 2)
    beta = (u0 * v0) + (u1 * v1)
    gamma = (math.pow(v0, 2) + math.pow(v1, 2)) - math.pow(radius, 2)
    sq_val = math.pow(beta, 2) - alpha * gamma

    if sq_val >= 0:
        t0 = (-beta + math.sqrt(math.pow(beta, 2) - alpha * gamma)) / alpha
        t1 = (-beta - math.sqrt(math.pow(beta, 2) - alpha * gamma)) / alpha

        A0 = math.radians(lat1)
        A1 = math.radians(lon1)
        xlatA = A0 + (math.radians(lat2) - math.radians(lat1)) * t0
        xlonA = A1 + (math.radians(lon2) - math.radians(lon1)) * t0
        xlatB = A0 + (math.radians(lat2) - math.radians(lat1)) * t1
        xlonB = A1 + (math.radians(lon2) - math.radians(lon1)) * t1

        intersections.append((math.degrees(xlatA), math.degrees(xlonA)))
        intersections.append((math.degrees(xlatB), math.degrees(xlonB)))
    return intersections


def is_point_inside_paa(ue_data, computed_area_tan, point):
    ue_point_distance = getDistanceBetweenPoints(ue_data['gps']['lat'],
                                                 ue_data['gps']['lon'],
                                                 point['lat'], point['lon'])
    ue_point_bearing = getBearingBetweenPoints(ue_data['gps']['lat'],
                                               ue_data['gps']['lon'],
                                               point['lat'], point['lon'])

    if ue_point_distance > (ue_data['gps']['acc'] + 1):
        return False

    ue_point_bearing = ue_point_bearing % 360
    ue_point_bearing = (ue_point_bearing + 360) % 360
    if (ue_point_bearing > 180):
        ue_point_bearing -= 360

    angle1 = computed_area_tan[0] % 360
    angle1 = (angle1 + 360) % 360
    if (angle1 > 180):
        angle1 -= 360
    angle2 = computed_area_tan[1] % 360
    angle2 = (angle2 + 360) % 360
    if (angle2 > 180):
        angle2 -= 360

    if angle1 > 0 and angle2 < 0:
        if (ue_point_bearing > angle1 and ue_point_bearing > angle2) or (
                ue_point_bearing < angle1 and ue_point_bearing < angle2):
            return True
        else:
            return False
    else:
        if (ue_point_bearing > angle1 and ue_point_bearing < angle2):
            return True
        else:
            return False

    return False

    # point2 = osmutils.getPointFromPointDistanceAndBearing(
    #     ue_data['gps']['lat'], ue_data['gps']['lon'], paa_circle_radius,
    #     computed_area_tan[0])
    # point1 = osmutils.getPointFromPointDistanceAndBearing(
    #     ue_data['gps']['lat'], ue_data['gps']['lon'], paa_circle_radius,
    #     computed_area_tan[1])


def get_shifted_way_segments(ue_lat, ue_lon, ue_acc, osm_elements,
                             osm_way_nodes, way_tags):
    way_json = []

    # compose way nodes, 'main' and 'segments'
    for i in range(len(osm_way_nodes) - 1):
        start_node_lat = osm_elements[osm_way_nodes[i]]['lat']
        start_node_lon = osm_elements[osm_way_nodes[i]]['lon']
        end_node_lat = osm_elements[osm_way_nodes[i + 1]]['lat']
        end_node_lon = osm_elements[osm_way_nodes[i + 1]]['lon']

        bearing = getBearingBetweenPoints(start_node_lat, start_node_lon,
                                          end_node_lat, end_node_lon)
        intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc,
                                              start_node_lat, start_node_lon,
                                              end_node_lat, end_node_lon)

        way_dict = {
            'tags': way_tags,
            'wayseg0': {
                'points': [{
                    'lat': start_node_lat,
                    'lon': start_node_lon
                }, {
                    'lat': end_node_lat,
                    'lon': end_node_lon
                }],
                'intersections': [{
                    'lat': x[0],
                    'lon': x[1]
                } for x in intersecs],
            }
        }

        j = 1
        for lane_width, shifting_bearing in itertools.product([2.4, 4.0],
                                                              [-90, 90]):
            wayseg_str = 'wayseg' + str(j)
            shifted_wayseg_nodes = []
            shifted_wayseg_nodes.append(
                getPointFromPointDistanceAndBearing(
                    start_node_lat, start_node_lon, lane_width,
                    bearing + shifting_bearing))
            shifted_wayseg_nodes.append(
                getPointFromPointDistanceAndBearing(end_node_lat, end_node_lon,
                                                    lane_width, bearing +
                                                    shifting_bearing))
            intersections = getRoadCircleIntersection(
                ue_lat, ue_lon, ue_acc, shifted_wayseg_nodes[0][0],
                shifted_wayseg_nodes[0][1], shifted_wayseg_nodes[1][0],
                shifted_wayseg_nodes[1][1])
            way_dict[wayseg_str] = {
                'points': [{
                    'lat': shifted_wayseg_nodes[0][0],
                    'lon': shifted_wayseg_nodes[0][1]
                }, {
                    'lat': shifted_wayseg_nodes[1][0],
                    'lon': shifted_wayseg_nodes[1][1]
                }],
                'intersections': [{
                    'lat': x[0],
                    'lon': x[1]
                } for x in intersections],
            }

            j += 1

        way_json.append(way_dict)

    return way_json


def processUELocation(lat, lon, acc):
    ue_lat = float(lat)
    ue_lon = float(lon)
    ue_acc = float(acc)

    google_road_query = "https://roads.googleapis.com/v1/nearestRoads?points="
    google_road_query += str(ue_lat) + "," + str(
        ue_lon) + "&key=AIzaSyD5hxWwH4oYIt6Us5DJgdXgO0jkLIYEz3k"

    # start = time.time()
    # google_response = requests.get(google_road_query)
    # elapsed = (time.time() - start)
    # print(elapsed * 1000)

    j, k = {'ways': []}, {}
    distance_delta = 5
    while len(j['ways']) == 0:
        osm_query = "[out:json];(way(around:" + str(
            ue_acc + distance_delta) + "," + str(ue_lat) + "," + str(ue_lon)
        osm_query += ")[\"highway\"~\"^(primary|secondary|tertiary|residential|service|motorway)$\"];>;);out;\n"
        # start = time.time()
        interpreter_process = subprocess.run(
            ["/home/gio/osm-3s_v0.7.55/cgi-bin/interpreter"],
            universal_newlines=True,
            input=osm_query,
            check=True,
            stdout=subprocess.PIPE)
        # elapsed = (time.time() - start)
        # print(elapsed * 1000)

        response_json = str(interpreter_process.stdout).split("\n",
                                                              2)[2].rstrip()
        j, k = process_json_response(response_json, ue_lat, ue_lon, ue_acc)
        distance_delta += 1
    return j, k


def process_json_response(response_json, ue_lat, ue_lon, ue_acc):
    out_json = {}
    out_ways_json = []
    out_ways_json_temp = []
    out_json['ue'] = {'lat': ue_lat, 'lon': ue_lon, 'acc': ue_acc}
    osm_json = json.loads(response_json)
    osm_elements = {}
    intersection_count = 0

    for osm_element in osm_json['elements']:
        osm_elements[osm_element['id']] = osm_element

        if osm_element['type'] == 'way':
            # json response variables
            ways_entry_json = {}
            way_json = []

            osm_way_nodes = osm_element['nodes']
            way_nodes = []
            way_seg_nodes = {}

            # create json dict with all way nodes
            for osm_way_node in osm_way_nodes:
                node_lat = osm_elements[osm_way_node]['lat']
                node_lon = osm_elements[osm_way_node]['lon']
                way_nodes.append((node_lat, node_lon))

                # json response build
                way_nodes_dic = {'lat': node_lat, 'lon': node_lon}
                way_json.append(way_nodes_dic)

                d = getDistanceBetweenPoints(ue_lat, ue_lon, node_lat,
                                             node_lon)
                way_seg_nodes[d] = (node_lat, node_lon)

            # perform road segment shifting
            # print(
            #     json.dumps(
            #         get_shifted_way_segments(ue_lat, ue_lon, ue_acc,
            #                                  osm_elements, osm_way_nodes,
            #                                  osm_element['tags'])))
            # print(
            #     get_shifted_way_segments(ue_lat, ue_lon, ue_acc, osm_elements,
            #                              osm_way_nodes, osm_element['tags']))
            # input('next temp json')
            way_json_temp = get_shifted_way_segments(ue_lat, ue_lon, ue_acc,
                                                     osm_elements,
                                                     osm_way_nodes,
                                                     osm_element['tags'])
            # center road segment processing
            way_seg_nodes = sorted(way_seg_nodes.items())
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc,
                                                  way_seg_nodes[0][1][0],
                                                  way_seg_nodes[0][1][1],
                                                  way_seg_nodes[1][1][0],
                                                  way_seg_nodes[1][1][1])

            # json response build
            wayseg_points_json = []

            wayseg_points_json.append({
                'lat': way_seg_nodes[0][1][0],
                'lon': way_seg_nodes[0][1][1]
            })
            wayseg_points_json.append({
                'lat': way_seg_nodes[1][1][0],
                'lon': way_seg_nodes[1][1][1]
            })

            wayseg_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg_intersections_json.append({
                    'lat': intersecs[0][0],
                    'lon': intersecs[0][1]
                })
                wayseg_intersections_json.append({
                    'lat': intersecs[1][0],
                    'lon': intersecs[1][1]
                })

            # shifted road segment1 processing
            bearing = getBearingBetweenPoints(way_seg_nodes[0][1][0],
                                              way_seg_nodes[0][1][1],
                                              way_seg_nodes[1][1][0],
                                              way_seg_nodes[1][1][1])
            shifted_way_seg1_nodes = []
            shifted_way_seg1_nodes.append(
                getPointFromPointDistanceAndBearing(way_seg_nodes[0][1][0],
                                                    way_seg_nodes[0][1][1],
                                                    2.4, bearing - 90))
            shifted_way_seg1_nodes.append(
                getPointFromPointDistanceAndBearing(way_seg_nodes[1][1][0],
                                                    way_seg_nodes[1][1][1],
                                                    2.4, bearing - 90))
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc,
                                                  shifted_way_seg1_nodes[0][0],
                                                  shifted_way_seg1_nodes[0][1],
                                                  shifted_way_seg1_nodes[1][0],
                                                  shifted_way_seg1_nodes[1][1])

            # json response build
            wayseg1_points_json = []
            wayseg1_points_json.append({
                'lat': shifted_way_seg1_nodes[0][0],
                'lon': shifted_way_seg1_nodes[0][1]
            })
            wayseg1_points_json.append({
                'lat': shifted_way_seg1_nodes[1][0],
                'lon': shifted_way_seg1_nodes[1][1]
            })

            wayseg1_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg1_intersections_json.append({
                    'lat': intersecs[0][0],
                    'lon': intersecs[0][1]
                })
                wayseg1_intersections_json.append({
                    'lat': intersecs[1][0],
                    'lon': intersecs[1][1]
                })

            # ----------------------------------------------------------------
            shifted_way_seg3_nodes = []
            shifted_way_seg3_nodes.append(
                getPointFromPointDistanceAndBearing(way_seg_nodes[0][1][0],
                                                    way_seg_nodes[0][1][1],
                                                    4.0, bearing - 90))
            shifted_way_seg3_nodes.append(
                getPointFromPointDistanceAndBearing(way_seg_nodes[1][1][0],
                                                    way_seg_nodes[1][1][1],
                                                    4.0, bearing - 90))
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc,
                                                  shifted_way_seg3_nodes[0][0],
                                                  shifted_way_seg3_nodes[0][1],
                                                  shifted_way_seg3_nodes[1][0],
                                                  shifted_way_seg3_nodes[1][1])

            # json response build
            wayseg3_points_json = []
            wayseg3_points_json.append({
                'lat': shifted_way_seg3_nodes[0][0],
                'lon': shifted_way_seg3_nodes[0][1]
            })
            wayseg3_points_json.append({
                'lat': shifted_way_seg3_nodes[1][0],
                'lon': shifted_way_seg3_nodes[1][1]
            })

            wayseg3_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg3_intersections_json.append({
                    'lat': intersecs[0][0],
                    'lon': intersecs[0][1]
                })
                wayseg3_intersections_json.append({
                    'lat': intersecs[1][0],
                    'lon': intersecs[1][1]
                })

            shifted_way_seg4_nodes = []
            shifted_way_seg4_nodes.append(
                getPointFromPointDistanceAndBearing(way_seg_nodes[0][1][0],
                                                    way_seg_nodes[0][1][1],
                                                    4.0, bearing + 90))
            shifted_way_seg4_nodes.append(
                getPointFromPointDistanceAndBearing(way_seg_nodes[1][1][0],
                                                    way_seg_nodes[1][1][1],
                                                    4.0, bearing + 90))
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc,
                                                  shifted_way_seg4_nodes[0][0],
                                                  shifted_way_seg4_nodes[0][1],
                                                  shifted_way_seg4_nodes[1][0],
                                                  shifted_way_seg4_nodes[1][1])

            # json response build
            wayseg4_points_json = []
            wayseg4_points_json.append({
                'lat': shifted_way_seg4_nodes[0][0],
                'lon': shifted_way_seg4_nodes[0][1]
            })
            wayseg4_points_json.append({
                'lat': shifted_way_seg4_nodes[1][0],
                'lon': shifted_way_seg4_nodes[1][1]
            })

            wayseg4_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg4_intersections_json.append({
                    'lat': intersecs[0][0],
                    'lon': intersecs[0][1]
                })
                wayseg4_intersections_json.append({
                    'lat': intersecs[1][0],
                    'lon': intersecs[1][1]
                })

            # ----------------------------------------------------------------
            # shifted road segment2 processing
            shifted_way_seg2_nodes = []
            shifted_way_seg2_nodes.append(
                getPointFromPointDistanceAndBearing(way_seg_nodes[0][1][0],
                                                    way_seg_nodes[0][1][1],
                                                    2.4, bearing + 90))
            shifted_way_seg2_nodes.append(
                getPointFromPointDistanceAndBearing(way_seg_nodes[1][1][0],
                                                    way_seg_nodes[1][1][1],
                                                    2.4, bearing + 90))
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc,
                                                  shifted_way_seg2_nodes[0][0],
                                                  shifted_way_seg2_nodes[0][1],
                                                  shifted_way_seg2_nodes[1][0],
                                                  shifted_way_seg2_nodes[1][1])

            # json response build
            wayseg2_points_json = []
            wayseg2_points_json.append({
                'lat': shifted_way_seg2_nodes[0][0],
                'lon': shifted_way_seg2_nodes[0][1]
            })
            wayseg2_points_json.append({
                'lat': shifted_way_seg2_nodes[1][0],
                'lon': shifted_way_seg2_nodes[1][1]
            })

            wayseg2_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg2_intersections_json.append({
                    'lat': intersecs[0][0],
                    'lon': intersecs[0][1]
                })
                wayseg2_intersections_json.append({
                    'lat': intersecs[1][0],
                    'lon': intersecs[1][1]
                })

            ways_entry_json['tags'] = osm_element['tags']
            ways_entry_json['way'] = way_json
            ways_entry_json['wayseg0'] = {
                'points': wayseg_points_json,
                'intersections': wayseg_intersections_json
            }
            ways_entry_json['wayseg1'] = {
                'points': wayseg1_points_json,
                'intersections': wayseg1_intersections_json
            }
            ways_entry_json['wayseg2'] = {
                'points': wayseg2_points_json,
                'intersections': wayseg2_intersections_json
            }
            ways_entry_json['wayseg3'] = {
                'points': wayseg3_points_json,
                'intersections': wayseg3_intersections_json
            }
            ways_entry_json['wayseg4'] = {
                'points': wayseg4_points_json,
                'intersections': wayseg4_intersections_json
            }
            out_ways_json.append(ways_entry_json)
            out_ways_json_temp.append({'ways': way_json_temp})
            # print(json.dumps(ways_entry_json, indent=4))
            # print(json.dumps(way_json_temp, indent=4))
            # input('next way entry...')

    out_json['ways'] = out_ways_json
    out_json['ue']['intersection_count'] = intersection_count
    return out_json, out_ways_json_temp


def get_road_segment_gdf(way_json):
    dataframes = []
    for way in way_json['ways']:
        way_seg_nodes = [[p['lat'], p['lon']]
                         for p in way['wayseg0']['points']]
        shifted_way_seg1_nodes = [[p['lat'], p['lon']]
                                  for p in way['wayseg1']['points']]
        shifted_way_seg2_nodes = [[p['lat'], p['lon']]
                                  for p in way['wayseg2']['points']]
        shifted_way_seg3_nodes = [[p['lat'], p['lon']]
                                  for p in way['wayseg3']['points']]
        shifted_way_seg4_nodes = [[p['lat'], p['lon']]
                                  for p in way['wayseg4']['points']]

        # Construct geopandas dataframe 'wayseg0_wayseg1'
        poly_tuple = ((way_seg_nodes[0][0], way_seg_nodes[0][1]),
                      (way_seg_nodes[1][0],
                       way_seg_nodes[1][1]), (shifted_way_seg1_nodes[1][0],
                                              shifted_way_seg1_nodes[1][1]),
                      (shifted_way_seg1_nodes[0][0],
                       shifted_way_seg1_nodes[0][1]), (way_seg_nodes[0][0],
                                                       way_seg_nodes[0][1]))
        way_seg0_way_seg1_wkt = 'POLYGON ((' + str(
            str(poly_tuple).replace(',', '').replace(')', ',').replace(
                '(', ''))
        way_seg0_way_seg1_wkt = way_seg0_way_seg1_wkt[:-2] + '))'

        # Construct geopandas dataframe 'wayseg1_wayseg3'
        poly_tuple = ((shifted_way_seg1_nodes[0][0],
                       shifted_way_seg1_nodes[0][1]),
                      (shifted_way_seg1_nodes[1][0],
                       shifted_way_seg1_nodes[1][1]),
                      (shifted_way_seg3_nodes[1][0],
                       shifted_way_seg3_nodes[1][1]),
                      (shifted_way_seg3_nodes[0][0],
                       shifted_way_seg3_nodes[0][1]),
                      (shifted_way_seg1_nodes[0][0],
                       shifted_way_seg1_nodes[0][1]))
        way_seg1_way_seg3_wkt = 'POLYGON ((' + str(
            str(poly_tuple).replace(',', '').replace(')', ',').replace(
                '(', ''))
        way_seg1_way_seg3_wkt = way_seg1_way_seg3_wkt[:-2] + '))'

        # Construct geopandas dataframe 'wayseg2_wayseg4'
        poly_tuple = ((shifted_way_seg2_nodes[0][0],
                       shifted_way_seg2_nodes[0][1]),
                      (shifted_way_seg2_nodes[1][0],
                       shifted_way_seg2_nodes[1][1]),
                      (shifted_way_seg4_nodes[1][0],
                       shifted_way_seg4_nodes[1][1]),
                      (shifted_way_seg4_nodes[0][0],
                       shifted_way_seg4_nodes[0][1]),
                      (shifted_way_seg2_nodes[0][0],
                       shifted_way_seg2_nodes[0][1]))
        way_seg2_way_seg4_wkt = 'POLYGON ((' + str(
            str(poly_tuple).replace(',', '').replace(')', ',').replace(
                '(', ''))
        way_seg2_way_seg4_wkt = way_seg2_way_seg4_wkt[:-2] + '))'

        # Construct geopandas dataframe 'wayseg0_wayseg2'
        poly_tuple = ((way_seg_nodes[0][0], way_seg_nodes[0][1]),
                      (way_seg_nodes[1][0],
                       way_seg_nodes[1][1]), (shifted_way_seg2_nodes[1][0],
                                              shifted_way_seg2_nodes[1][1]),
                      (shifted_way_seg2_nodes[0][0],
                       shifted_way_seg2_nodes[0][1]), (way_seg_nodes[0][0],
                                                       way_seg_nodes[0][1]))
        way_seg0_way_seg2_wkt = 'POLYGON ((' + str(
            str(poly_tuple).replace(',', '').replace(')', ',').replace(
                '(', ''))
        way_seg0_way_seg2_wkt = way_seg0_way_seg2_wkt[:-2] + '))'

        # Geopandas dataframes
        way_name = ''
        if 'name' in way['tags']:
            way_name = way['tags']['name']
        df = pd.DataFrame({
            'way_name':
            way_name,
            'polygon_name': [
                'way_seg0_way_seg1', 'way_seg0_way_seg2', 'way_seg1_way_seg3',
                'way_seg2_way_seg4'
            ],
            'geometry': [
                way_seg0_way_seg1_wkt, way_seg0_way_seg2_wkt,
                way_seg1_way_seg3_wkt, way_seg2_way_seg4_wkt
            ]
        })

        df['geometry'] = df['geometry'].apply(shapely.wkt.loads)
        dataframes.append(df)

    if len(dataframes) > 0:
        df = pd.concat(dataframes, ignore_index=True, sort=False)
        gdf = geopandas.GeoDataFrame(df, geometry='geometry')
        return gdf
    return geopandas.GeoDataFrame()


def get_paa_polygon_gdf(ue_data, computed_area_tan, arc):
    polygon_points = []
    polygon_points.append((ue_data['gps']['lat'], ue_data['gps']['lon']))
    delta_bear = arc / 64
    for i in range(64):
        polygon_points.append(
            getPointFromPointDistanceAndBearing(
                ue_data['gps']['lat'], ue_data['gps']['lon'],
                ue_data['gps']['acc'],
                computed_area_tan[1] + (i * delta_bear)))

    polygon_points.append((ue_data['gps']['lat'], ue_data['gps']['lon']))

    if arc == 0:
        paa_wkt = 'EMPTY'
    else:
        paa_wkt = 'POLYGON ((' + str(
            str(polygon_points).replace(',', '').replace(')', ',').replace(
                '[', '').replace('(', ''))
        paa_wkt = paa_wkt[:-2] + '))'

    if arc == 0:
        df = geopandas.GeoSeries(shapely.geometry.Polygon([]))
        # print('||||||||||||||||||||||||||||||||||||||||||||||||||||')
        # print(df)
        gdf = geopandas.GeoDataFrame(geometry=df)
    else:
        df = pd.DataFrame({'geometry': [paa_wkt]})
        df['geometry'] = df['geometry'].apply(shapely.wkt.loads)

        gdf = geopandas.GeoDataFrame(df, geometry='geometry')

    # print('------------------------------------------------------------')
    # print(gdf)
    return gdf

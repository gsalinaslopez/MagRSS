import math
import json
import subprocess

_EARTH_RADIUS = 6371007.2

def getDistanceBetweenPoints(lat1, lon1, lat2, lon2):
    deltaLat = math.radians(lat2 - lat1)
    deltaLon = math.radians(lon2 - lon1)
    a = math.sin(deltaLat / 2) * math.sin(deltaLat / 2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(deltaLon / 2) * math.sin(deltaLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS  * c

def getBearingBetweenPoints(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    deltaLon = lon2 - lon1
    y = math.sin(deltaLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(deltaLon)
    return math.degrees(math.atan2(y, x))

def getPointFromPointDistanceAndBearing(lat, lon, dist, bearing):
    lat = math.radians(lat)
    lon = math.radians(lon)
    bearing = math.radians(bearing)
    dr = dist/_EARTH_RADIUS 

    dest_lat = math.asin(math.sin(lat) * math.cos(dr) + math.cos(lat) * math.sin(dr) * math.cos(bearing))
    atan2_y = math.sin(bearing) * math.sin(dr) * math.cos(lat)
    atan2_x = math.cos(dr) - math.sin(lat) * math.sin(dest_lat)
    dest_lon = lon + math.atan2(atan2_y, atan2_x)
    return (math.degrees(dest_lat), (math.degrees(dest_lon) + 540)%360 - 180)

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
    sq_val = math.pow(beta,2) - alpha * gamma
    
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

def processUELocation(lat, lon, acc): 
    
    ue_lat = float(lat)
    ue_lon = float(lon)
    ue_acc = float(acc)
    
    out_json = {}
    out_ways_json = []

    google_road_query = "https://roads.googleapis.com/v1/nearestRoads?points="
    google_road_query += str(ue_lat) + "," + str(ue_lon) + "&key=AIzaSyD5hxWwH4oYIt6Us5DJgdXgO0jkLIYEz3k"  

    #start = time.time()
    #google_response = requests.get(google_road_query)
    #elapsed = (time.time() - start)
    #print(elapsed * 1000)

    out_json['ue'] = {'lat' : ue_lat, 'lon' : ue_lon, 'acc' : ue_acc}

    osm_query = "[out:json];(way(around:" + str(ue_acc) + "," + str(ue_lat) + "," + str(ue_lon)
    osm_query += ")[\"highway\"~\"^(primary|secondary|tertiary|residential|service|motorway)$\"];>;);out;\n"
    #start = time.time()
    interpreter_process = subprocess.run(["/home/gio/osm-3s_v0.7.55/cgi-bin/interpreter"], universal_newlines=True, input=osm_query, check=True, stdout=subprocess.PIPE)
    #elapsed = (time.time() - start)
    #print(elapsed * 1000)

    response_json = str(interpreter_process.stdout).split("\n",2)[2].rstrip()
    
    osm_json = json.loads(response_json)
    osm_elements = {}
    intersection_count = 0

    for osm_element in osm_json['elements']:
        osm_elements[osm_element['id']] = osm_element

        if osm_element['type'] == 'way':
            #json response variables
            ways_entry_json = {}
            way_json = []
            #wayseg_json = {}


            osm_way_nodes = osm_element['nodes']
            way_nodes = []
            way_seg_nodes = {}
            
            for osm_way_node in osm_way_nodes:
                node_lat = osm_elements[osm_way_node]['lat']
                node_lon = osm_elements[osm_way_node]['lon']
                way_nodes.append((node_lat, node_lon))

                #json response build
                way_nodes_dic = {'lat' : node_lat, 'lon' : node_lon}
                way_json.append(way_nodes_dic)

                d = getDistanceBetweenPoints(ue_lat, ue_lon, node_lat, node_lon)
                way_seg_nodes[d] = (node_lat, node_lon)


            #center road segment processing
            way_seg_nodes = sorted(way_seg_nodes.items())
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc, way_seg_nodes[0][1][0], way_seg_nodes[0][1][1], way_seg_nodes[1][1][0], way_seg_nodes[1][1][1])
            
            #json response build
            wayseg_points_json = []

            wayseg_points_json.append({'lat' : way_seg_nodes[0][1][0], 'lon' : way_seg_nodes[0][1][1]})
            wayseg_points_json.append({'lat' : way_seg_nodes[1][1][0], 'lon' : way_seg_nodes[1][1][1]})
            
            wayseg_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg_intersections_json.append({'lat' : intersecs[0][0], 'lon' : intersecs[0][1]})
                wayseg_intersections_json.append({'lat' : intersecs[1][0], 'lon' : intersecs[1][1]})

            #shifted road segment1 processing
            bearing = getBearingBetweenPoints(way_seg_nodes[0][1][0], way_seg_nodes[0][1][1], way_seg_nodes[1][1][0], way_seg_nodes[1][1][1])
            shifted_way_seg1_nodes = []
            shifted_way_seg1_nodes.append(getPointFromPointDistanceAndBearing(way_seg_nodes[0][1][0], way_seg_nodes[0][1][1], 2.4, bearing - 90))
            shifted_way_seg1_nodes.append(getPointFromPointDistanceAndBearing(way_seg_nodes[1][1][0], way_seg_nodes[1][1][1], 2.4, bearing - 90))
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc, shifted_way_seg1_nodes[0][0], shifted_way_seg1_nodes[0][1], shifted_way_seg1_nodes[1][0], shifted_way_seg1_nodes[1][1])
            
            #json response build
            wayseg1_points_json = []
            wayseg1_points_json.append({'lat' : shifted_way_seg1_nodes[0][0], 'lon' : shifted_way_seg1_nodes[0][1]})
            wayseg1_points_json.append({'lat' : shifted_way_seg1_nodes[1][0], 'lon' : shifted_way_seg1_nodes[1][1]})
            
            wayseg1_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg1_intersections_json.append({'lat' : intersecs[0][0], 'lon' : intersecs[0][1]})
                wayseg1_intersections_json.append({'lat' : intersecs[1][0], 'lon' : intersecs[1][1]})

            #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            #shifted road segment3 processing
            bearing = getBearingBetweenPoints(way_seg_nodes[0][1][0], way_seg_nodes[0][1][1], way_seg_nodes[1][1][0], way_seg_nodes[1][1][1])
            shifted_way_seg3_nodes = []
            shifted_way_seg3_nodes.append(getPointFromPointDistanceAndBearing(way_seg_nodes[0][1][0], way_seg_nodes[0][1][1], 4.8, bearing - 90))
            shifted_way_seg3_nodes.append(getPointFromPointDistanceAndBearing(way_seg_nodes[1][1][0], way_seg_nodes[1][1][1], 4.8, bearing - 90))
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc, shifted_way_seg3_nodes[0][0], shifted_way_seg3_nodes[0][1], shifted_way_seg3_nodes[1][0], shifted_way_seg3_nodes[1][1])
            
            #json response build
            wayseg3_points_json = []
            wayseg3_points_json.append({'lat' : shifted_way_seg3_nodes[0][0], 'lon' : shifted_way_seg3_nodes[0][1]})
            wayseg3_points_json.append({'lat' : shifted_way_seg3_nodes[1][0], 'lon' : shifted_way_seg3_nodes[1][1]})
            #print(wayseg3_points_json)
            #print('**********************************')
            wayseg3_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg3_intersections_json.append({'lat' : intersecs[0][0], 'lon' : intersecs[0][1]})
                wayseg3_intersections_json.append({'lat' : intersecs[1][0], 'lon' : intersecs[1][1]})
            
            #shifted road segment4 processing
            bearing = getBearingBetweenPoints(way_seg_nodes[0][1][0], way_seg_nodes[0][1][1], way_seg_nodes[1][1][0], way_seg_nodes[1][1][1])
            shifted_way_seg4_nodes = []
            shifted_way_seg4_nodes.append(getPointFromPointDistanceAndBearing(way_seg_nodes[0][1][0], way_seg_nodes[0][1][1], 4.8, bearing + 90))
            shifted_way_seg4_nodes.append(getPointFromPointDistanceAndBearing(way_seg_nodes[1][1][0], way_seg_nodes[1][1][1], 4.8, bearing + 90))
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc, shifted_way_seg4_nodes[0][0], shifted_way_seg4_nodes[0][1], shifted_way_seg4_nodes[1][0], shifted_way_seg4_nodes[1][1])
            
            #json response build
            wayseg4_points_json = []
            wayseg4_points_json.append({'lat' : shifted_way_seg4_nodes[0][0], 'lon' : shifted_way_seg4_nodes[0][1]})
            wayseg4_points_json.append({'lat' : shifted_way_seg4_nodes[1][0], 'lon' : shifted_way_seg4_nodes[1][1]})
            
            wayseg4_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg4_intersections_json.append({'lat' : intersecs[0][0], 'lon' : intersecs[0][1]})
                wayseg4_intersections_json.append({'lat' : intersecs[1][0], 'lon' : intersecs[1][1]})
            #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
            #shifted road segment2 processing
            shifted_way_seg2_nodes = []
            shifted_way_seg2_nodes.append(getPointFromPointDistanceAndBearing(way_seg_nodes[0][1][0], way_seg_nodes[0][1][1], 2.4, bearing + 90))
            shifted_way_seg2_nodes.append(getPointFromPointDistanceAndBearing(way_seg_nodes[1][1][0], way_seg_nodes[1][1][1], 2.4, bearing + 90))
            intersecs = getRoadCircleIntersection(ue_lat, ue_lon, ue_acc, shifted_way_seg2_nodes[0][0], shifted_way_seg2_nodes[0][1], shifted_way_seg2_nodes[1][0], shifted_way_seg2_nodes[1][1])
            
            #json response build
            wayseg2_points_json = []
            wayseg2_points_json.append({'lat' : shifted_way_seg2_nodes[0][0], 'lon' : shifted_way_seg2_nodes[0][1]})
            wayseg2_points_json.append({'lat' : shifted_way_seg2_nodes[1][0], 'lon' : shifted_way_seg2_nodes[1][1]})
            
            wayseg2_intersections_json = []
            if (len(intersecs) >= 2):
                intersection_count += len(intersecs)
                wayseg2_intersections_json.append({'lat' : intersecs[0][0], 'lon' : intersecs[0][1]})
                wayseg2_intersections_json.append({'lat' : intersecs[1][0], 'lon' : intersecs[1][1]})

            ways_entry_json['way'] = way_json
            ways_entry_json['wayseg'] = {'points' : wayseg_points_json, 'intersections' : wayseg_intersections_json}
            ways_entry_json['wayseg1'] = {'points' : wayseg1_points_json, 'intersections' : wayseg1_intersections_json}
            ways_entry_json['wayseg2'] = {'points' : wayseg2_points_json, 'intersections' : wayseg2_intersections_json}
            ways_entry_json['wayseg3'] = {'points' : wayseg3_points_json, 'intersections' : wayseg3_intersections_json}
            ways_entry_json['wayseg4'] = {'points' : wayseg4_points_json, 'intersections' : wayseg4_intersections_json}
            out_ways_json.append(ways_entry_json)
    
    out_json['ways'] = out_ways_json
    out_json['ue']['intersection_count'] = intersection_count
    return out_json
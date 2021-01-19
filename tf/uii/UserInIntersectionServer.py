import socket
import sys
import json
import math
import datetime


BS = {'243' : {'lat' : 24.787113, 'lon' : 121.001955}, '244' : {'lat' : 24.784410, 'lon' : 120.997406}, '245' : {'lat' : 24.784410, 'lon' : 120.997406}, '246' : {'lat' : 24.787461, 'lon' : 120.995878}, '247' : {'lat' : 24.787461, 'lon' : 120.995878}, '248' : {'lat' : 24.787461, 'lon' : 120.995878}}
#{'lat' : 24.786651, 'lon' : 121.001796}

def stepsToKilometer(steps):
    return steps * 0.0008128

def getBearing(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    lon_diff = lon2 - lon1
    y = math.sin(lon_diff) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon_diff)
    return math.degrees(math.atan2(y, x))

def getPointFromPointDistanceAndBearing(lat, lon, dist, bearing):
    earth_radius = 6371

    lat = math.radians(lat)
    lon = math.radians(lon)
    bearing = math.radians(bearing)

    dr = dist/earth_radius
    dest_lat = math.asin(math.sin(lat) * math.cos(dr) + math.cos(lat) * math.sin(dr) * math.cos(bearing))
    atan2_y = math.sin(bearing) * math.sin(dr) * math.cos(lat)
    atan2_x = math.cos(dr) - math.sin(lat) * math.sin(dest_lat)
    dest_lon = lon + math.atan2(atan2_y, atan2_x)
    return (math.degrees(dest_lat), (math.degrees(dest_lon) + 540)%360 - 180)

def getConflictBaseStationOrientation(a, b, readings, pci, actual_orientation, conflict_orientation):
    if b >=1:
        tmp = b + 2
    else:
        tmp = b + 1

    prev_coord = BS[str(pci)]
    orientation = actual_orientation


    for k in readings[tmp-1].keys():
        if BS[str(k)] == prev_coord:
            if readings[tmp-1][k] == conflict_orientation:
                print("conflict in orientations between current read and " + str(tmp), file = log_server)
                orientation = "static"
                #return orientation

    for i in range(a, b + 1):
        """
        for k in readings[i].keys():
            if BS[str(k)] == prev_coord:
                if readings[i][k] == conflict_orientation:
                    print("conflict in orientations between current read and " + str(i + 1), file = log_server)
                    orientation = "static"
                    #return orientation
        """

        if pci in readings[i]:
            if readings[i][pci] == conflict_orientation:
                print("conflict in orientations between current read and " + str(i + 1), file = log_server)
                orientation = "static"
                #return orientation
    return orientation

def getTowardsBaseStationTangentPoints(pci, client_last_known_lat, client_last_known_lon):
    print("towards: " + str(pci), file = log_server)

    dst_bs = BS[str(pci)]
    dst_bs_bearing = getBearing(client_last_known_lat, client_last_known_lon, dst_bs['lat'], dst_bs['lon'])
    return (dst_bs_bearing - 90, dst_bs_bearing + 90)

def getAwayBaseStationTangentPoints(pci, client_last_known_lat, client_last_known_lon):
    print("away from: " + str(pci), file = log_server)

    dst_bs = BS[str(pci)]
    dst_bs_bearing = getBearing(client_last_known_lat, client_last_known_lon, dst_bs['lat'], dst_bs['lon'])
    if (dst_bs_bearing > 0):
        dst_bs_bearing = dst_bs_bearing - 180
    else:
        dst_bs_bearing = dst_bs_bearing + 180
    return (dst_bs_bearing - 90, dst_bs_bearing + 90)

def getOverlapFromTanPoints(tangent_points1, tangent_points2):
    print("comparing areas " + str(tangent_points1) + " and " + str(tangent_points2), file = log_server)
    if tangent_points1[0] == 0 and tangent_points1[0] == 0:
        return tangent_points2
    elif tangent_points1[0] == 360 and tangent_points1[0] == 360:
        return tangent_points1
    elif tangent_points2[0] == 360 and tangent_points2[0] == 360:
        return tangent_points2
    #normalize to 0 - 360 range
    #"""
    if tangent_points1[0] < -180:
        tangent_points1 = (360 + tangent_points1[0], tangent_points1[1])
    elif tangent_points1[0] > 180:
        tangent_points1 = (tangent_points1[0] - 360, tangent_points1[1])

    if tangent_points1[1] < -180:
        tangent_points1 = (tangent_points1[0], 360 + tangent_points1[1])
    elif tangent_points1[1] > 180:
        tangent_points1 = (tangent_points1[0], tangent_points1[1] - 360)

    if tangent_points2[0] < -180:
        tangent_points2 = (360 + tangent_points2[0], tangent_points2[1])
    elif tangent_points2[0] > 180:
        tangent_points2 = (tangent_points2[0] - 360, tangent_points2[1])

    if tangent_points2[1] < -180:
        tangent_points2 = (tangent_points2[0], 360 + tangent_points2[1])
    elif tangent_points2[1] > 180:
        tangent_points2 = (tangent_points2[0], tangent_points2[1] - 360)

    #"""
    
    first = tangent_points1[0] if (tangent_points1[0] > tangent_points2[0]) else tangent_points2[0]
    second = tangent_points1[1] if (tangent_points1[1] < tangent_points2[1]) else tangent_points2[1]
    return (first, second)

if __name__ == "__main__":
    UDP_IP = "127.0.0.1"
    UDP_PORT = int(sys.argv[2])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    center_steps = 0
    radius = 0
    client_last_known_location = {}
    client_last_known_cell = {}

    previous_readings = []
    prev_reading_count = 0
    prev_prev_reading_count = 0

    backup_area = []
    backup_area_count = 0
    count = 0
    out_count = 0

    log_rsrp = open(sys.argv[1] + '_rsrp.txt', 'w')
    log_steps = open(sys.argv[1] + '_steps.txt', 'w')
    log_server = open(sys.argv[1] + '_server.txt', 'w')

    while True:
        data, addr = sock.recvfrom(1024)
        print(data, file = log_server)

        #decode received json packet, clean it up
        decoded = json.loads(data.decode("utf-8"))
        for cell_pci in decoded['cell']:
            if str(cell_pci['pci']) not in BS:
                print("removing unwanted cell " + str(cell_pci))
                decoded['cell'].remove(cell_pci)
        for cell_pci in decoded['cell']:
            if str(cell_pci['pci']) not in BS:
                print("removing unwanted cell " + str(cell_pci))
                decoded['cell'].remove(cell_pci)        
        # Center and last known location updates
        # TODO - center update doesnt mean skip this line
        if count % 60 == 0:
            client_last_known_location = decoded['gps']
            client_last_known_cell = decoded['cell']
            center_steps = int(decoded['steps'])
            print("updating center...\n" + str(client_last_known_location) + " --- " + str(client_last_known_cell), file = log_server)
            print('--------------------------', file = log_server)

        else:
            print(count, file = log_server)

            radius = stepsToKilometer(int(decoded['steps']) - center_steps + 10)
            user_dst = stepsToKilometer(int(decoded['steps']) - center_steps)
            acc = float(decoded['gps']['acc'])
            rsrp_threshold = 3
            computed_area_tan = (0, 0)

            # List union to see if there is a new BS appearing or disappearing
            last_known_pci_list = [d['pci'] for d in client_last_known_cell]
            read_cell_pci_list = [d['pci'] for d in decoded['cell']]
            
            # Update counter for prev and prev_prev readings
            previous_readings.append({})
            prev_reading_count = out_count - 1 if out_count > 1 else 0
            prev_prev_reading_count = out_count - 2 if out_count > 2 else 0

            for read_cell in decoded['cell']:

                # Recently entered into new BS area, asume 'towards'
                if read_cell['pci'] not in last_known_pci_list:
                    #client_last_known_cell.append(read_cell)
                    print("recently entered into " + str(read_cell['pci']), file = log_server)

                    # update readings entry
                    # check if either the prev or prev_prev entries conflict with out decision
                    orientation = getConflictBaseStationOrientation(prev_prev_reading_count, prev_reading_count, previous_readings, read_cell['pci'], "towards", "away")
                    previous_readings[out_count].update({read_cell['pci'] : orientation})

                    if orientation == "towards":
                        tan_points = getTowardsBaseStationTangentPoints(read_cell['pci'], client_last_known_location['lat'], client_last_known_location['lon'])
                    else:
                        print("static at: " + str(read_cell['pci']), file = log_server)
                        #tan_points = computed_area_tan
                        tan_points = (360, 360)

                    computed_area_tan = getOverlapFromTanPoints(computed_area_tan, tan_points)
                    print(computed_area_tan, file = log_server)
                    print('', file = log_server)

                    continue
                
                for last_known_cell in client_last_known_cell:

                    # Recently left BS are, asume 'away'
                    if last_known_cell['pci'] not in read_cell_pci_list:
                        #client_last_known_cell.remove(last_known_cell)
                        print("recently left from " + str(last_known_cell['pci']), file = log_server)

                        # update readings entry
                        # check if either the prev or prev_prev entries conflict with out decision
                        orientation = getConflictBaseStationOrientation(prev_prev_reading_count, prev_reading_count, previous_readings, last_known_cell['pci'], "away", "towards")
                        previous_readings[out_count].update({last_known_cell['pci'] : orientation})

                        if orientation == "away":
                            tan_points = getAwayBaseStationTangentPoints(last_known_cell['pci'], client_last_known_location['lat'], client_last_known_location['lon'])
                        else:
                            print("static at: " + str(last_known_cell['pci']), file = log_server)
                            #tan_points = computed_area_tan
                            tan_points = (360, 360)

                        computed_area_tan = getOverlapFromTanPoints(computed_area_tan, tan_points)
                        print(computed_area_tan, file = log_server)
                        print('', file = log_server)
                        continue
                    elif int(read_cell['pci']) == int(last_known_cell['pci']):
                        print("last cell: " + str(last_known_cell), file = log_server)
                        print("read cell: " + str(read_cell), file = log_server)

                        if int(read_cell['val']) >= int(last_known_cell['val']) + rsrp_threshold:
                            orientation = getConflictBaseStationOrientation(prev_prev_reading_count, prev_reading_count, previous_readings, read_cell['pci'], "towards", "away")
                            previous_readings[out_count].update({read_cell['pci'] : orientation})

                            if orientation == "towards":
                                tan_points = getTowardsBaseStationTangentPoints(read_cell['pci'], client_last_known_location['lat'], client_last_known_location['lon'])
                            else:
                                print("static at: " + str(last_known_cell['pci']), file = log_server)
                                #tan_points = computed_area_tan
                                tan_points = (360, 360)
                            #tan_points = getTowardsBaseStationTangentPoints(read_cell['pci'], client_last_known_location['lat'], client_last_known_location['lon'])
                        elif int(read_cell['val']) <= int(last_known_cell['val']) - rsrp_threshold:
                            orientation = getConflictBaseStationOrientation(prev_prev_reading_count, prev_reading_count, previous_readings, read_cell['pci'], "away", "towards")
                            previous_readings[out_count].update({read_cell['pci'] : orientation})

                            if orientation == "away":
                                tan_points = tan_points = getAwayBaseStationTangentPoints(read_cell['pci'], client_last_known_location['lat'], client_last_known_location['lon'])
                            else:
                                print("static at: " + str(last_known_cell['pci']), file = log_server)
                                #tan_points = computed_area_tan
                                tan_points = (360, 360)
                            #tan_points = getAwayBaseStationTangentPoints(read_cell['pci'], client_last_known_location['lat'], client_last_known_location['lon'])
                        else:
                            previous_readings[out_count].update({read_cell['pci'] : "static"})
                            print("static at: " + str(read_cell['pci']), file = log_server)
                            tan_points = computed_area_tan
                        computed_area_tan = getOverlapFromTanPoints(computed_area_tan, tan_points)
                        print(computed_area_tan, file = log_server)
                        print('', file = log_server)

            # Add current reading for future use
            #previous_readings[out_count].update({"computed_area" : computed_area_tan})
            backup_area.append((computed_area_tan[0], computed_area_tan[1]))

            # Get arc from computed area
            if computed_area_tan[1] < 0 and computed_area_tan[0] > 0:
                arc = (360 + computed_area_tan[1]) - computed_area_tan[0]
            elif computed_area_tan[1] < 0 and computed_area_tan[0] < 0:
                arc = (360 + computed_area_tan[1]) - (360 + computed_area_tan[0])
            else:
                arc = computed_area_tan[1] - computed_area_tan[0]

            # Points 1 and 2, based on computed area
            point2 = getPointFromPointDistanceAndBearing(client_last_known_location['lat'], client_last_known_location['lon'], radius, computed_area_tan[0])
            point1 = getPointFromPointDistanceAndBearing(client_last_known_location['lat'], client_last_known_location['lon'], radius, computed_area_tan[1])
            
            
            # Points 3, 4, 5 and 6, based on previous readings
            point4 = getPointFromPointDistanceAndBearing(client_last_known_location['lat'], client_last_known_location['lon'], radius, backup_area[backup_area_count][0])
            point3 = getPointFromPointDistanceAndBearing(client_last_known_location['lat'], client_last_known_location['lon'], radius, backup_area[backup_area_count][1])
            if len(backup_area) <= 2:
                tan5_and_6 = 0
            else:
                tan5_and_6 = backup_area_count + 1
            point6 = getPointFromPointDistanceAndBearing(client_last_known_location['lat'], client_last_known_location['lon'], radius, backup_area[tan5_and_6][0])
            point5 = getPointFromPointDistanceAndBearing(client_last_known_location['lat'], client_last_known_location['lon'], radius, backup_area[tan5_and_6][1])

            print("final computed area:" + str(computed_area_tan), file = log_server)
            print("using backup area count: " + str(backup_area_count + 1) + "." + str(backup_area[backup_area_count]) + " and " + str(tan5_and_6 + 1) + "." + str(backup_area[tan5_and_6]) + "--- len: " + str(len(backup_area)), file = log_server)
            
            print("\nvar center = new google.maps.Marker({\
                    position: {lat: " + str(client_last_known_location['lat']) + ", lng: " + str(client_last_known_location['lon']) + "},\
                    map: map});", file = log_server)
            print("var circle = new google.maps.Circle({\
                    strokeColor: '#FF0000',\
                    strokeOpacity: 0.8,\
                    strokeWeight: 0.5,\
                    fillColor: '#FF0000',\
                    fillOpacity: 0.02,\
                    map: map,\
                    center: {lat: " + str(client_last_known_location['lat']) + ", lng: " + str(client_last_known_location['lon']) + "},\
                    radius: " + str(radius * 1000) + "});", file = log_server)
            print("var tan1 = new google.maps.Marker({\
                    position: {lat: " + str(point1[0]) + ", lng: " + str(point1[1]) + "},\
                    icon: new google.maps.MarkerImage(\"http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|\" + \"42F453\",\
                    new google.maps.Size(21, 34),\
                    new google.maps.Point(0,0),\
                    new google.maps.Point(10, 34)),\
                    map: map});", file = log_server)
            print("var tan2 = new google.maps.Marker({\
                    position: {lat: " + str(point2[0]) + ", lng: " + str(point2[1]) + "},\
                    icon: new google.maps.MarkerImage(\"http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|\" + \"4542F4\",\
                    new google.maps.Size(21, 34),\
                    new google.maps.Point(0,0),\
                    new google.maps.Point(10, 34)),\
                    map: map});", file = log_server)
            print("var tan3 = new google.maps.Marker({\
                    position: {lat: " + str(point3[0]) + ", lng: " + str(point3[1]) + "},\
                    icon: new google.maps.MarkerImage(\"http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|\" + \"41F476\",\
                    new google.maps.Size(21, 34),\
                    new google.maps.Point(0,0),\
                    new google.maps.Point(10, 34)),\
                    map: map});", file = log_server)
            print("var tan4 = new google.maps.Marker({\
                    position: {lat: " + str(point4[0]) + ", lng: " + str(point4[1]) + "},\
                    icon: new google.maps.MarkerImage(\"http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|\" + \"4286F4\",\
                    new google.maps.Size(21, 34),\
                    new google.maps.Point(0,0),\
                    new google.maps.Point(10, 34)),\
                    map: map});", file = log_server)
            print("var tan5 = new google.maps.Marker({\
                    position: {lat: " + str(point5[0]) + ", lng: " + str(point5[1]) + "},\
                    icon: new google.maps.MarkerImage(\"http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|\" + \"41f491\",\
                    new google.maps.Size(21, 34),\
                    new google.maps.Point(0,0),\
                    new google.maps.Point(10, 34)),\
                    map: map});", file = log_server)
            print("var tan6 = new google.maps.Marker({\
                    position: {lat: " + str(point6[0]) + ", lng: " + str(point6[1]) + "},\
                    icon: new google.maps.MarkerImage(\"http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|\" + \"41E5F4\",\
                    new google.maps.Size(21, 34),\
                    new google.maps.Point(0,0),\
                    new google.maps.Point(10, 34)),\
                    map: map});", file = log_server)
            print("var user = new google.maps.Marker({\
                    position: {lat: " + str(decoded['gps']['lat']) + ", lng: " + str(decoded['gps']['lon']) + "},\
                    icon: new google.maps.MarkerImage(\"http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|\" + \"F4F142\",\
                    new google.maps.Size(21, 34),\
                    new google.maps.Point(0,0),\
                    new google.maps.Point(10, 34)),\
                    map: map});\n", file = log_server)

            rsrp_str = {"circle" : {"radius" : radius, "center" : {"lat" : client_last_known_location['lat'], "lon" : client_last_known_location['lon']}, "tan1" : {"lat" : point1[0], "lon" : point1[1]}, "tan2" : {"lat" : point2[0] , "lon" : point2[1]}, "tan3" : {"lat" : point3[0] , "lon" : point3[1]}, "tan4" : {"lat" : point4[0] , "lon" : point4[1]}, "tan5" : {"lat" : point5[0] , "lon" : point5[1]}, "tan6" : {"lat" : point6[0] , "lon" : point6[1]}, "arc" : arc}, "user" : {"lat" : decoded['gps']['lat'], "lon" : decoded['gps']['lon']}, "dst" : user_dst, "acc" : acc }
            print(rsrp_str, file = log_rsrp)      

            if count > 2:
                backup_area_count = out_count - 2

            out_count += 1
            print(str(out_count) + "\n--------------------------", file = log_server)
        
        count = count + 1
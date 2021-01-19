import sys
import re
import operator

if (len(sys.argv) != 5):
    print ('wrong number of args')
    exit(0)

file_name = sys.argv[1]
cid1 = str(sys.argv[2])
cid2 = str(sys.argv[3])
cid3 = str(sys.argv[4])

color_dict = {0 : "#0061FF", 1 : "#F44242"}
j = 0

print(str(file_name).replace('.txt', '_stats.txt'))
cidstats = open(str(file_name).replace('.txt', '_stats.txt'), 'w')

with open(str(file_name)) as fin:
    for line in fin:
        if (line[0] == 'b' and line[1] == '\''):
            str_split = line.split(' ')
            cid1_val = 0
            cid2_val = 0
            cid3_val = 0
            arcPts_str = ''
            bs_list = {}

            user_lat_lon = 'var userPoint' + str(j) + ' = new google.maps.LatLng('

            
            for i in range(len(str_split)):
                if ('lat' in str_split[i]):
                    user_lat_lon += str_split[i + 2]
                    user_lat_lon += re.sub(',', '', str_split[i + 5]) + ');'
                if (cid1 in str_split[i] and 'pci' in str_split[i - 2]):
                    cid1_val = re.sub('[\[}\],\n\'n\\\]', '', str_split[i + 3])
                    bs_list[cid1] = int(cid1_val)
                    arcPts_str += 'var arcPts' + cid1 + '_' + str(j) + '= drawArc(centerPoint, 315, 75, centerPoint.distanceFrom(userPoint' + str(j) + '));'
                    arcPts_str += ' arcPts' + cid1 + '_' + str(j) + '.push(centerPoint);'

                if (cid2 in str_split[i] and 'pci' in str_split[i - 2]):
                    cid2_val = re.sub('[\[}\],\n\'n\\\]', '', str_split[i + 3])
                    bs_list[cid2] = int(cid2_val)
                    arcPts_str += 'var arcPts' + cid2 + '_' + str(j) + '= drawArc(centerPoint, 80, 200, centerPoint.distanceFrom(userPoint' + str(j) + '));'
                    arcPts_str += ' arcPts' + cid2 + '_' + str(j) + '.push(centerPoint);'

                if (cid3 in str_split[i] and 'pci' in str_split[i - 2]):
                    cid3_val = re.sub('[\[}\],\n\'n\\\]', '', str_split[i + 3])
                    bs_list[cid3] = int(cid3_val)
                    arcPts_str += 'var arcPts' + cid3 + '_' + str(j) + '= drawArc(centerPoint, 240, 0, centerPoint.distanceFrom(userPoint' + str(j) + '));'
                    arcPts_str += ' arcPts' + cid3 + '_' + str(j) + '.push(centerPoint);'
                    
            bs_list_sorted = sorted(bs_list.items(), key=operator.itemgetter(1), reverse=True)

            popup_str = 'var contentStr' + str(j) + ' = \'' + re.sub('\'', '', str(bs_list_sorted)) + '\';'
            info_str = 'var infowindow' + str(j) + ' = new google.maps.InfoWindow({ content: contentStr' + str(j) + ' });'

            marker_str = 'var marker' + str(j) + ' = new google.maps.Marker({ position : userPoint' + str(j) + ', map : map });'
            
            polygon_str = ''
            polygon_list = []
            for i in range(len(bs_list_sorted)):
                pol = 'CID' + str(i) + '_' + str(j)
                polygon_list.append(pol)
                polygon_str += 'var ' + pol + ' = new google.maps.Polygon({ paths: [arcPts'
                polygon_str += str(bs_list_sorted[i][0]) + '_' + str(j) + '], strokeColor: \"' + str(color_dict[i]) + "\","
                polygon_str += 'strokeOpacity: 0.5, strokeWeight: 2, fillColor: ' + '\"' +  str(color_dict[i]) + "\", fillOpacity: 0.35 });"

                if (i == 1):
                    break
            
            marker_listener_str = 'marker' + str(j) + '.addListener(\'click\', function() { clearMarkings();'
            for i in range(len(polygon_list)):
                marker_listener_str += 'visiblePolygons.push(' + polygon_list[i] + ');'
                marker_listener_str += polygon_list[i] + '.setMap(map);'
            marker_listener_str += 'infowindow' + str(j) + '.open(map,marker' + str(j) + '); });\n'    

            print(bs_list_sorted)
            cidstats.write(user_lat_lon)
            cidstats.write(arcPts_str)
            cidstats.write(marker_str)
            cidstats.write(popup_str)
            cidstats.write(info_str)
            cidstats.write(polygon_str)
            cidstats.write(marker_listener_str)

            j += 1
            
cidstats.close();
import argparse
from xml.dom import minidom


def main():
    parser = argparse.ArgumentParser(
        description=
        '.gpx file extension visualizer in google maps. Add cid RSRP readings')
    parser.add_argument('--file', type=str)
    parser.add_argument('--gmaps', action='store_true')
    parser.add_argument('--skip_step', type=int, default=1)
    args = vars(parser.parse_args())

    gps_file = open(args['file'])
    gps_server_file = open(
        str(args['file']).replace('.gpx', '_server.txt'), 'w')
    xmldoc = minidom.parse(gps_file)

    gpx_points = xmldoc.getElementsByTagName('trkpt')

    ue_index = 0
    for gpx_point in gpx_points:
        # print(gpx_point.attributes['lat'].value,
        #       gpx_point.attributes['lon'].value)
        ue_index += 1
        if ue_index % args['skip_step'] != 0:
            continue

        server_str = 'b\'{\"gps\": {\"acc\": 3.9, \"lat\": ' + str(
            gpx_point.attributes['lat'].value) + ', \"lon\": ' + str(
                gpx_point.attributes['lon'].value) + '}, \"steps\": 0}\\n\'\n'
        # ) + '}, \"steps\": 0, \"cell\": [{\"pci\": , \"val\": }, {\"pci\": , \"val\": }]}\\n\'\n'
        # print(server_str)
        gps_server_file.write(server_str)

        if args['gmaps']:
            infowindow_ue_str = 'infowindow_temp_ue_' + str(ue_index)
            infowindow_js_var = ('var ' + infowindow_ue_str +
                                 ' =  new google.maps.InfoWindow({ content: ' +
                                 '\"<<' + str(ue_index / args['skip_step']) +
                                 '>>\"' + '});')
            ue_position_str = ('{lat: ' +
                               str(gpx_point.attributes['lat'].value) + ', ' +
                               'lng: ' +
                               str(gpx_point.attributes['lon'].value) + '}')
            ue_marker_str = 'marker_temp_ue' + str(ue_index)
            ue_marker_js_var = ('var ' + ue_marker_str +
                                ' = new google.maps.Marker({'
                                'position:' + ue_position_str +
                                ', map: map});')
            ue_add_listener_js = (ue_marker_str +
                                  '.addListener(\'click\', function() { ' +
                                  infowindow_ue_str + '.open(map, ' +
                                  ue_marker_str + '); '
                                  '});')

            print(infowindow_js_var + ue_marker_js_var + ue_add_listener_js)

    gps_file.close()
    gps_server_file.close()


if __name__ == '__main__':
    main()

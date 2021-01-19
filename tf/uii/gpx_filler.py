import json
import osmutils


def main():
    ue_logs = []
    with open('routes/E_I/E_I_sony1_1min_10s_server.txt') as f:
        for line in f:
            if line[0] == 'b' and line[1] == '\'':
                ue_log = json.loads(line[2:-4])
                ue_logs.append(ue_log)

        # for i in range(0, len(ue_logs)):
        #     print(ue_logs[i])

    gpx_logs = []
    with open('routes/E_J/E_J_sidewalk_towards_server.txt') as f:
        for line in f:
            if line[0] == 'b' and line[1] == '\'':
                gpx_log = json.loads(line[2:-4])
                print(gpx_log['gps']['lat'], gpx_log['gps']['lon'])

                closest_distance = 10000
                closest_distance_in = 0
                for i in range(1, len(ue_logs)):
                    distance = osmutils.getDistanceBetweenPoints(
                        gpx_log['gps']['lat'], gpx_log['gps']['lon'],
                        ue_logs[i]['gps']['lat'], ue_logs[i]['gps']['lon'])
                    if distance < closest_distance:
                        closest_distance_in = i
                        closest_distance = distance

                print('closest point: ', ue_logs[closest_distance_in]['cell'])
                gpx_log['cell'] = ue_logs[closest_distance_in]['cell']
                print(str(gpx_log))
                gpx_logs.append(gpx_log)
                # input('next...')

    out_file = open('routes/E_J/E_J_sidewalk_towards_server.txt.bak2', 'w')
    for gpx_log in gpx_logs:
        print('b\'' + str(gpx_log).replace('\'', '\"') + '\\n\'',
              file=out_file)
    out_file.close()


if __name__ == '__main__':
    main()

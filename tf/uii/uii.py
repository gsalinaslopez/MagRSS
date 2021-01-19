import json
import math
import operator
import pathlib

import warnings
import pandas as pd
import geopandas
import osmutils
import shapely

warnings.filterwarnings('ignore', 'GeoSeries.notna', UserWarning)

_WAY_SEG_COLORS = [
    "\'#FF0000\'", "\'#EEFF00\'", "\'#EEFF00\'", "\'#00FF44\'", "\'#00FF44\'"
]
_WAY_SEG_LABELS = [
    '\"main\"', '\"road\"', '\"road\"', '\"sidewalk\"', '\"sidewalk\"'
]
_GMAPS_MARKER_ICON_URL = (
    'new google.maps.MarkerImage(\"http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld=%E2%80%A2|{}\", new google.maps.Size(21, 34), new google.maps.Point(0,0), new google.maps.Point(10, 34))'
)

_BS = {
    '243': {
        'lat': 24.787113,
        'lon': 121.001955
    },
    '244': {
        'lat': 24.784410,
        'lon': 120.997406
    },
    '245': {
        'lat': 24.784410,
        'lon': 120.997406
    },
    '246': {
        'lat': 24.787461,
        'lon': 120.995878
    },
    '247': {
        'lat': 24.787461,
        'lon': 120.995878
    },
    '248': {
        'lat': 24.787461,
        'lon': 120.995878
    }
}


def _get_clean_train_filepaths(train_data_dir):
    clean_train_files = []
    main_train_dir_path = pathlib.Path(
        pathlib.PurePath(pathlib.Path.cwd()).parent, pathlib.Path('train'))

    for train_dir in [
            x for x in main_train_dir_path.iterdir()
            if x.is_dir() and '.' not in x.name
    ]:
        clean_dir = train_dir / str(train_data_dir)
        for clean_train_file in [
                x for x in clean_dir.iterdir() if not x.is_dir()
        ]:
            clean_train_files.append(str(clean_train_file))

    return clean_train_files


def get_pd_dataframe_from_dir(train_data_dir):
    clean_train_files = _get_clean_train_filepaths(train_data_dir)

    # setup pandas dataframe
    dataframe = pd.concat([pd.read_csv(x) for x in clean_train_files],
                          sort=False)

    return dataframe


def get_towards_bs_tangent_points(pci, ue_data):
    dst_bs = _BS[str(pci)]
    dst_bs_bearing = osmutils.getBearingBetweenPoints(ue_data['gps']['lat'],
                                                      ue_data['gps']['lon'],
                                                      dst_bs['lat'],
                                                      dst_bs['lon'])
    return (dst_bs_bearing - 90, dst_bs_bearing + 90)


def get_away_bs_tangent_points(pci, ue_data):
    dst_bs = _BS[str(pci)]
    dst_bs_bearing = osmutils.getBearingBetweenPoints(ue_data['gps']['lat'],
                                                      ue_data['gps']['lon'],
                                                      dst_bs['lat'],
                                                      dst_bs['lon'])
    if dst_bs_bearing > 0:
        dst_bs_bearing = dst_bs_bearing - 180
    else:
        dst_bs_bearing = dst_bs_bearing + 180
    return (dst_bs_bearing - 90, dst_bs_bearing + 90)


def get_overlap_from_tan_points(tangent_points1, tangent_points2):
    if tangent_points1[0] == 0 and tangent_points1[0] == 0:
        return tangent_points2
    if tangent_points1[0] == 360 and tangent_points1[0] == 360:
        return tangent_points1
    if tangent_points2[0] == 360 and tangent_points2[0] == 360:
        return tangent_points2

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

    first = tangent_points1[0] if (
        tangent_points1[0] > tangent_points2[0]) else tangent_points2[0]
    second = tangent_points1[1] if (
        tangent_points1[1] < tangent_points2[1]) else tangent_points2[1]
    return (first, second)


def get_gmaps_way_drawings(ue_index, ue_data, computed_area_tan, arc,
                           paa_prev_results):
    closest_road_segment, closest_ways = osmutils.processUELocation(
        ue_data['gps']['lat'], ue_data['gps']['lon'], ue_data['gps']['acc'])

    cat_temp = computed_area_tan
    road_segment_gdf_list = []
    computed_area_tan = [0, 0]
    computed_area_tan[0] = cat_temp[1]
    computed_area_tan[1] = cat_temp[0]
    way_clipped_area_count = 0
    way_clipped_area_list = []
    way_seg_count = 0
    way_seg_paths = []
    way_seg_intersections = []
    way_seg_intersec_stats = ''
    way_seg_intersec_stats_dict = {"main": 0, "road": 0, "sidewalk": 0}
    way_seg_js_vars = []

    # Compute PAA as a GeoDataFrame once
    paa_gdf = osmutils.get_paa_polygon_gdf(ue_data, computed_area_tan, arc)
    paa_gdf.crs = "EPSG:4326"
    # Add PAA backups
    backup1_computed_area_tan = [
        paa_prev_results[-1]['computed_area_tan'][1],
        paa_prev_results[-1]['computed_area_tan'][0]
    ]
    backup1_paa_gdf = osmutils.get_paa_polygon_gdf(ue_data,
                                                   backup1_computed_area_tan,
                                                   paa_prev_results[-1]['arc'])
    backup1_paa_gdf.crs = "EPSG:4326"

    backup2_computed_area_tan = [
        paa_prev_results[-2]['computed_area_tan'][1],
        paa_prev_results[-2]['computed_area_tan'][0]
    ]
    backup2_paa_gdf = osmutils.get_paa_polygon_gdf(ue_data,
                                                   backup2_computed_area_tan,
                                                   paa_prev_results[-2]['arc'])
    backup2_paa_gdf.crs = "EPSG:4326"

    paa_gdf_extended = paa_gdf.copy()
    paa_gdf_extended = paa_gdf_extended.append(backup1_paa_gdf,
                                               ignore_index=True)
    paa_gdf_extended = paa_gdf_extended.append(backup2_paa_gdf,
                                               ignore_index=True)

    # print(backup1_computed_area_tan, backup2_computed_area_tan,
    #       computed_area_tan)
    # print(paa_prev_results[-1]['arc'], paa_prev_results[-2]['arc'], arc)
    # paa_gdf.plot()
    # backup1_paa_gdf.plot()
    # backup2_paa_gdf.plot()

    # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    # paa_polygons = [
    #     paa_gdf_extended.iloc[0]['geometry'],
    #     paa_gdf_extended.iloc[1]['geometry'],
    #     paa_gdf_extended.iloc[2]['geometry']
    # ]
    paa_gdf_extended['new_column'] = 1
    # print(paa_gdf_extended)
    # print('yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy')
    # print(paa_gdf_extended.iloc[0]['geometry'])
    # print(paa_gdf_extended.iloc[1]['geometry'])
    # print(paa_gdf_extended.iloc[2]['geometry'])
    # if not paa_gdf_extended.iloc[0]['geometry'].is_empty:
    #     geopandas.GeoSeries(paa_gdf_extended.iloc[0]['geometry']).plot()
    # else:
    #     geopandas.GeoSeries().plot()
    # if not paa_gdf_extended.iloc[1]['geometry'].is_empty:
    #     geopandas.GeoSeries(paa_gdf_extended.iloc[1]['geometry']).plot()
    # else:
    #     geopandas.GeoSeries().plot()
    # if not paa_gdf_extended.iloc[2]['geometry'].is_empty:
    #     geopandas.GeoSeries(paa_gdf_extended.iloc[2]['geometry']).plot()
    # else:
    #     geopandas.GeoSeries().plot()
    # print('zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz')
    g = geopandas.GeoSeries(paa_gdf_extended['geometry'].unary_union)
    h = geopandas.GeoDataFrame()
    h['geometry'] = g
    paa_gdf_extended = h.copy()

    if paa_gdf_extended.area.iloc[0] == 0.0:
        paa_gdf_extended = osmutils.get_paa_polygon_gdf(ue_data, (0, 0), 360)
    # paa_gdf_extended.plot()
    # print('plotted?')
    # print(paa_gdf_extended)
    # h.plot()
    # print(h)

    for closest_way in closest_ways:
        for way in closest_way['ways']:
            for i in range(5):
                way_seg_i = 'wayseg' + str(i)

                # Generate gmaps paths for waysegment(s)
                way_seg_points = [{
                    'lat': p['lat'],
                    'lng': p['lon']
                } for p in way[way_seg_i]['points']]

                way_seg_ue_js_var = ('var ' + way_seg_i + '_' +
                                     str(way_seg_count) + '_ue' +
                                     str(ue_index))
                way_seg_paths.append(
                    way_seg_ue_js_var + ' = new google.maps.Polyline({'
                    'path: ' + str(str(way_seg_points).replace('\'', '')) +
                    ', geodesic: true, strokeColor: ' + _WAY_SEG_COLORS[i] +
                    ','
                    ' strokeOpacity: 0.7, strokerWeight: 2});')
                way_seg_js_vars.append(way_seg_ue_js_var)

                # Generate gmaps markers for intersection(s)
                way_seg_intersec_count = 0
                for way_seg_intersection_point in way[way_seg_i][
                        'intersections']:
                    point = str(way_seg_intersection_point).replace(
                        'lon', 'lng')

                    way_seg_intersec_js_var = ('var ' + way_seg_i + '_' +
                                               str(way_seg_count) +
                                               '_intersec' +
                                               str(way_seg_intersec_count) +
                                               '_ue' + str(ue_index))
                    way_seg_intersections.append(
                        way_seg_intersec_js_var + ' = new google.maps.Marker({'
                        'position: ' + str(point.replace('\'', '')) +
                        ', icon: ' + str(
                            _GMAPS_MARKER_ICON_URL.format(_WAY_SEG_COLORS[i]).
                            replace('\'', '').replace('#', '')) + ', label: ' +
                        str(_WAY_SEG_LABELS[i]) + '});')
                    way_seg_js_vars.append(way_seg_intersec_js_var)
                    way_seg_intersec_count += 1

                    if osmutils.is_point_inside_paa(
                            ue_data, computed_area_tan,
                            way_seg_intersection_point):
                        way_seg_intersec_stats += _WAY_SEG_LABELS[i].replace(
                            '\"', '') + ' '
                        way_seg_intersec_stats_dict[_WAY_SEG_LABELS[i].replace(
                            '\"', '')] += 1

                # Get stats about number of intersections per segment
                # way_seg_intersec_stats[i] += way_seg_intersec_count

            way_seg_count += 1

        # Calculate intersected area using geopandas
        road_segments_gdf = osmutils.get_road_segment_gdf(closest_way)
        road_segments_gdf.crs = "EPSG:4326"

        road_segment_gdf_list.append(road_segments_gdf)
        areas = 0
        clipped_areas = {
            'sidewalk': 0,
            'sidewalk_area_m2': 0,
            'sidewalk_area_percent': 0,
            'road': 0,
            'road_area_m2': 0,
            'road_area_percent': 0,
            'paa_area': 0,
            'intersec_area': 0
        }

        # road_segments_gdf.plot()
        for road_segment_gdf in road_segments_gdf.iterrows():
            clipped_area = geopandas.clip(paa_gdf_extended,
                                          road_segment_gdf[1]['geometry'])
            if clipped_area.size > 0 and clipped_area['geometry'].iloc[
                    0] is not None:
                # clipped area polygon JS
                # clipped_area.plot()
                # print('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
                # print(clipped_area.area)

                way_ue_clipped_var_js_name = ('var wayclip_' +
                                              str(way_clipped_area_count) +
                                              '_ue' + str(ue_index))
                try:
                    way_ue_clipped_var_js = way_ue_clipped_var_js_name + (
                        ' = new google.maps.Polygon({'
                        'path: ' + str(
                            list(clipped_area['geometry'].iloc[0].exterior.
                                 coords)).replace('(', '{lat: ').replace(
                                     ')', '}').replace('}, {', 'x').replace(
                                         ', ', ', lng: ').replace('x', '}, {')
                        + ', geodesic: true, strokeColor: ')
                except AttributeError:
                    clipped_area_mutipoly_path = []
                    for poly in clipped_area['geometry'].iloc[0].geoms:
                        clipped_area_mutipoly_path.append(
                            str(list(poly.exterior.coords)).replace(
                                '(', '{lat: ').replace(')', '}').replace(
                                    '}, {', 'x').replace(', ',
                                                         ', lng: ').replace(
                                                             'x', '}, {'))
                    way_ue_clipped_var_js = way_ue_clipped_var_js_name + (
                        ' = new google.maps.Polygon({'
                        'path: ' + str(clipped_area_mutipoly_path).replace(
                            '\'', '') + ', geodesic: true, strokeColor: ')

                # Road or Sidewalk area computation
                areas += float(clipped_area.area.iloc[0])
                if road_segment_gdf[1][
                        'polygon_name'] == 'way_seg0_way_seg1' or road_segment_gdf[
                            1]['polygon_name'] == 'way_seg0_way_seg2':
                    clipped_areas['road'] += float(clipped_area.area.iloc[0])
                    way_ue_clipped_var_js += '\'#FFFF00\', fillColor: \'#FFFF00\''
                else:
                    clipped_areas['sidewalk'] += float(
                        clipped_area.area.iloc[0])
                    way_ue_clipped_var_js += '\'#FF00FF\', fillColor: \'#FF00FF\''

                way_ue_clipped_var_js += ', strokeOpacity: 0.7, strokerWeight: 2, fillOpacity: 0.5});'
                way_seg_js_vars.append(way_ue_clipped_var_js_name)
                way_clipped_area_count += 1
                # TODO: reenable
                print(way_ue_clipped_var_js)

        clipped_areas['paa_area'] = paa_gdf_extended.area.iloc[0]
        clipped_areas['intersec_area'] = areas
        clipped_areas['paa_area_m2'] = (
            math.pi * math.pow(ue_data['gps']['acc'], 2)) * (arc / 360)
        if areas != 0:
            clipped_areas['road_area_percent'] = (
                clipped_areas['road'] * 100) / clipped_areas['paa_area']
            clipped_areas['road_area_m2'] = (
                clipped_areas['road_area_percent'] *
                clipped_areas['paa_area_m2']) / 100

            clipped_areas['sidewalk_area_percent'] = (
                clipped_areas['sidewalk'] * 100) / clipped_areas['paa_area']
            clipped_areas['sidewalk_area_m2'] = (
                clipped_areas['sidewalk_area_percent'] *
                clipped_areas['paa_area_m2']) / 100

        way_clipped_area_list.append(clipped_areas)
    # return (road_segment_gdf_list, paa_gdf, areas)

    if way_clipped_area_list[0]['paa_area'] > 0:
        d = {
            'road_area_percent': (math.fsum([
                clipped_areas['road']
                for clipped_areas in way_clipped_area_list
            ]) * 100) / (way_clipped_area_list[0]['paa_area'] *
                         len(way_clipped_area_list)),
            'road_area_m2':
            math.fsum([
                clipped_areas['road_area_m2']
                for clipped_areas in way_clipped_area_list
            ]),
            'sidewalk_area_percent': (math.fsum([
                clipped_areas['sidewalk']
                for clipped_areas in way_clipped_area_list
            ]) * 100) / (way_clipped_area_list[0]['paa_area'] *
                         len(way_clipped_area_list)),
            'sidewalk_area_m2':
            math.fsum([
                clipped_areas['sidewalk_area_m2']
                for clipped_areas in way_clipped_area_list
            ])
        }
        way_clipped_area_list.append(d)

    master_js_string = ''

    # Gmaps variables for way segments paths and intersections
    for way_seg_path in way_seg_paths:
        master_js_string += way_seg_path
    for way_seg_intersection in way_seg_intersections:
        master_js_string += way_seg_intersection

    # Generate gmapss poplygon for PAA
    centerpoint_ue_str = 'centerpoint_ue' + str(ue_index)
    paa_centerpoint_js_var = ('var ' + centerpoint_ue_str +
                              ' = new google.maps.LatLng(' +
                              str(ue_data['gps']['lat']) + ', ' +
                              str(ue_data['gps']['lon']) + ');')

    paa_ue_str = 'paa_ue' + str(ue_index)
    paa_js_var = ('var ' + paa_ue_str + ' = drawArc(' + centerpoint_ue_str +
                  ', ' + str(computed_area_tan[1]) + ', ' +
                  str(computed_area_tan[0]) + ', ' +
                  str(ue_data['gps']['acc']) + ');')
    paa_push_js = paa_ue_str + '.push(' + centerpoint_ue_str + ');'

    paa_poly_ue_str = 'paa_poly_ue' + str(ue_index)
    paa_poly_js_var = ('var ' + paa_poly_ue_str +
                       ' = new google.maps.Polygon({')
    if paa_gdf_extended['geometry'].iloc[0].area > 0 and paa_gdf_extended[
            'geometry'].iloc[0] is not None:
        try:
            paa_poly_js_var += 'path: ' + str(
                list(paa_gdf_extended['geometry'].iloc[0].exterior.coords
                     )).replace('(', '{lat: ').replace(')', '}').replace(
                         '}, {', 'x').replace(', ', ', lng: ').replace(
                             'x', '}, {') + ', '
        except AttributeError:
            paa_gdf_multipoly_path = []
            for poly in paa_gdf_extended['geometry'].iloc[0].geoms:
                paa_gdf_multipoly_path.append(
                    str(list(poly.exterior.coords)).replace(
                        '(', '{lat: ').replace(')', '}').replace(
                            '}, {',
                            'x').replace(', ', ', lng: ').replace('x', '}, {'))
            paa_poly_js_var += 'path: ' + str(paa_gdf_multipoly_path).replace(
                '\'', '') + ', '

    paa_poly_js_var += (
        'strokeColor: \"0061FF\", ' +
        'strokeOpacity: 0.5, strokeWeight: 2, filllColor: \"0061FF\", ' +
        'fillOpacity: 0.15 });')

    master_js_string += paa_centerpoint_js_var
    master_js_string += paa_js_var
    master_js_string += paa_push_js
    master_js_string += paa_poly_js_var

    gmaps_js_vars = [
        str(js_var).replace('var ', '') for js_var in way_seg_js_vars
    ]
    gmaps_js_vars.append(paa_poly_ue_str)
    set_map_js = '.setMap(map);'.join(map(str,
                                          gmaps_js_vars)) + '.setMap(map);'
    set_poly_js = 'visiblePolygons.push(' + '); visiblePolygons.push('.join(
        map(str, gmaps_js_vars)) + ');'

    # String for road and sidewalk area overlap percentage
    road_sidewalk_percentage = {'road': [], 'sidewalk': []}
    for i in range(len(way_clipped_area_list)):
        road_percentage_str = str(i) + ': '
        sidewalk_percentage_str = str(i) + ': '

        if 'road_area_percent' in way_clipped_area_list[i]:
            road_percentage_str += (
                str(way_clipped_area_list[i]['road_area_percent']) + '% ' +
                str(way_clipped_area_list[i]['road_area_m2']) + 'm2 ')
            road_sidewalk_percentage['road'].append(road_percentage_str)
        if 'sidewalk_area_percent' in way_clipped_area_list[i]:
            sidewalk_percentage_str += (
                str(way_clipped_area_list[i]['sidewalk_area_percent']) + '% ' +
                str(way_clipped_area_list[i]['sidewalk_area_m2']) + 'm2 ')
            road_sidewalk_percentage['sidewalk'].append(
                sidewalk_percentage_str)

    infowindow_ue_str = 'infowindow_ue_' + str(ue_index)
    infowin_str = str(road_sidewalk_percentage)
    infowin_str += ' PREDICTION:'
    prediction = ''
    if way_clipped_area_list[-1]['road_area_percent'] > way_clipped_area_list[
            -1]['sidewalk_area_percent']:
        infowin_str += ' ROAD'
        prediction = 'road'
    elif way_clipped_area_list[-1][
            'sidewalk_area_percent'] > way_clipped_area_list[-1][
                'road_area_percent']:
        infowin_str += ' SIDEWALK'
        prediction = 'sidewalk'
    else:
        infowin_str += ' UNDEFINED'
        prediction = 'sidewalk'

    infowindow_js_var = ('var ' + infowindow_ue_str +
                         ' =  new google.maps.InfoWindow({ content: ' + '\"' +
                         infowin_str + '\"' + '});')

    ue_position_str = ('{lat: ' + str(ue_data['gps']['lat']) + ', ' + 'lng: ' +
                       str(ue_data['gps']['lon']) + '}')
    ue_marker_str = 'marker_ue' + str(ue_index)
    ue_marker_js_var = ('var ' + ue_marker_str + ' = new google.maps.Marker({'
                        'position:' + ue_position_str + ', map: map});')
    ue_add_listener_js = (ue_marker_str +
                          '.addListener(\'click\', function() { ' +
                          infowindow_ue_str + '.open(map, ' + ue_marker_str +
                          '); '
                          'clearMarkings(); ' + set_poly_js + set_map_js +
                          '});')

    master_js_string += infowindow_js_var
    master_js_string += ue_marker_js_var
    master_js_string += ue_add_listener_js

    # TODO: reenable
    print(master_js_string)

    if prediction == 'road':
        return False
    else:
        return True


def get_gmaps_drawings(ue_index, ue_data, computed_area_tan, arc):
    closest_road_segment, closest_way = osmutils.processUELocation(
        ue_data['gps']['lat'], ue_data['gps']['lon'], ue_data['gps']['acc'])

    cat_temp = computed_area_tan
    computed_area_tan = [0, 0]
    computed_area_tan[0] = cat_temp[1]
    computed_area_tan[1] = cat_temp[0]
    way_seg_count = 0
    way_seg_paths = []
    way_seg_intersections = []
    way_seg_intersec_stats = ''
    way_seg_intersec_stats_dict = {"main": 0, "road": 0, "sidewalk": 0}
    way_seg_js_vars = []

    for way in closest_road_segment['ways']:
        for i in range(5):
            way_seg_i = 'wayseg' + str(i)

            # Generate gmaps paths for waysegment(s)
            way_seg_points = [{
                'lat': p['lat'],
                'lng': p['lon']
            } for p in way[way_seg_i]['points']]

            way_seg_ue_js_var = ('var ' + way_seg_i + '_' +
                                 str(way_seg_count) + '_ue' + str(ue_index))
            way_seg_paths.append(way_seg_ue_js_var +
                                 ' = new google.maps.Polyline({'
                                 'path: ' +
                                 str(str(way_seg_points).replace('\'', '')) +
                                 ', geodesic: true, strokeColor: ' +
                                 _WAY_SEG_COLORS[i] + ','
                                 ' strokeOpacity: 0.7, strokerWeight: 2});')
            way_seg_js_vars.append(way_seg_ue_js_var)

            # Generate gmaps markers for intersection(s)
            way_seg_intersec_count = 0
            for way_seg_intersection_point in way[way_seg_i]['intersections']:
                point = str(way_seg_intersection_point).replace('lon', 'lng')

                way_seg_intersec_js_var = ('var ' + way_seg_i + '_' +
                                           str(way_seg_count) + '_intersec' +
                                           str(way_seg_intersec_count) +
                                           '_ue' + str(ue_index))
                way_seg_intersections.append(
                    way_seg_intersec_js_var + ' = new google.maps.Marker({'
                    'position: ' + str(point.replace('\'', '')) + ', icon: ' +
                    str(
                        _GMAPS_MARKER_ICON_URL.format(_WAY_SEG_COLORS[i]).
                        replace('\'', '').replace('#', '')) + ', label: ' +
                    str(_WAY_SEG_LABELS[i]) + '});')
                way_seg_js_vars.append(way_seg_intersec_js_var)
                way_seg_intersec_count += 1

                if osmutils.is_point_inside_paa(ue_data, computed_area_tan,
                                                way_seg_intersection_point):
                    way_seg_intersec_stats += _WAY_SEG_LABELS[i].replace(
                        '\"', '') + ' '
                    way_seg_intersec_stats_dict[_WAY_SEG_LABELS[i].replace(
                        '\"', '')] += 1

            # Get stats about number of intersections per segment
            # way_seg_intersec_stats[i] += way_seg_intersec_count

        way_seg_count += 1

    # Calculate intersected area
    road_segments_gdf = osmutils.get_road_segment_gdf(closest_road_segment)
    paa_gdf = osmutils.get_paa_polygon_gdf(ue_data, computed_area_tan, arc)

    road_segments_gdf.crs = "EPSG:4326"
    paa_gdf.crs = "EPSG:4326"

    areas = 0
    clipped_areas = {
        'sidewalk': 0,
        'road': 0,
        'paa_area': 0,
        'intersec_area': 0
    }
    for road_segment_gdf in road_segments_gdf.iterrows():
        clipped_area = geopandas.clip(paa_gdf, road_segment_gdf[1]['geometry'])
        if clipped_area.size > 0 and clipped_area['geometry'].iloc[
                0] is not None:
            areas += float(clipped_area.area.iloc[0])
            if road_segment_gdf[1][
                    'polygon_name'] == 'way_seg0_way_seg1' or road_segment_gdf[
                        1]['polygon_name'] == 'way_seg0_way_seg2':
                clipped_areas['road'] += float(clipped_area.area.iloc[0])
            else:
                clipped_areas['sidewalk'] += float(clipped_area.area.iloc[0])

    clipped_areas['paa_area'] = paa_gdf.area.iloc[0]
    clipped_areas['intersec_area'] = areas
    clipped_areas['paa_area_m2'] = (
        math.pi * math.pow(ue_data['gps']['acc'], 2)) * (arc / 360)
    if areas != 0:
        clipped_areas['road_percent'] = (clipped_areas['road'] *
                                         100) / clipped_areas['paa_area']
        clipped_areas['sidewalk_percent'] = (clipped_areas['sidewalk'] *
                                             100) / clipped_areas['paa_area']
    # return (road_segments_gdf, paa_gdf, areas)

    # Gmaps variables for way segments paths and intersections
    master_js_string = ''
    for way_seg_path in way_seg_paths:
        master_js_string += way_seg_path
    for way_seg_intersection in way_seg_intersections:
        master_js_string += way_seg_intersection

    # Generate gmapss poplygon for PAA
    centerpoint_ue_str = 'centerpoint_ue' + str(ue_index)
    paa_centerpoint_js_var = ('var ' + centerpoint_ue_str +
                              ' = new google.maps.LatLng(' +
                              str(ue_data['gps']['lat']) + ', ' +
                              str(ue_data['gps']['lon']) + ');')

    paa_ue_str = 'paa_ue' + str(ue_index)
    paa_js_var = ('var ' + paa_ue_str + ' = drawArc(' + centerpoint_ue_str +
                  ', ' + str(computed_area_tan[1]) + ', ' +
                  str(computed_area_tan[0]) + ', ' +
                  str(ue_data['gps']['acc'] + 1) + ');')
    paa_push_js = paa_ue_str + '.push(' + centerpoint_ue_str + ');'

    paa_poly_ue_str = 'paa_poly_ue' + str(ue_index)
    paa_poly_js_var = (
        'var ' + paa_poly_ue_str + ' = new google.maps.Polygon({' +
        'paths: [' + paa_ue_str + '], ' + 'strokeColor: \"0061FF\", ' +
        'strokeOpacity: 0.5, strokeWeight: 2, filllColor: \"0061FF\", ' +
        'fillOpacity: 0.35 });')

    master_js_string += paa_centerpoint_js_var
    master_js_string += paa_js_var
    master_js_string += paa_push_js
    master_js_string += paa_poly_js_var

    gmaps_js_vars = [
        str(js_var).replace('var ', '') for js_var in way_seg_js_vars
    ]
    gmaps_js_vars.append(paa_poly_ue_str)
    set_map_js = '.setMap(map);'.join(map(str,
                                          gmaps_js_vars)) + '.setMap(map);'
    set_poly_js = 'visiblePolygons.push(' + '); visiblePolygons.push('.join(
        map(str, gmaps_js_vars)) + ');'
    infowindow_ue_str = 'infowindow_ue_' + str(ue_index)
    # infowin_str = str(way_seg_intersec_stats_dict) + str(
    #     computed_area_tan[0]) + ', ' + str(
    #         computed_area_tan[1]) + ' arc: ' + str(arc) + str(
    #             dict(sorted(clipped_areas.items(),
    #                         key=operator.itemgetter(1))))
    road_sidewalk_percentage = {'road': 0, 'sidewalk': 0}
    if 'road_percent' in clipped_areas:
        road_sidewalk_percentage['road'] = clipped_areas['road_percent']
    if 'sidewalk_percent' in clipped_areas:
        road_sidewalk_percentage['sidewalk'] = clipped_areas[
            'sidewalk_percent']

    infowin_str = '<<' + str(ue_index) + '>>' + str(
        dict(
            sorted(road_sidewalk_percentage.items(),
                   key=operator.itemgetter(1)))) + str(ue_data['cell'])
    infowindow_js_var = ('var ' + infowindow_ue_str +
                         ' =  new google.maps.InfoWindow({ content: ' + '\"' +
                         infowin_str + '\"' + '});')

    ue_position_str = ('{lat: ' + str(ue_data['gps']['lat']) + ', ' + 'lng: ' +
                       str(ue_data['gps']['lon']) + '}')
    ue_marker_str = 'marker_ue' + str(ue_index)
    ue_marker_js_var = ('var ' + ue_marker_str + ' = new google.maps.Marker({'
                        'position:' + ue_position_str + ', map: map});')
    ue_add_listener_js = (ue_marker_str +
                          '.addListener(\'click\', function() { ' +
                          infowindow_ue_str + '.open(map, ' + ue_marker_str +
                          '); '
                          'clearMarkings(); ' + set_poly_js + set_map_js +
                          '});')

    master_js_string += infowindow_js_var
    master_js_string += ue_marker_js_var
    master_js_string += ue_add_listener_js

    print(master_js_string)
    return False


def process_ue_location(ue_index, ue_prev_data, ue_data, paa_prev_results):
    # paa_circle_radius = ue_data['gps']['acc']
    rsrp_threshold = 3
    computed_area_tan = (0, 0)

    # List union to see if there is a new BS appearing or disappearing
    last_known_pci_list = [
        d['pci'] for d in ue_prev_data['cell'] if str(d['pci']) in _BS.keys()
    ]
    read_cell_pci_list = [
        d['pci'] for d in ue_data['cell'] if str(d['pci']) in _BS.keys()
    ]

    unwanted_cells = [
        x['pci'] for x in ue_data['cell'] if x['pci'] not in read_cell_pci_list
    ]
    ue_data['cell'] = [
        ue_d for ue_d in ue_data['cell'] if str(ue_d['pci']) in _BS.keys()
    ]
    unwanted_cells = [
        x['pci'] for x in ue_prev_data['cell']
        if x['pci'] not in last_known_pci_list
    ]
    ue_prev_data['cell'] = [
        ue_d for ue_d in ue_prev_data['cell']
        if str(ue_d['pci']) in _BS.keys()
    ]

    # TODO: previous_readings

    for read_cell in ue_data['cell']:
        # Recently entered into new BS area, assume 'towards'
        if read_cell['pci'] not in last_known_pci_list:
            # TODO: conflicting orientation
            tan_points = get_towards_bs_tangent_points(read_cell['pci'],
                                                       ue_data)
            computed_area_tan = get_overlap_from_tan_points(
                computed_area_tan, tan_points)
            continue

        for last_known_cell in ue_prev_data['cell']:
            # Recently left BS are, asume 'away'
            if last_known_cell['pci'] not in read_cell_pci_list:
                # TODO: conflicting orientation
                tan_points = get_away_bs_tangent_points(
                    last_known_cell['pci'], ue_data)
                computed_area_tan = get_overlap_from_tan_points(
                    computed_area_tan, tan_points)
                continue
            elif int(read_cell['pci']) == int(last_known_cell['pci']):
                if int(read_cell['val']) >= int(
                        last_known_cell['val']) + rsrp_threshold:
                    tan_points = get_towards_bs_tangent_points(
                        read_cell['pci'], ue_data)
                elif int(read_cell['val']) <= int(
                        last_known_cell['val']) - rsrp_threshold:
                    tan_points = get_away_bs_tangent_points(
                        read_cell['pci'], ue_data)
                else:
                    tan_points = computed_area_tan

                computed_area_tan = get_overlap_from_tan_points(
                    computed_area_tan, tan_points)

    # TODO: backup area

    # Get arc from computed area
    if computed_area_tan[1] < 0 and computed_area_tan[0] > 0:
        arc = (360 + computed_area_tan[1]) - computed_area_tan[0]
    elif computed_area_tan[1] < 0 and computed_area_tan[0] < 0:
        arc = (360 + computed_area_tan[1]) - (360 + computed_area_tan[0])
    else:
        arc = computed_area_tan[1] - computed_area_tan[0]

    # Tangent Points
    # point2 = osmutils.getPointFromPointDistanceAndBearing(
    #     ue_data['gps']['lat'], ue_data['gps']['lon'], paa_circle_radius,
    #     computed_area_tan[0])
    # point1 = osmutils.getPointFromPointDistanceAndBearing(
    #     ue_data['gps']['lat'], ue_data['gps']['lon'], paa_circle_radius,
    #     computed_area_tan[1])

    # print('LEN ->' + str(len(paa_prev_results)))
    # print(computed_area_tan)

    # aa, b, c = get_gmaps_way_drawings(ue_index, ue_data, computed_area_tan,
    #                                   arc, paa_prev_results)
    # paa_prev_results.append({
    #     'computed_area_tan': computed_area_tan,
    #     'arc': arc,
    #     'paa_gdf': b
    # })

    # return aa, b, c

    # TODO: resume from here

    bool_road_sidewalk_prediction = get_gmaps_way_drawings(
        ue_index, ue_data, computed_area_tan, arc, paa_prev_results)

    # Save PAA arc and tangent points for further usage
    paa_prev_results.append({
        'computed_area_tan': computed_area_tan,
        'arc': arc
    })

    return bool_road_sidewalk_prediction


def main():
    ue_logs = []
    with open('routes/E_J/E_J_sidewalk_towards_server.txt.bak2') as f:
        for line in f:
            if line[0] == 'b' and line[1] == '\'':
                ue_log = json.loads(line[2:-4])
                ue_logs.append(ue_log)

        a = 0
        hits = 0
        paa_results = [{
            'computed_area_tan': (0, 0),
            'arc': 0
        }, {
            'computed_area_tan': (0, 0),
            'arc': 0
        }]

        for i in range(1, len(ue_logs)):
            if i % 12 == 0:
                a = i
            if process_ue_location(i, ue_logs[a], ue_logs[i], paa_results):
                hits += 1

        print(hits / (len(ue_logs) - 1))
        print('LEN -> ', len(paa_results))


if __name__ == '__main__':
    main()

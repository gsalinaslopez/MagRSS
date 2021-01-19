import pathlib

import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from tqdm import tqdm

import cleaner_utils


def plot_all_df_details(
    dataframes, master_directory_path, lowess_param=0.050, dbm_rounding=None):
    results = []
    
    for i in tqdm(range(len(dataframes))):
        dataframes[i] = cleaner_utils.clean_non_ocurring_dbm(dataframes[i])
        dataframes[i] = cleaner_utils.clean_n_strongest_dbm(
            dataframes[i], rounding=dbm_rounding)
        results.append(
            cleaner_utils.get_magnetometer_details(
                dataframes[i], lowess_param=lowess_param, interactive=False))

    # input('results computation - DONE')

    all_df = []
    main_train_dir_path = pathlib.Path(
        pathlib.PurePath(pathlib.Path.cwd()).parent, 
                         pathlib.Path('train'), 
                         'files',
                         master_directory_path)
    for i in range(0, len(results), 2):
        new_df_dict_s = {'lat': dataframes[i]['lat'],
                         'lon': dataframes[i]['lon'],
                         'bear': dataframes[i]['bear'],
                         'heading': dataframes[i]['heading'],
                         'magx_kalman': results[i][-11],
                         'magy_kalman': results[i][-10],
                         'magz_kalman': results[i][-9],
                         'magx_lowess': results[i][-7],
                         'magy_lowess': results[i][-6],
                         'magz_lowess': results[i][-5],
                         'mag': results[i][-12],
                         'mag_kalman': results[i][-8],
                         'mag_lowess': results[i][-4],
                         'timestamp': dataframes[i]['timestamp'],
                         'intersection_points': dataframes[i]['intersection_points'],
                         'label': dataframes[i]['label']}
        for dbm in dataframes[i].columns.to_list():
            if 'dbm' in dbm:
                new_df_dict_s[dbm] = dataframes[i][dbm]

        new_df_dict_r = {'lat': dataframes[i + 1]['lat'],
                         'lon': dataframes[i + 1]['lon'],
                         'bear': dataframes[i + 1]['bear'],
                         'heading': dataframes[i + 1]['heading'],
                         'magx_kalman': results[i + 1][-11],
                         'magy_kalman': results[i + 1][-10],
                         'magz_kalman': results[i + 1][-9],
                         'magx_lowess': results[i + 1][-7],
                         'magy_lowess': results[i + 1][-6],
                         'magz_lowess': results[i + 1][-5],
                         'mag': results[i + 1][-12],
                         'mag_kalman': results[i + 1][-8],
                         'mag_lowess': results[i + 1][-4],
                         'timestamp': dataframes[i + 1]['timestamp'],
                         'intersection_points': dataframes[i + 1]['intersection_points'],
                         'label': dataframes[i + 1]['label']}
        for dbm in dataframes[i + 1].columns.to_list():
            if 'dbm' in dbm:
                new_df_dict_r[dbm] = dataframes[i + 1][dbm]
        
        new_df_s = pd.DataFrame(new_df_dict_s)
        new_df_r = pd.DataFrame(new_df_dict_r)
        new_df = pd.concat([new_df_s, new_df_r], sort=False)

        columns = new_df.columns.tolist()

        non_dbm_columns = [x for x in columns if '_dbm' not in x]
        dbm_columns = [x for x in columns if '_dbm' in x] 
        
        col = non_dbm_columns[:-1] + dbm_columns + non_dbm_columns[-1:]
        new_df = new_df[col]
        s = 'master_' + \
            str(lowess_param) + '_' + \
            str(dbm_rounding) + '_' + \
            str(i//2) + '.csv'
        new_df.to_csv(pathlib.Path(main_train_dir_path, s), index=False)

        all_df.append(new_df)

    # master.csv file creation
    df = pd.concat(all_df, ignore_index=True, sort=False)
    df.fillna(0, inplace = True)

    columns = df.columns.tolist()

    non_dbm_columns = [x for x in columns if '_dbm' not in x]
    dbm_columns = [x for x in columns if '_dbm' in x] 
    
    col = non_dbm_columns[:-1] + dbm_columns + non_dbm_columns[-1:]
    df = df[col]
    s = 'master_' + str(lowess_param) + '_' + str(dbm_rounding) + '.csv'
    df.to_csv(pathlib.Path(main_train_dir_path, s), index=False)

    input('master csv file creation - DONE')
    
    for i in range(0, len(results), 2):
        cleaner_utils.plot_signal_strength(
            signal=[results[i][-8], results[i + 1][-8]],
            labels=['sidewalk', 'road'],
            title='combined magnetometer - kalman filtered')
        cleaner_utils.plot_signal_strength(
            signal=[results[i][-4], results[i + 1][-4]],
            labels=['sidewalk', 'road'],
            title='combined magnetometer - lowess filtered')
        input('next...')
        cleaner_utils.plot_dbm_occurence_timeseries(dataframes[i], 
            xvlines=results[i][-3])
        cleaner_utils.plot_dbm_occurence_timeseries(dataframes[i + 1], 
            xvlines=results[i + 1][-3])
        cleaner_utils.plot_dbm_heatmap_timeseries(dataframes[i], 
            xvlines=results[i][-3])
        cleaner_utils.plot_dbm_heatmap_timeseries(dataframes[i + 1], 
            xvlines=results[i + 1][-3])
        input('plot ' + str(i))


    input('results plotting - DONE')
    return
                              

def master_cleanup(train_dir):
    train_files = cleaner_utils._get_clean_train_filepaths(train_dir)
    dataframes = []

    for train_file in train_files:
        dataframes.append(pd.read_csv(train_file))

    # cleaner_utils.get_signal_peaks(dataframes[0]['mag_y'].values.copy(), thres=0.9)
    # dataframes[0].loc[0:16,'mag_y'] -= 30
    dataframes[0] = dataframes[0].loc[20:]

    dataframes[1].loc[0:473,'mag_x'] -= 90
    dataframes[1].loc[0:6,'mag_y'] -= 8
    dataframes[1].loc[0:471,'mag_z'] -= 25
    dataframes[1].loc[0:1793,'mag_z'] -= 10

    dataframes[2] = dataframes[2][6:]

    dataframes[3] = dataframes[3][24:4322]

    dataframes[5].loc[0:544,'mag_x'] -= 40
    dataframes[5].loc[0:543,'mag_y'] += 25
    dataframes[5].loc[0:2088,'mag_y'] -= 20

    dataframes[6].loc[4290:,'mag_x'] -= 20

    dataframes[7].loc[10:2826,'mag_x'] -= 30
    dataframes[7] = dataframes[7][9:]
    # dataframes[7].loc[0:2820,'mag_z'] += 13

    dataframes[10] = dataframes[10][57:4612]
    dataframes[10].loc[3387:,'mag_y'] -= 10

    dataframes[11].loc[2249:4448,'mag_x'] -= 25

    dataframes[12].loc[0:1590,'mag_x'] += 15

    dataframes[16].loc[108:128,'mag_x'] -= 20
    dataframes[16] = dataframes[16][30:3073]

    dataframes[18] = dataframes[18][19:2697]

    dataframes[20] = dataframes[18][:3654]

    dataframes[22].loc[0:69,'mag_x'] -= 90
    dataframes[22].loc[0:69,'mag_y'] -= 20

    dataframes[23].loc[2347:2654,'mag_x'] -= 80
    dataframes[23].loc[2734:,'mag_y'] -= 8
    dataframes[23].loc[2347:2623,'mag_z'] -= 25

    # for i in range(0, len(dataframes)):
    #     print(i, dataframes[i]['mag_z'].shape)
    #     # try:
    #     cleaner_utils.get_signal_peaks(dataframes[i]['mag_z'].values.copy(), thres=0.9)
    #     # except:
    #     #     print(dataframes[i]['mag_x'].values)
    #     # cleaner_utils.plot_signal_strength(
    #     #     signal=[dataframes[i]['mag_x'].values,
    #     #             dataframes[i + 1]['mag_x'].values],
    #     #     labels=['sidewalk', 'road'],
    #     #     title='combined magnetometer - kalman filtered')
    #     input('next')
    # exit(0)

    # t = 0.05
    # while t <= 0.125:
    #     plot_all_df_details(
    #         dataframes, train_dir, lowess_param=t, dbm_rounding=10)
    #     t += 0.005
    # # cleaner_utils.print_dbm_occurence_percentage(dataframes[0])

    # results = []

    # dataframes[20] =  dataframes[20][360:]
    # dataframes[21] =  dataframes[21][130:]
    # dataframes[21] =  dataframes[21][:dataframes[20].shape[0]]
    
    # results.append(
    #     cleaner_utils.get_magnetometer_details(
    #         dataframes[20], lowess_param=0.75, interactive=False))
    # results.append(
    #     cleaner_utils.get_magnetometer_details(
    #         dataframes[21], lowess_param=0.75, interactive=False))
    # cleaner_utils.plot_signal_strength(
    #         signal=[results[0][-4], results[1][-4]],
    #         labels=['sidewalk', 'road'],
    #         title='combined magnetometer - lowess filtered')
    # cleaner_utils.plot_signal_strength(
    #         signal=[results[0][-8], results[1][-8]],
    #         labels=['sidewalk', 'road'],
    #         title='combined magnetometer - lowess filtered')

    # input()
    # exit(0)
    # plot_all_df_details(dataframes, train_dir, lowess_param=0.075, dbm_rounding=5)
    # exit(0)

    # signal = dataframes[0]['mag_x'].values
    # # signal2 = dataframes[20]['mag_y'].values
    # # signal3 = dataframes[20]['mag_z'].values
    # # # filtered = cleaner_utils.get_kalman_filtered(signal)
    # l_filtered = cleaner_utils.get_lowess_filtered(signal)
    # # l_filtered2 = cleaner_utils.get_lowess_filtered(signal2)
    # # l_filtered3 = cleaner_utils.get_lowess_filtered(signal3)

    # plt.ion()
    # plt.figure()
    
    # plt.plot(range(len(signal)), signal, label='Raw magnetometer signal')
    # plt.xticks([0, 500, 798, 1000, 1500, 1607, 2000, 2395, 2500, 3000, 3013])
    # plt.axvline(798, color='r')
    # plt.axvline(1607, color='r')
    # plt.axvline(2395, color='r')
    # plt.axvline(3013, color='r')
    # # plt.plot(range(len(signal2)), signal2, label='Raw magnetometer Y-axis')
    # # plt.plot(range(len(signal3)), signal3, label='Raw magnetometer Z-axis')

    # # plt.plot(range(len(filtered)), filtered, label='', linewidth=4)
    # plt.plot(range(len(l_filtered)), l_filtered, label='Kalman-filtered signal', linewidth=2)
    # # plt.plot(range(len(l_filtered2)), l_filtered2, label='Magnetometer Y-axis', linewidth=2)
    # # plt.plot(range(len(l_filtered3)), l_filtered3, label='Magnetometer Z-axis', linewidth=2)
    # # plt.plot(range(len(results[0][-4])), results[0][-4], label='TMI - Road \'A\' Lane', linewidth=4)
    # # plt.plot(range(len(results[1][-4])), results[1][-4], label='TMI - Road \'B\' Lane', linewidth=4)
    # # plt.scatter(range(len(signal)), signal, s=0.1)
    # # plt.gca().get_xaxis().set_visible(False)
        
    # # plt.title('Road Lane \'A\'', fontsize=32)
    # plt.ylabel('magnetic field strength (µT)', fontsize=32)
    # plt.xlabel('timestep', fontsize=32)
    # plt.legend()
    # plt.show()

    # input()
    # exit(0)


    # cleaner_utils.get_magnetometer_details(dataframes[0], plot=True, interactive=True)
    results = cleaner_utils.get_magnetometer_details(
        dataframes[1], interactive=False)
    xvlines = []
    xvlines.extend(results[-3])
    xvlines.append(results[-3][-1] + results[-3][0])
    # xvlines.extend(results[-2])
    # xvlines.extend(results[-1])
    input('no lowpass - DONE')
    # cleaner_utils.get_magnetometer_details(dataframes[0], lowpass=True)
    # cleaner_utils.plot_dbm_occurence_timeseries(dataframes[0])#, xvlines=xvlines)
    cleaner_utils.plot_dbm_heatmap_timeseries(dataframes[1])#, xvlines=xvlines)
    input('heatmap plot - DONE')

    print(dataframes[1].columns.to_list())
    df = cleaner_utils.clean_non_ocurring_dbm(dataframes[1])
    print(df.columns.to_list())
    # cleaner_utils.plot_dbm_occurence_timeseries(df, xvlines=xvlines)
    cleaner_utils.plot_dbm_heatmap_timeseries(df, xvlines=xvlines)

    print(df.iloc[120])
    input('heatmap plot2 - DONE')

    d3 = cleaner_utils.clean_n_strongest_dbm(df, 3)
    # cleaner_utils.plot_dbm_occurence_timeseries(d3, xvlines=xvlines)
    cleaner_utils.plot_dbm_heatmap_timeseries(d3, xvlines=xvlines)

    print(d3.iloc[120])
    input('heatmap plot3 - DONE')

    exit(0)


def main():
    master_cleanup('1000cid_nskip')


if __name__ == '__main__':
    main()

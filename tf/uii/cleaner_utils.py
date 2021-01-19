import pathlib
import math

from statsmodels.nonparametric.smoothers_lowess import lowess
from scipy.signal import freqz, butter, lfilter
from pykalman import KalmanFilter

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import peakutils


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


def autocor(x):
  result = np.correlate(x, x, mode='full')
  return result[int(result.size/2):]


def shift_signal(signal, shift=-1, ran=(0,0)):
    signal[ran[0]:ran[1]] -= shift


def get_signal_peaks(signal, thres=0.50):
    peak_indices = peakutils.indexes(signal, thres=thres)
    y = [signal[i] for i in peak_indices]

    if len(y) != 0:
        avg = sum(y) / len(y)
    else:
        avg = 0

    overflow_indices = [i for i in peak_indices if signal[i] >= avg]
    overflow_peaks = [i for i in y if i >= avg]
    
    plt.plot(range(len(signal)), signal)
    plt.plot(peak_indices, y, marker='x', color='b', label='peaks')
    try:
        plt.plot(overflow_indices, overflow_peaks, marker='x', color='r')
    except:
        print(overflow_indices)
        print(overflow_peaks)
    plt.axhline(avg, linewidth=4, color='r')
    plt.show()


def get_signal_freq_index(signal):
    ult_autocor = autocor(signal).copy()
    new_autocor = []
    maxx = 0
    x_in = 0
    for i in range(len(ult_autocor)):
        if i <= 200:
            new_autocor.append(0)
        else:
            new_autocor.append(ult_autocor[i])

        if new_autocor[i] > maxx:
            maxx = new_autocor[i]
            x_in = i 
    
    return x_in


def freq_from_autocorr(sig, fs):
    # Calculate autocorrelation and throw away the negative lags
    corr = np.correlate(sig, sig, mode='full')
    corr = corr[len(corr)//2:]

    # Find the first low point
    d = np.diff(corr)
    print(d)
    start = np.nonzero(d > 0)[0][0]
    peak = 0
    start = 0
    peaks = []
    while peak < len(corr):
        peaks.append(peak)
        d = np.diff(corr)
        start += np.nonzero(d > 0)[0][0]
        peak += np.argmax(corr[start:]) + start
    
    return peaks
    
    
def butter_bandpass(lowcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    b, a = butter(order, low, btype='low')
    return b, a


def butter_bandpass_filter(data, lowcut, fs, order=5):
    b, a = butter_bandpass(lowcut, fs, order=order)
    y = lfilter(b, a, data)
    return y


def clean_signal_peaks(signal, thres=0.50):
    s = signal.copy()
    indices = peakutils.indexes(s, thres=thres)
    y = [s[j] for j in indices]
    avg = sum(y) / len(y)

    overflow_indices = [i for i in indices if s[i] >= avg]
    overflow_peaks = [i for i in y if i > avg]

    for overflow_index in range(len(s)):
        #move to the left, if possible:
        leftward_index = overflow_index
        while leftward_index >= 0 and s[leftward_index] > avg:
            leftward_index -= 1

        rightward_index = overflow_index
        while rightward_index < len(s) and s[rightward_index] > avg:
            rightward_index += 1

        leftward_distance = abs(overflow_index - leftward_index)
        rightward_distance = abs(rightward_index - overflow_index)

        if leftward_distance < rightward_distance and s[leftward_index] < avg:
            s[overflow_index] = s[leftward_index]
        else:
            s[overflow_index] = s[rightward_index]
    
    return s


def clean_n_strongest_dbm(dataframe, n=3, rounding=None):
    df = dataframe.copy()

    dbm_columns = [col for col in df.columns.to_list() if 'dbm' in col]

    for i in df.index:
        d = df.loc[i, dbm_columns]
        n_largest_index = d.nsmallest(3, keep='first').index

        null_cols = [col for col in dbm_columns 
                    if col not in n_largest_index]

        df.loc[i, null_cols] = 0

        if rounding is not None and rounding != -1:
            df.loc[i, n_largest_index] = (
                int(rounding) * round(df.loc[i, n_largest_index]/int(rounding)))

    return df


def clean_non_ocurring_dbm(dataframe):
    df = dataframe.copy()

    dbm_columns = [col for col in df.columns.to_list() if 'dbm' in col]
    results = get_magnetometer_details(df, interactive=False)
    cid_stats = {k : [] for k in dbm_columns}

    r = results[-3].tolist()
    r.insert(0, 0)
    for i in range(len(r) - 1):
        for dbm_col in dbm_columns:
            s = df[dbm_col][r[i]:r[i + 1]].value_counts()
            cid_stats[dbm_col].append((r[i + 1] - r[i]) - s.loc[0])
    print(cid_stats)

    dbm_col_to_drop = []
    for dbm_col in dbm_columns:
        print(dbm_col, np.std(cid_stats[dbm_col]))
        if 0 in cid_stats[dbm_col]:
            dbm_col_to_drop.append(dbm_col)

    df.drop(columns=dbm_col_to_drop, inplace=True)

    return df


def print_dbm_occurence_percentage(dataframe):
    df = dataframe.copy()

    columns = df.columns.to_list()
    print(columns)    

    dbm_columns = [col for col in columns if 'dbm' in col]
    
    for dbm_col in dbm_columns:
        s = df[dbm_col].value_counts(normalize=True)
        print(s.name, 100 - (s.loc[0] * 100))


def dbm_str_occurence(dbm, cid):
    if dbm != 0:
        return str(cid) 
    else:
        return str(0)


def plot_dbm_occurence_timeseries(dataframe, xvlines=None):
    df = dataframe.copy()

    dummy = []
    dbm_occurences = []
    for dbm in df.columns.to_list():
        if 'dbm' in dbm:
            result = [dbm_str_occurence(x, dbm) for x in df[dbm].values]
            dummy.append(result)

    for i in range(len(dummy[0])):
        entry = []
        for j in range(len(dummy)):
            entry.append(dummy[j][i])
        dbm_occurences.append(entry)
    
    XVals = range(len(df.values))
    YVals = dbm_occurences.copy()

    X = [XVals[i] for i, data in enumerate(YVals) for j in range(len(data))]
    Y = [val for data in YVals for val in data]

    plt.ion()
    plt.figure(figsize=(26, 16))
    plt.scatter(X, Y, s=0.2)

    if xvlines is not None:
        for vline in xvlines:
            plt.axvline(vline, color='r')

    plt.show()


def plot_dbm_heatmap_timeseries(dataframe, xvlines=None):
    df = dataframe.copy()

    dummy = []
    x = range(len(df))
    y = []
    col = ['33_dbm', '25_dbm', '181_dbm', '208_dbm', '200_dbm', '189_dbm']
    for dbm in col:
    # for dbm in df.columns.to_list():
        if 'dbm' in dbm:
            df[dbm].replace(to_replace=0, value=np.nan, inplace=True)
            result = [x for x in df[dbm].values]
            y.append(dbm)
            dummy.append(result)

    dummy = list(reversed(dummy.copy()))
    y = list(reversed(y.copy()))
    y = [str(cid)[:str(cid).find('_')] for cid in y]
    fig, ax = plt.subplots()
    im = ax.imshow(np.array(dummy), aspect='auto', interpolation=None, cmap='OrRd') 
    ax.set_yticks(np.arange(len(y)))
    ax.set_yticklabels(y)
    # ax.set_xticks([0, 500, 798, 1000, 1500, 1607, 2000, 2395, 2500, 3000, 3013])
    ax.set_ylabel(ylabel='Serving Cell ID', fontsize=24)
    ax.set_xlabel(xlabel='timestep', fontsize=24)
    ax.grid(which='minor', axis='y', color='w', linestyle='-', linewidth=2)

    cbar = fig.colorbar(im, ax=ax)
    cbar.ax.set_ylabel('RSRP (dBm)', fontsize=24)

    if xvlines is not None:
        for vline in xvlines:
            ax.axvline(vline, color='b')

    fig.tight_layout()
    plt.title('Road Lane \'B\'', fontsize=28)
    # plt.axvline(798, color='b')
    # plt.axvline(1607, color='b')
    # plt.axvline(2395, color='b')
    # plt.axvline(3013, color='b')
    plt.show()


def plot_signal_strength(signal, labels, title, y_lims=None, xvlines=None):
    plt.ion()
    plt.figure()
    # plt.figure(figsize=(26, 16))
    
    for i in range(len(signal)):
        if labels[i] == '':
            plt.plot(range(len(signal[i])), signal[i])
        else:
            plt.plot(range(len(signal[i])), signal[i], label=labels[i])
    # for mag in signal:
    #     plt.plot(range(len(mag)), mag, label=label_name)
    #     #plt.scatter(range(len(mag)), mag, s=0.1)
        
    if y_lims is not None and len(y_lims) == 2:
        axes = plt.gca()
        axes.set_ylim(y_lims)
        
    if xvlines is not None:
        for vline in xvlines:
            plt.axvline(vline, color='r')
            
    plt.title(title)
    plt.ylabel('magnetic field strength (µT)')
    plt.xlabel('timestep')
    plt.legend()
    plt.show()


def get_lowpass_filtered(data, fs=166, lowcut=11, order=6):
    return butter_bandpass_filter(data, lowcut, fs, order=order)


def get_lowess_filtered(data, frac=0.050):
    return lowess(data, range(len(data)), frac=frac)[:, 1]


def get_kalman_filtered(data, n_iter=10):
    kf = KalmanFilter()

    return kf.em(data, n_iter=n_iter).smooth(data)[0][:, 0]


def get_combined_mag_strength(magx, magy, magz):
    mag_values = [list(i) for i in zip(magx, magy, magz)]
    mag_strength = [math.sqrt(math.pow(x, 2) + math.pow(y, 2) + math.pow(z, 2))
                    for x, y, z in mag_values]
    
    return mag_strength


def get_magnetometer_details(
    dataframe, 
    lowpass=False, 
    lowess_param=0.050,
    plot=False, 
    interactive=True):
    results = []

    df = dataframe.copy()

    magx = df['mag_x'].values 
    magy = df['mag_y'].values
    magz = df['mag_z'].values

    if lowpass:
        magx = get_lowpass_filtered(magx.copy())
        magy = get_lowpass_filtered(magy.copy())
        magz = get_lowpass_filtered(magz.copy())
    
    combined_raw  = get_combined_mag_strength(magx, magy, magz)
    results.append(magx)
    results.append(magy)
    results.append(magz)
    results.append(combined_raw)

    autocor_raw_x = autocor(magx)
    autocor_raw_y = autocor(magy)
    autocor_raw_z = autocor(magz)
    autocor_combined_raw = autocor(combined_raw)

    autocor_raw_x_peaks_indices = peakutils.indexes(autocor_raw_x, thres=0.90) 
    autocor_raw_x_peaks = [autocor_raw_x[i] 
                           for i in autocor_raw_x_peaks_indices]
    autocor_raw_y_peaks_indices = peakutils.indexes(autocor_raw_y, thres=0.90) 
    autocor_raw_y_peaks = [autocor_raw_y[i] 
                           for i in autocor_raw_y_peaks_indices]
    autocor_raw_z_peaks_indices = peakutils.indexes(autocor_raw_z, thres=0.90) 
    autocor_raw_z_peaks = [autocor_raw_z[i] 
                           for i in autocor_raw_z_peaks_indices]

    kalman_x = get_kalman_filtered(magx)
    kalman_y = get_kalman_filtered(magy)
    kalman_z = get_kalman_filtered(magz)
    combined_kalman = get_combined_mag_strength(kalman_x, kalman_y, kalman_z)
    results.append(kalman_x)
    results.append(kalman_y)
    results.append(kalman_z)
    results.append(combined_kalman)

    autocor_kx = autocor(kalman_x)
    autocor_ky = autocor(kalman_y)
    autocor_kz = autocor(kalman_z)
    autocor_combined_kalman = autocor(combined_kalman)

    autocor_kalman_x_peaks_indices = peakutils.indexes(autocor_kx, thres=0.15)
    autocor_kalman_x_peaks = [autocor_kx[i]
                              for i in autocor_kalman_x_peaks_indices]
    autocor_kalman_y_peaks_indices = peakutils.indexes(autocor_ky, thres=0.15)
    autocor_kalman_y_peaks = [autocor_ky[i]
                              for i in autocor_kalman_y_peaks_indices]
    autocor_kalman_z_peaks_indices = peakutils.indexes(autocor_kz, thres=0.15)
    autocor_kalman_z_peaks = [autocor_kz[i]
                              for i in autocor_kalman_z_peaks_indices]
    
    lowess_x = get_lowess_filtered(magx, frac=lowess_param)
    lowess_y = get_lowess_filtered(magy)
    lowess_z = get_lowess_filtered(magz)
    combined_lowess = get_combined_mag_strength(lowess_x, lowess_y, lowess_z)
    results.append(lowess_x)
    results.append(lowess_y)
    results.append(lowess_z)
    results.append(combined_lowess)

    autocor_lx  =  autocor(lowess_x)
    autocor_ly  =  autocor(lowess_y)
    autocor_lz  =  autocor(lowess_z)
    autocor_combined_lowess = autocor(combined_lowess)

    autocor_lowess_x_peaks_indices = peakutils.indexes(autocor_lx, thres=0.15)
    autocor_lowess_x_peaks = [autocor_lx[i]
                              for i in autocor_lowess_x_peaks_indices]
    autocor_lowess_y_peaks_indices = peakutils.indexes(autocor_ly, thres=0.15)
    autocor_lowess_y_peaks = [autocor_ly[i]
                              for i in autocor_lowess_y_peaks_indices]
    autocor_lowess_z_peaks_indices = peakutils.indexes(autocor_lz, thres=0.15)
    autocor_lowess_z_peaks = [autocor_lz[i]
                              for i in autocor_lowess_z_peaks_indices]
    results.append(autocor_lowess_x_peaks_indices)
    results.append(autocor_lowess_y_peaks_indices)
    results.append(autocor_lowess_z_peaks_indices)

    kalman_lowess_x = get_lowess_filtered(kalman_x)
    kalman_lowess_y = get_lowess_filtered(kalman_y)
    kalman_lowess_z = get_lowess_filtered(kalman_z)
    combined_kalman_lowess = get_combined_mag_strength(
        kalman_lowess_x, kalman_lowess_y, kalman_lowess_z)
    # results.append(kalman_lowess_x)
    # results.append(kalman_lowess_y)
    # results.append(kalman_lowess_z)
    # results.append(combined_kalman_lowess)

    autocor_klx  =  autocor(kalman_lowess_x)
    autocor_kly  =  autocor(kalman_lowess_y)
    autocor_klz  =  autocor(kalman_lowess_z)
    autocor_combined_kalman_lowess = autocor(combined_kalman_lowess)

    autocor_kalman_lowess_x_peaks_indices = peakutils.indexes(autocor_klx, thres=0.15)
    autocor_kalman_lowess_x_peaks = [autocor_klx[i]
                              for i in autocor_kalman_lowess_x_peaks_indices]
    autocor_kalman_lowess_y_peaks_indices = peakutils.indexes(autocor_kly, thres=0.15)
    autocor_kalman_lowess_y_peaks = [autocor_kly[i]
                              for i in autocor_kalman_lowess_y_peaks_indices]
    autocor_kalman_lowess_z_peaks_indices = peakutils.indexes(autocor_klz, thres=0.15)
    autocor_kalman_lowess_z_peaks = [autocor_klz[i]
                              for i in autocor_kalman_lowess_z_peaks_indices]
    # results.append(autocor_kalman_lowess_x_peaks_indices)
    # results.append(autocor_kalman_lowess_y_peaks_indices)
    # results.append(autocor_kalman_lowess_z_peaks_indices)

    if not plot:
        return results


    """
    MAGNETOMETER X
    """
    plot_signal_strength(signal=[magx], labels=[''],
        title='Raw magnetic field intensity - X-axis')
    plot_signal_strength(signal=[magx, kalman_x, lowess_x, kalman_lowess_x], 
        labels=['magx', 'kalman_x', 'lowess_x', 'kalman_lowess_x'],
        title='magx', xvlines=autocor_lowess_x_peaks_indices)
    plot_signal_strength(
        signal=[autocor_raw_x, autocor_kx, autocor_lx, autocor_klx], 
        labels=['autocor_raw_x', 'autocor_kx', 'autocor_lx', 'autocor_klx'], 
        title='autocorrelated magx')
    
    plt.figure()
    plt.plot(range(len(autocor_raw_x)), autocor_raw_x, label='autocor raw x')
    plt.plot(autocor_raw_x_peaks_indices, autocor_raw_x_peaks, 
        marker='x', color='r')
    plt.show()

    plt.figure()
    plt.plot(range(len(autocor_kx)), autocor_kx, label='autocor kalman x')
    plt.plot(autocor_kalman_x_peaks_indices, autocor_kalman_x_peaks, 
        marker='x', color='r')
    plt.legend()
    plt.show()

    plt.figure()
    plt.plot(range(len(autocor_lx)), autocor_lx)
    # plt.plot(range(len(autocor_lx)), autocor_lx, label='autocor lowess x')
    plt.plot(autocor_lowess_x_peaks_indices, autocor_lowess_x_peaks, 
        marker='x', color='r')
    for i in range(len(autocor_lowess_x_peaks_indices)):
        plt.annotate(
            'i = ' + str(autocor_lowess_x_peaks_indices[i]), 
            xy=(autocor_lowess_x_peaks_indices[i], autocor_lowess_x_peaks[i]))
    plt.title('Autocorrelated Magnetometer Signal')
    plt.legend()
    plt.show()

    plt.figure()
    plt.plot(
        range(len(autocor_klx)), autocor_klx, label='autocor kalman lowess x')
    plt.plot(
        autocor_kalman_lowess_x_peaks_indices, autocor_kalman_lowess_x_peaks, 
        marker='x', color='r')
    plt.legend()
    plt.show()

    if interactive:
        input('MAGNETOMETER X')

    """
    MAGNETOMETER Y
    """
    plot_signal_strength(signal=[magy], labels=['raw'],
        title='Raw magnetic field intensity - Y-axis')
    plot_signal_strength(signal=[magy, kalman_y, lowess_y, kalman_lowess_y], 
        labels=['magy', 'kalman_y', 'lowess_y', 'kalman_lowess_y'],
        title='magy', xvlines=autocor_lowess_y_peaks_indices)
    plot_signal_strength(
        signal=[autocor_raw_y, autocor_ky, autocor_ly, autocor_kly], 
        labels=['autocor_raw_y', 'autocor_ky', 'autocor_ly', 'autocor_kly'], 
        title='autocorrelated magy')

    plt.figure()
    plt.plot(range(len(autocor_raw_y)), autocor_raw_y, label='autocor raw y')
    plt.plot(autocor_raw_y_peaks_indices, autocor_raw_y_peaks, 
        marker='x', color='r')
    plt.show()

    plt.figure()
    plt.plot(range(len(autocor_ky)), autocor_ky, label='autocor kalman y')
    plt.plot(autocor_kalman_y_peaks_indices, autocor_kalman_y_peaks, 
        marker='x', color='r')
    plt.legend()
    plt.show()

    plt.figure()
    plt.plot(range(len(autocor_ly)), autocor_ly, label='autocor lowess y')
    plt.plot(autocor_lowess_y_peaks_indices, autocor_lowess_y_peaks, 
        marker='x', color='r')
    plt.legend()
    plt.show()

    plt.figure()
    plt.plot(
        range(len(autocor_kly)), autocor_kly, label='autocor kalman lowess y')
    plt.plot(
        autocor_kalman_lowess_y_peaks_indices, autocor_kalman_lowess_y_peaks, 
        marker='x', color='r')
    plt.legend()
    plt.show()

    if interactive:
        input('MAGNETOMETER Y')

    """
    MAGNETOMETER Z
    """
    plot_signal_strength(signal=[magz], labels=['raw'],
        title='Raw magnetic field intensity - Z-axis')
    plot_signal_strength(signal=[magz, kalman_z, lowess_z, kalman_lowess_z], 
        labels=['magz', 'kalman_z', 'lowess_z', 'kalman_lowess_z'],
        title='magz', xvlines=autocor_lowess_z_peaks_indices)
    plot_signal_strength(
        signal=[autocor_raw_z, autocor_kz, autocor_lz, autocor_klz], 
        labels=['autocor_raw_z', 'autocor_kz', 'autocor_lz', 'autocor_klz'], 
        title='autocorrelated magz')

    plt.figure()
    plt.plot(range(len(autocor_raw_z)), autocor_raw_z, label='autocor raw z')
    plt.plot(autocor_raw_z_peaks_indices, autocor_raw_z_peaks, 
        marker='x', color='r')
    plt.show()

    plt.figure()
    plt.plot(range(len(autocor_kz)), autocor_kz, label='autocor kalman z')
    plt.plot(autocor_kalman_z_peaks_indices, autocor_kalman_z_peaks, 
        marker='x', color='r')
    plt.legend()
    plt.show()

    plt.figure()
    plt.plot(range(len(autocor_lz)), autocor_lz, label='autocor lowess z')
    plt.plot(autocor_lowess_z_peaks_indices, autocor_lowess_z_peaks, 
        marker='x', color='r')
    plt.legend()
    plt.show()
    
    plt.figure()
    plt.plot(
        range(len(autocor_klz)), autocor_klz, label='autocor kalman lowess z')
    plt.plot(
        autocor_kalman_lowess_z_peaks_indices, autocor_kalman_lowess_z_peaks, 
        marker='x', color='r')
    plt.legend()
    plt.show()

    if interactive:
        input('MAGNETOMETER Z')

    """
    COMBINED MAGNETOMETER 
    """
    freq_lines = []
    freq_lines.extend(autocor_lowess_x_peaks_indices)
    freq_lines.extend(autocor_lowess_y_peaks_indices)
    freq_lines.extend(autocor_lowess_z_peaks_indices)

    plot_signal_strength(signal=[combined_raw],
        labels=['raw'],
        title='Combined magnetic field intensity - X,Y,Z-axis')
    plot_signal_strength(signal=[combined_raw, combined_kalman, combined_lowess], 
        labels=['combined_raw', 'combined_kalman', 'combined_lowess'], 
        title='Combined magnetic field intensity', xvlines=freq_lines)
    plot_signal_strength(
        signal=[autocor_combined_raw, autocor_combined_kalman, autocor_combined_lowess], 
        labels=['autocor_combined_raw', 'autocor_combined_kalman', 'autocor_combined_lowess'], 
        title='autocorrelated combined magnetometer')

    if interactive:
        input('COMBINED MAGNETOMETER')

    plt.close('all')

    return results


def main():
    return 0


if __name__ == '__main__':
    main()
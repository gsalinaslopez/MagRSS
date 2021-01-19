import csv
import datetime
import pathlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import tensorflow as tf
from tensorflow import keras
from tensorflow import feature_column



""" 
Data handling and generators
"""
def _get_clean_train_filepaths(train_data_dir):
    """Crawls directory specified in @train_data_dir
    
    Assumes the master train folder is located at `cwd`../train

    Returns:
        An array containing the filepaths of the clean train files
    """
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


def _get_clean_train_files_columns(train_data_dir):
    """Creates a CSV dictionary reader for each file in @train_data_dir

    Returns:
        A list containing the headers of all the files, no repetitions
    """
    clean_train_files = _get_clean_train_filepaths(train_data_dir)
    
    all_headers = []
    for file in clean_train_files:
        with open(str(file)) as csv_file:
            all_headers += [x for x in csv.DictReader(csv_file).fieldnames]
            csv_file.close()
    
    return list(set(all_headers))


def _get_train_files_column_subset(
    train_data_dir, 
    columns_to_select=None,
    include_dbm=False):
    """Retrieves a subset from the columns of all the files in @train_data_dir
    """
    # If select columns is not specified, select them all by default
    file_column_names = _get_clean_train_files_columns(train_data_dir)

    if columns_to_select is None:
        selected_columns = [x for x in file_column_names if '_dbm' not in x]
    else:
        selected_columns = list(
            set(file_column_names).intersection(columns_to_select))

    if include_dbm:
        dbm_column_names = [x for x in file_column_names if '_dbm' in x]
        selected_columns += dbm_column_names

    selected_columns.append('label')

    return list(set(selected_columns))


def get_pd_dataframe_from_dir(train_data_dir):
    clean_train_files = _get_clean_train_filepaths(train_data_dir)

    # setup pandas dataframe
    df = pd.concat([pd.read_csv(x) for x in clean_train_files], sort=False)

    return df


def dataframe_to_dataset_input_fn(
    df, 
    shuffle=True, 
    batch_size=32):
    dataframe = df.copy()
    labels = dataframe.pop('label')

    dataset = tf.data.Dataset.from_tensor_slices(
        (dataframe.to_dict('list'), labels.values))

    if shuffle:
        dataset = dataset.shuffle(buffer_size=len(dataframe))

    return dataset.batch(batch_size).repeat()
    

def get_dataset_from_csv_dir(
    train_data_dir, 
    batch_size=32, 
    columns_to_select=None,
    include_dbm=False):
    clean_train_files = _get_clean_train_filepaths(train_data_dir)

    selected_columns = _get_train_files_column_subset(
        train_data_dir, 
        columns_to_select=columns_to_select, 
        include_dbm=include_dbm)
    
    return selected_columns
    dataset = tf.data.experimental.make_csv_dataset(
        file_pattern=clean_train_files,
        batch_size=batch_size,
        label_name='label'
    ) 

def univariate_data_np(dataset, start_index, end_index, history_size, 
                       target_size):
    data = []
    labels = []

    start_index = start_index + history_size
    if end_index is None:
        end_index = len(dataset) - target_size

    for i in range(start_index, end_index):
        indices = range(i-history_size, i)
        # Reshape data from (history_size,) to (history_size, 1)
        data.append(np.reshape(dataset[indices], (history_size, 1)))
        labels.append(dataset[i+target_size])
    return np.array(data), np.array(labels)


def multivariate_time_series_generator(data, targets, length, sampling_rate, 
                                       stride, start_index, end_index, 
                                       single_step=False):
    timeseries_data = []
    labels = []
    
    start_index = start_index + length
    if end_index is None:
        end_index = len(data) - stride
    
    for i in range(start_index, end_index):
        indices = range(i - length, i, sampling_rate)
        timeseries_data.append(data[indices])

        if single_step:
            labels.append(targets[i + stride])
        else:
            labels.append(targets[i : i + stride])
    
    return np.array(data), np.array(labels)


"""
Tf and Keras model tools
"""
def get_sequential_model(
    feature_layer=None,
    layers=[['dense', '64', 'None', 'None']]):
    """ 
    Generate a sequential keras model and attach the layers as specified in the
    @layers parameter where:

    layer = [
        'layer type', 
        '# of nodes', 
        'kernel regularizer value, if any',
        'add a dropout, if any',
        'wether to return sequence (for RNN)', 
        'is bidirectional (for RNN)]']
    """

    model = tf.keras.Sequential()
    
    if feature_layer is not None:
        model.add(feature_layer)
    
    for layer in layers:
        layer_type = str(layer[0])
        n_units = int(layer[1])

        if layer[2] != 'None':
            kernel_reg = tf.keras.regularizers.l2(float(layer[2]))
        else:
            kernel_reg = None

        dropout = str(layer[3])

        # Add up dummy values 'False' and 'False' in case input layer is not RNN
        if len(layer) <= 4:
            layer.append('False')
            layer.append('False')

        return_seq = True if str(layer[4]) == 'True' else False

        is_bidir = True if str(layer[5]) == 'True' else False

        if layer_type == 'simplernn':
            keras_layer = tf.keras.layers.SimpleRNN(
                n_units, 
                kernel_regularizer=kernel_reg,
                return_sequences=return_seq)
        elif layer_type == 'gru':
            keras_layer = tf.keras.layers.GRU(
                n_units, 
                kernel_regularizer=kernel_reg,
                return_sequences=return_seq)
        elif layer_type == 'lstm':
            keras_layer = tf.keras.layers.LSTM(
                n_units, 
                kernel_regularizer=kernel_reg, 
                return_sequences=return_seq)
        elif layer_type == 'dense':
            keras_layer = tf.keras.layers.Dense(
                n_units, 
                kernel_regularizer=kernel_reg,
                activation='relu')

        if is_bidir:
            keras_layer = tf.keras.layers.Bidirectional(keras_layer)
        
        model.add(keras_layer)

        if dropout != 'None':
            model.add(tf.keras.layers.Dropout(float(dropout)))

    model.add(tf.keras.layers.Dense(1))

    return model


def get_tensorboard_log_callback(features, args):
    """
    Generates a callback where the output dir is based on the cli arguments from 
    the calling NN.
    """
    features_dir = '_'.join([str(f) for f in features 
                             if 'label' not in f and 'dbm' not in f])
    dbm_dir = 'ydbm' if args['dbm'] else 'ndbm'
    epochs_dir = 'epochs' + str(args['epochs'])
    layers_dir = ''
    for layer in args['layers']:
        layers_dir = layers_dir + '_'.join(layer) + '_'
    datetime_file_name = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')

    tb_log_filename = '_'.join((features_dir, dbm_dir, epochs_dir, layers_dir, 
                                datetime_file_name)) 
    print(tb_log_filename)
    tb_log_path = pathlib.Path(
        pathlib.PurePath(pathlib.Path.cwd()).parent, 
        pathlib.Path('results'),
        pathlib.Path('tensorboard'),
        pathlib.Path(features_dir, dbm_dir, epochs_dir, layers_dir)
    )
    print(tb_log_path)
    if not tb_log_path.exists():
        tb_log_path.mkdir(parents=True)

    return tf.keras.callbacks.TensorBoard(
               str(pathlib.Path(tb_log_path, tb_log_filename)))

    
"""
Plotting tools
"""
def plot_train_history(history, title):
    for history_element in history.history.keys():
        if 'val_' not in history_element:
            plot_train_history_element(history, history_element, title)
    
    return


def plot_train_history_element(history, element_name, title):
    train_element_name = str(element_name)
    train_history_element = history.history[train_element_name]
    
    val_element_name = 'val_' + str(element_name)
    val_history_element = history.history[val_element_name]
    
    epochs = range(len(train_history_element))

    plt.plot(epochs, train_history_element, 'b', label=train_element_name)
    plt.plot(epochs, val_history_element, 'r', label=val_element_name)
    plt.title(title)
    plt.xlabel('epoch')
    plt.ylabel(train_element_name)
    plt.legend()

    plt.show()





def main():
    d = list(get_pd_dataframe_from_dir('1cid_nskip').columns)
    #print(d, len(d))
    h = _get_clean_train_files_columns('1cid_nskip')
    #print(h, len(h))
    i = set(d).intersection(h)
    print(i, len(i))

    k = get_dataset_from_csv_dir('1cid_nskip', 
        columns_to_select=None, 
        include_dbm=True)

    print(k, len(k))

if __name__ == '__main__':
    main()
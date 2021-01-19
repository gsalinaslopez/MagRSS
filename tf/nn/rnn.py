# TensorFlow and tf.keras
import tensorflow as tf
from tensorflow import keras
from tensorflow import feature_column
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator

# Helper libraries
import numpy as np
import pandas 
import pathlib
import os
import sys
import argparse
import datetime

import nnutils


# setup and parse cli arguments
parser = argparse.ArgumentParser(description='Back propagation NN that trains '
                                 'on data generated by the MagRss app')
parser.add_argument('--train_dir', type=str, default='2cid_nskip')
parser.add_argument('--dbm', action='store_true', help='set this flag to '
                    'include dbm entries into the featureset')
parser.add_argument('--epochs', type=int, default=10)
parser.add_argument('--batch_size', type=int, default=20)
parser.add_argument('--early_stopping', nargs=2, default=argparse.SUPPRESS, 
                    metavar=('MONITOR', 'PATIENCE'))
parser.add_argument('--features', nargs='+', type=str, 
                    default=argparse.SUPPRESS)
parser.add_argument('--layer', nargs='+', dest='layers', action='append')# , 
                    # metavar=('LAYER_TYPE', 'NUMBER_OF_NODES', 
                    #          'KERNEL_REGULARIZER', 'DROPUT', 'RETURN_SEQUENCES',
                    #          'IS_BIDIRECTIONAL'))
parser.add_argument('--tensorboard', action='store_true', 
                    help='set this flag to log history/scalar data from the ' 
                         'model\'s run')
args = vars(parser.parse_args())
if args['layers'] is None:
    args['layers'] = [['lstm', '64', 'None', 'None', 'False', 'True'],
                      ['dense', '64', 'None', 'None']] 
print(args)


df = nnutils.get_pd_dataframe_from_dir(args['train_dir'])
df.fillna(0, inplace = True)

print(df.columns)
# include/exclude cid dbm fields
if not args['dbm']:
    dbm_columns = [column for column in df.columns if 'dbm' in column]
    df.drop(columns=dbm_columns, inplace=True)

# set of features to be used for training
if 'features' in args:
    f_col = [column for column in df.columns
             if column not in args['features'] 
             and 'dbm' not in column and column != 'label']
    df.drop(columns=f_col, inplace=True)
print(df.columns, df.shape)

# train, test = train_test_split(df, test_size=0.2)
train, val = train_test_split(df, test_size=0.2)
# train, val = train_test_split(train, test_size=0.2)

# setup data arrays from pandas dataframe
batch_size = args['batch_size']
train_x = train.copy()
train_y = [[i] for i in train_x.pop('label').values]
val_x = val.copy()
val_y = [[i] for i in val_x.pop('label').values]
# test_x = test.copy()
# test_y = [[i] for i in test_x.pop('label').values]
steps_per_epoch = len(train_x.values) // batch_size

print(train_x)
print(len(train_x.values))
print(len(train_y))
print(val_x)
print(len(val_x.values))
print(len(val_y))
# print(test_x)
# print(len(test_x.values))
# print(len(test_y))

# time series generator for our RNN model
train_data_gen = TimeseriesGenerator(train_x.values, train_y, length=32, batch_size=args['batch_size'])
val_data_gen = TimeseriesGenerator(val_x.values, val_y, length=32, batch_size=args['batch_size'])
# test_data_gen = TimeseriesGenerator(test_x.values, test_y, length=32, batch_size=1)
batch_0 = train_data_gen[0]
print(batch_0)

print(steps_per_epoch)

# setup optimizer to reduce the learning rate over time
lr_schedule = tf.keras.optimizers.schedules.InverseTimeDecay(
    0.001, 
    decay_steps = steps_per_epoch * 1000, 
    decay_rate=1, 
    staircase=False)
optimizer = tf.keras.optimizers.Adam(lr_schedule)

# setup callbacks
callbacks = []
if 'early_stopping' in args:
    monitor = str(args['early_stopping'][0])
    patience = int(args['early_stopping'][1])
    callbacks.append(tf.keras.callbacks.EarlyStopping(monitor=monitor, patience=patience))

# if args['tensorboard']:
#     callbacks.append(nnutils.get_tensorboard_log_callback(train.columns, args))

layers = args['layers'].copy()
h = {}
model = nnutils.get_sequential_model(layers=layers)
model.compile(optimizer=optimizer, loss='binary_crossentropy', 
    metrics=['accuracy', 'binary_crossentropy'])
h['drop'] = model.fit_generator(
    train_data_gen, validation_data=val_data_gen, epochs=args['epochs'], 
    callbacks=callbacks, verbose=2)
<<<<<<< HEAD
<<<<<<< HEAD
exit(0)
=======
# model.summary()
=======
model.summary()
>>>>>>> 5c217fca87548048706388a9ebf0df55f50cb5ec

nnutils.plot_train_history(h['drop'], 'drop')

exit(0)
# try:
#     predictions = model.predict_generator(test_data_gen)

#     i = 0
#     total_test = len(predictions.reshape((-1)))
#     predictions = predictions.reshape(-1)
#     accurate = 0


#     for res_x, res_y in test_data_gen:
#         if round(predictions[i], 0) == float(res_y[0]):
#             accurate += 1
#         i += 1

#     accuracy = float(accurate/ total_test) 
#     print(i, len(predictions))
#     print('accurate {} out of {} [{}%]'.format(accurate, total_test, accuracy))
#     print('++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
#     #predictions = model.predict(test_data_gen)
# except:
#     print('predictionErrorViewController')
# exit(0)
>>>>>>> 21ba1687e44259f170c7639d8862ff9d8411a05e
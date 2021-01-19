from __future__ import absolute_import, division, print_function, unicode_literals

import keras;
from keras.models import Sequential;
from keras.layers import Dense;


import tensorflow as tf
from tensorflow.keras import layers

network = Sequential();

        #Hidden Layer#1
network.add(Dense(units=6,
                  activation='relu',
                  kernel_initializer='uniform',
                  input_dim=11))

        #Hidden Layer#2
network.add(Dense(units=6,
                  activation='relu',
                  kernel_initializer='uniform'))

        #Exit Layer
network.add(Dense(units=1,
                  activation='sigmoid',
                  kernel_initializer='uniform'))

import os
os.environ["PATH"] += os.pathsep + 'D:/Graphviz2.38/bin/'
from ann_visualizer.visualize import ann_viz

ann_viz(network, title="")

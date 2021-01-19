from __future__ import absolute_import, division, print_function, unicode_literals

# Helper libraries
import numpy as np
import pandas as pd
import pathlib
import itertools
import operator
import collections
import sys
import csv
import subprocess
import argparse
import datetime
from tqdm import tqdm


def get_args():
    # setup and parse cli arguments
    parser = argparse.ArgumentParser(description='Neural Network launcher '
                                     'script. Dispatches different subsets and '
                                     'permutations of featuresets, layers, and '
                                     'other tweaks to the selected neural '
                                     'network')
    parser.add_argument('--nn', choices=['rnn', 'bpnn'], default='bpnn')
    parser.add_argument('--train_dir', type=str, default='m1')
    parser.add_argument('--train_file', type=str, default='all', help='specific'
                        'file to be used, defaults to use all files in '
                        'train_dir')
    parser.add_argument('--dbm', action='store_true', help='set this flag to '
                        'include dbm entries into the featureset')
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--batch_size', type=int, default=20)
    parser.add_argument('--early_stopping', nargs=2, default=argparse.SUPPRESS, 
                        metavar=('MONITOR', 'PATIENCE'))
    parser.add_argument('--features', nargs='+', type=str, 
                        default=argparse.SUPPRESS)
    parser.add_argument('--featureset_permutation_range', nargs=1, type=int, 
                        default=argparse.SUPPRESS, help='range of the '
                        'feature-subset(s). range(len(FEATURES) - '
                        'FEATURESET_PERMUTATION_RANGE')
    parser.add_argument('--layers_permutations', action='store_true')
    args = vars(parser.parse_args())
    print(args)

    return args


def get_pd_dataframe_from_dir(train_data_dir):
    # iterate through the 'train' folder
    clean_train_files = []
    train_path = pathlib.Path('train')

    for train_dir in [x for x in train_path.iterdir() 
                      if x.is_dir() and '.' not in x.name]:
        # top 'clean' directory
        clean_dir = train_dir / train_data_dir
        for clean_train_file in [x for x in clean_dir.iterdir() 
                                 if not x.is_dir()]:
            clean_train_files.append(str(clean_train_file))
            
    df = pandas.concat(
        [pandas.read_csv(x) for x in clean_train_files], sort=True)

    return df


def get_rnn_layer_permutations():
    l1 = itertools.product(
        ['simplernn', 'gru', 'lstm'], 
        [128], 
        ['True', 'False'], 
        ['True', 'False'])
    l2 = itertools.product(
        ['simplernn', 'gru', 'lstm'], 
        [128], 
        ['True', 'False'], 
        ['True', 'False'])
    l3 = itertools.product(
        ['dense'], 
        [64])
    three_layer_stack = itertools.product(l1, l2, l3)

    l1 = itertools.product(
        ['simplernn', 'gru', 'lstm'], 
        [128], 
        ['True', 'False'], 
        ['True', 'False'])
    l2 = itertools.product(
        ['simplernn', 'gru', 'lstm'], 
        [128], 
        ['True', 'False'], 
        ['True', 'False'])
    two_rnn_layer_stack = itertools.product(l1, l2)

    l1 = itertools.product(
        ['simplernn', 'gru', 'lstm'], 
        [128], 
        ['True', 'False'], 
        ['True', 'False'])
    l3 = itertools.product(
        ['dense'], 
        [64])
    two_layer_stack = itertools.product(l1, l3)

    l1 = itertools.product(
        ['simplernn', 'gru', 'lstm'], 
        [128], 
        ['True', 'False'], 
        ['True', 'False'])
    one_layer_stack = itertools.product(l1)

    layer_stacks = []
    for x in three_layer_stack:
        instruction = ''
        for el in list(x):
            instruction = instruction + '--layer'
            for i in range(len(el) + 2):
                if i == 2 or i == 3:
                    instruction = instruction + ' ' + 'None'
                elif i == 4 or i == 5:
                    instruction = instruction + ' ' + str(el[i-2])
                else:
                    instruction = instruction + ' ' + str(el[i])
            instruction = instruction + ' '
        layer_stacks.append(instruction)
    for x in two_rnn_layer_stack:
        instruction = ''
        for el in list(x):
            instruction = instruction + '--layer'
            for i in range(len(el) + 2):
                if i == 2 or i == 3:
                    instruction = instruction + ' ' + 'None'
                elif i == 4 or i == 5:
                    instruction = instruction + ' ' + str(el[i-2])
                else:
                    instruction = instruction + ' ' + str(el[i])
            instruction = instruction + ' '
        layer_stacks.append(instruction)
    # for x in two_layer_stack:
    #     instruction = ''
    #     for el in list(x):
    #         instruction = instruction + '--layer'
    #         for i in range(len(el) + 2):
    #             if i == 2 or i == 3:
    #                 instruction = instruction + ' ' + 'None'
    #             elif i == 4 or i == 5:
    #                 instruction = instruction + ' ' + str(el[i-2])
    #             else:
    #                 instruction = instruction + ' ' + str(el[i])
    #         instruction = instruction + ' '
    #     # layer_stacks.append(instruction)
    # for x in one_layer_stack:
    #     instruction = ''
    #     for el in list(x):
    #         instruction = instruction + '--layer'
    #         for i in range(len(el) + 2):
    #             if i == 2 or i == 3:
    #                 instruction = instruction + ' ' + 'None'
    #             elif i == 4 or i == 5:
    #                 instruction = instruction + ' ' + str(el[i-2])
    #             else:
    #                 instruction = instruction + ' ' + str(el[i])
    #         instruction = instruction + ' '
    #     # layer_stacks.append(instruction)
    
    print(len(layer_stacks))
    # input('checking...')
    return layer_stacks


def get_bpnn_layer_permutations():
    l1 = itertools.product(
        ['dense'], 
        [128]) 
    l2 = itertools.product(
        ['dense'], 
        [128]) 
    dropout = itertools.product(
        ['None', '0.1', '0.01', '0.001', '0.0001'], 
        ['None', '0.2', '0.3', '0.4', '0.5'])
    two_layer_stack = itertools.product(l1, l2, dropout)

    layer_stacks = []
    for x in two_layer_stack:
        el = list(x)
        instruction = '--layer ' + str(el[0][0]) + ' ' + str(el[0][1]) + \
                      ' ' + str(el[2][0]) + ' ' + str(el[2][1]) + \
                      ' --layer ' + str(el[1][0]) + ' ' + str(el[1][1]) + \
                      ' ' + str(el[2][0]) + ' ' + str(el[2][1])
        layer_stacks.append(instruction)
        
    print(layer_stacks, len(layer_stacks))
    return layer_stacks


def dispatch_to_nn(file, df):
    args = get_args()

    # work with an specific file
    if args['train_file'] != 'all' and args['train_file'] not in file:
        return

    
    # set of features to be dispatched
    if 'features' in args:
        f_col = [column for column in df.columns 
                 if column in args['features']]
    else:
        f_col = [column for column in df.columns 
                 if 'dbm' not in column and 'label' not in column]

    # generate all feature-subsets permutations
    if 'featureset_permutation_range' not in args:
        args['featureset_permutation_range'] = len(f_col)
    else:
        args['featureset_permutation_range'] = int(
            args['featureset_permutation_range'][0])

    feature_iterations = []
    for i in range(len(f_col), args['featureset_permutation_range'] - 1, -1):
        for subset in itertools.combinations(f_col, i):
            feature_iterations.append(list(subset))

    features_cli_dispatch_iterations = [
        '--features ' + ' '.join(feature_iteration) 
        for feature_iteration in feature_iterations]
        

    # setup the .csv log file
    datetime_file_name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    cli_args_filename = [
        str(k) + str(v) for k, v in args.items() 
        if 'features' not in k and 'featureset_permutation_range' not in k]
    csv_log_filename = '_'.join(cli_args_filename) + \
                       '_' + datetime_file_name + '.csv'

    range_dir = 'range_' + str(len(f_col)) + '_' + \
                str(args['featureset_permutation_range'])

    if args['layers_permutations']:
        layers_permutations_dir = 'ylayerspermutations' 
    else:
        layers_permutations_dir = 'nlayerspermutations'
    
    results_log_path = pathlib.Path(
        'results', args['nn'], range_dir, layers_permutations_dir)

    csv_log_path = pathlib.Path(results_log_path, csv_log_filename)
    print(csv_log_path)

    if not results_log_path.exists():
        results_log_path.mkdir(parents=True)

    with open(str(csv_log_path), 'a', newline='') as csv_outfile:
            dict_writer = csv.DictWriter(
                csv_outfile,
                fieldnames = ['iteration', 
                              'loss', 
                              'acc', 
                              'binary_crossentropy', 
                              'val_loss', 
                              'val_acc', 
                              'val_binary_crossentropy'])
            dict_writer.writeheader()
            csv_outfile.close()


    # generate the cli commands to dispatch
    cli_dispatch_nn = "python " + str(pathlib.Path(args['nn'] + '_2.py')) + ' '
    cli_dispatch_dir = "--train_dir " + str(args['train_dir']) + ' '
    cli_dispatch_file = "--train_file " + str(file) + ' '
    cli_dispatch_dbm = "--dbm " if args['dbm'] else ''
    cli_dispatch_epochs = "--epochs " + str(args['epochs']) + ' '
    cli_dispatch_batch_size = "--batch_size " + str(args['batch_size']) + ' '
    # TODO: early stopping
    cli_dispatch_tensorboard = "--tensorboard" + ' '
    cli_dispatch_commands = []
    for features_cli_dispatch_iteration in features_cli_dispatch_iterations:
        cli_cmd = cli_dispatch_nn + \
                  cli_dispatch_dir + \
                  cli_dispatch_file + \
                  cli_dispatch_dbm + \
                  cli_dispatch_epochs + \
                  cli_dispatch_batch_size + \
                  cli_dispatch_tensorboard + \
                  features_cli_dispatch_iteration
        if args['layers_permutations']:
            cli_cmd += ' '
            for cli_dispatch_layer in get_bpnn_layer_permutations():
                cli_dispatch_commands.append(cli_cmd + cli_dispatch_layer)
        else:
            cli_dispatch_commands.append(cli_cmd)


    # process all cli dispatchs
    for cli_dispatch in tqdm(cli_dispatch_commands):
        print("current execution:", cli_dispatch)

        try:
            output = subprocess.check_output(cli_dispatch, cwd=str(pathlib.Path('nn')), shell=True)
            output = output.decode("utf-8")
        except:
            continue

        fit_results = output.split(' ')
        iteration_result = {'iteration' : str(cli_dispatch),
            'loss' : fit_results[-16], 
            'acc' : fit_results[-13], 
            'binary_crossentropy' : fit_results[-10],
            'val_loss' : fit_results[-7],
            'val_acc' : fit_results[-4],
            'val_binary_crossentropy' : str(fit_results[-1]).rstrip()}
        
        with open(str(csv_log_path), 'a', newline='') as csv_outfile:
            dict_writer = csv.DictWriter(csv_outfile, 
                fieldnames = ['iteration', 'loss', 'acc', 'binary_crossentropy', 'val_loss', 'val_acc', 'val_binary_crossentropy'])
            dict_writer.writerow(iteration_result)
            csv_outfile.close()

    return

def main():
    args = get_args()

    # iterate through the 'train' folder
    clean_train_files = []
    main_train_dir_path = pathlib.Path(
        pathlib.PurePath(pathlib.Path.cwd()), pathlib.Path('train'))
    
    for train_dir in [x for x in main_train_dir_path.iterdir()
                      if x.is_dir() and '.' not in x.name]:
        clean_dir = train_dir / str(args['train_dir']) #'m1'
        for clean_train_file in [x for x in clean_dir.iterdir() 
                                 if not x.is_dir()]:
            clean_train_files.append(str(clean_train_file))
            
    dataframes = []
    files = []
    for train_file in clean_train_files:
        dataframes.append(pd.read_csv(train_file))
        files.append(train_file)

    for i in range(len(dataframes)):
        print('***************************************************************')
        dispatch_to_nn(files[i], dataframes[i])


if __name__ == '__main__':
    main()

    exit(0)
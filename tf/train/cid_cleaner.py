import pathlib
import csv
import operator
import tqdm
import osmutils
import itertools
import argparse

import pandas as pd

def cleanup(file_in, file_out, num_cid, skip):
    csvfile = open(str(file_in))
    reader = csv.reader(csvfile)

    # remove the columns name, we are going to clean the csv file anyways
    next(reader)

    cid_tmp_entries = []
    for row in reader:
        cid_dbm = {}
        cid_preffix_it = 0
        for field in row:
            if '_' in field:
                if cid_preffix_it == 2:
                    cid_dbm[field[:field.find('_')]] = int(field[field.find('_') + 1 :])
                if cid_preffix_it == 6:
                    cid_preffix_it = -1
                cid_preffix_it = cid_preffix_it + 1

        # pick up 'num_cid' strongest entries
        dbm_entries = []
        for _ in range(num_cid):
            try:
                x = max(cid_dbm.items(), key = operator.itemgetter(1))
                dbm_entries.append(x)
                del cid_dbm[x[0]]
            except ValueError:
                continue

        # skip entry if it doesn't satisfies 'num_cid'
        if skip and len(dbm_entries) != num_cid:
            continue

        # add entry
        cid_tmp_entry = row[:9]
        for dbm_entry in dbm_entries:
            cid_tmp_entry.append(str(dbm_entry[0]) + '_' + str(dbm_entry[1]))
        cid_tmp_entry.append(row[len(row) - 2])
        cid_tmp_entry.append(row[len(row) - 1])
        
        cid_tmp_entries.append(cid_tmp_entry)
    
    # build all the keys
    key_list = ['lat', 'lon', 'acc', 'bear', 'bearAcc', 'mag_x', 'mag_y', 'mag_z', 'heading']

    for row in cid_tmp_entries:
        for field in row:
            # retrieve all values that are related to cellID and build a key
            if '_' in field:
                # generate keys with the preffix 'cid_'
                cid = field[:field.find('_')]
                cid_key = cid + '_dbm'
                if cid_key not in key_list:
                    key_list.append(cid_key)
    key_list.append('timestamp')
    key_list.append('intersection_points')
    key_list.append('label')

    csv_out_file_len = len(cid_tmp_entries)
    csv_rows = []
    for row in cid_tmp_entries:
        # create dictionary keys, all 'empty' because each entry won't necessary have 
        # a value for all keys
        field_it = 0
        csv_row_entry = {k: 0 for k in key_list}
        
        ue_acc = 0
        ue_lat = 0
        ue_lon = 0
        # iterate through every field and filling up the csv row dict
        for field in row:
            if '_' in field:
                # cid related  fields
                cid = field[:field.find('_')]
                csv_row_entry[cid + '_dbm'] = 0
                csv_row_entry[cid + '_dbm'] = field[field.find('_') + 1:]
            elif field_it == len(row) - 2:
                # timestamp field
                csv_row_entry['timestamp'] = field
            elif field_it == len(row) - 1:
                # label field
                if field == "SIDEWALK":
                    csv_row_entry['label'] = 0
                elif field == "ROAD":
                    csv_row_entry['label'] = 1
                else:
                    csv_row_entry['label'] = field
            else:
                # remaining fields
                csv_row_entry[key_list[field_it]] = field
                if key_list[field_it] == 'lat':
                    ue_lat = field
                if key_list[field_it] == 'lon':
                    ue_lon = field
                if key_list[field_it] == 'acc':
                    ue_acc = field
            
            field_it = field_it + 1
        #out_json = processUELocation(ue_lat, ue_lon, ue_acc)
        csv_row_entry['intersection_points'] = 0#out_json['ue']['intersection_count']
        csv_rows.append(csv_row_entry)

    print("cleaned .csv file len:",csv_out_file_len)
    with open(str(file_out), 'w', newline='') as csv_outfile:
        dict_writer = csv.DictWriter(csv_outfile, fieldnames=key_list)
        dict_writer.writeheader()
        
        for csv_row in csv_rows:
            dict_writer.writerow(csv_row)
        csv_outfile.close()
    
    return csv_out_file_len


def pandas_cleanup(file_in, file_out, num_cid, skip):
    df = pd.read_csv(file_in)
    print(df.shape)


def create_master_clean_file(clean_train_files, clean_directory_path):
    df = pd.concat(
        [pd.read_csv(x) for x in clean_train_files], 
        ignore_index=True, 
        sort=False)
    df.fillna(0, inplace = True)

    columns = df.columns.tolist()

    non_dbm_columns = [x for x in columns if '_dbm' not in x]
    dbm_columns = [x for x in columns if '_dbm' in x] 
    
    col = non_dbm_columns[:-1] + dbm_columns + non_dbm_columns[-1:]
    df = df[col]
    df.to_csv(pathlib.Path(clean_directory_path, 'master.csv'), index=False)


def parse_train_folder():
    # iterate through the 'train' folder
    for train_dir in [x for x in pathlib.Path.cwd().iterdir() 
                      if x.is_dir() and '.' not in x.name]:
        # top level folder, indicates logging device used
        clean_combinations = itertools.product([1, 2, 3, 1000], [True, False])
        for i in clean_combinations:
            clean_train_files = []
            total_len = 0
            for train_file in [x for x in train_dir.iterdir() 
                               if not x.is_dir()]:
                clean_directory_name = str(i[0]) + 'cid_'
                clean_directory_name += 'yskip' if i[1] else 'nskip'

                clean_directory_path = pathlib.Path(
                    train_dir, clean_directory_name)
                if not clean_directory_path.exists():
                    clean_directory_path.mkdir(parents=True)
                
                clean_file_path = pathlib.Path(
                    clean_directory_path, 
                    str(train_file.parts[-1]).split('.')[0] + 
                    '_clean.csv')
                #print(train_file, clean_directory_path, clean_file_path)
            
                print("cleaning up \'" + str(train_file) + "\'...")
                #pandas_cleanup(train_file, clean_file_path, i[0], i[1])
                total_len += cleanup(train_file, clean_file_path, i[0], i[1])
                print("cleaning done \'" + str(clean_file_path) + "\'")
                clean_train_files.append(clean_file_path)
            
            create_master_clean_file(clean_train_files, clean_directory_path)
            print('total length of master file should be...', total_len)


def main():
    parse_train_folder()


if __name__ == '__main__':
    main()
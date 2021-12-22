import pandas as pd
import argparse
import logging
import os
from pathlib import Path
import shutil

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def get_args_from_command_line():
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--perimeter", type=str)
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = get_args_from_command_line()
    path_data = '/home/mtonneau/twitter/data'
    path_perimeter = os.path.join(path_data, args.perimeter, 'perimeter', 'perimeter.csv')
    path_timelines = os.path.join(path_data, args.perimeter, 'timelines')
    output_path = os.path.join(path_data, args.perimeter, 'timelines_users_left_out')
    perimeter_df = pd.read_csv(path_perimeter)
    perimeter_df['user_id'] = perimeter_df['user_id'].astype(str)
    perimeter_list = perimeter_df['user_id'].tolist()
    print(len(perimeter_list))
    print(len(list(dict.fromkeys(perimeter_list))))
    list_dir = os.listdir(path_timelines)
    not_captured_list = [user_id for user_id in perimeter_list if user_id not in list_dir]
    for user_id in not_captured_list:
        print(user_id)
    # print([user_id for user_id in perimeter_list if user_id not in os.listdir(path_timelines)])
    # for user_id in os.listdir(path_timelines):
    #     user_id = str(user_id)
    #     if user_id not in perimeter_list:
    #         shutil.move(os.path.join(path_timelines, user_id), output_path)



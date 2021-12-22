import pandas as pd
import argparse
import logging
import os
from pathlib import Path

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
    path_data = '/home/mtonneau/twitter/data'
    path_perimeter = os.path.join(path_data, args.perimeter, 'perimeter', 'perimeter.csv')
    path_timelines = os.path.join(path_data, args.perimeter, 'timelines')
    perimeter_df = pd.read_csv(path_perimeter)
    perimeter_df['user_id'] = perimeter_df['user_id'].astype(str)
    perimeter_list = perimeter_df['user_id'].tolist()
    for path in os.listdir(path_timelines):
        path = str(path)
        print(path)


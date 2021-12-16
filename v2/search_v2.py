import tweepy
from hoover.anon.utils import retrieve_keys, build_search_query_keywords, save_to_json
import argparse
import logging
import time
import os
import ast
import pandas as pd
from tenacity import retry, wait_fixed
from hoover.anon.anonymize_v1 import clean_anonymize_line_dict, anonymize, anonymize_text

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def get_args_from_command_line():
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--keys_folder_name", type=str, help="Name of the folder where keys are stored")
    parser.add_argument("--search_method", type=str,
                        help="Whether to search the full archive or the recent tweets. Two possibles values are 'full_archive' or 'recent'.")
    parser.add_argument("--lang", type=str,
                        help="Language of the tweets to be collected. If not provided, will collect tweets matching the query in all languages.")
    parser.add_argument("--keywords_path", type=str, default=None)
    parser.add_argument("--start_time", type=str,
                        help="For full archive collection, when to start the collection. Format is YYYY-MM-DD")
    parser.add_argument("--outfile", type=str, help="Path to the json file where the output will be stored")
    parser.add_argument("--anonymize", type=int, help="Whether to directly anonymize the collected data")
    parser.add_argument("--anon_db_folder_path", type=str, help="Path to anon DB.")
    args = parser.parse_args()
    return args


def extract_and_save_data_from_response(response, outfile, anonymize, anon_db_folder_path):
    """Extract data from response, save to outfile and return timestamp from the first collected tweet, if existing."""
    month_str_list = list()
    user_dict = dict()
    if response.includes and 'users' in response.includes.keys():
        for user_object in response.includes['users']:
            user_id = user_object.data['id']
            user_object.data.pop('id', None)
            user_dict[user_id] = user_object.data
    if response.data:
        for count, tweet in enumerate(response.data):
            results_dict = tweet.data
            if len(user_dict) > 0 and 'author_id' in results_dict.keys():
                results_dict = {**results_dict, **user_dict[results_dict['author_id']]}
            if 'created_at' in results_dict.keys():
                month_str_list.append(results_dict['created_at'][:7])
            if anonymize == 1:
                results_dict = anonymize_v2(response=results_dict, anon_db_folder_path=anon_db_folder_path)
            save_to_json(data_dict=results_dict, outfile=outfile)
        if len(month_str_list) > 0:
            return month_str_list[0]
        else:
            return None
    else:
        return None


def get_timestamp_last_collected_tweet(outfile):
    """Retrieve and return earliest date from the 10 last collected tweets."""
    timestamp_list = list()
    tweet_id_list = list()
    with open(outfile) as file:
        for count, line in enumerate((file.readlines()[-10:])):
            line_dict = ast.literal_eval(line)
            tweet_id_list.append(line_dict['id'])
            if 'created_at' in line_dict.keys():
                timestamp_list.append(pd.to_datetime(line_dict['created_at']))
            else:
                timestamp_list.append(pd.Timestamp.now(tz='UTC'))
    val, idx = min((val, idx) for (idx, val) in enumerate(timestamp_list))
    end_time = f'{val.isoformat()[:-6]}.000Z'
    logger.info(f'Starting back from {end_time}')
    return end_time

@retry(wait=wait_fixed(60))
def get_search_response(client, **search_arguments_dict):
    """Try to get a response from the API. If an exception is raised, wait for 10 seconds and retry."""
    try:
        response = client.search_all_tweets(**search_arguments_dict)
        return response
    except Exception as e:
        logger.info(f'Exception {e} raised. Waiting for 10 seconds')
        raise e

def log_month_string_if_new(month_str, old_month_str):
    """Log the month from which the tweets last collected are from, if different from the month from the last API response."""
    if month_str:
        if month_str != old_month_str:
            logger.info(f'Collecting data from {month_str}')
        return month_str
    else:
        return old_month_str

def anonymize_v2(response, anon_db_folder_path):
    output_dict = dict()
    for key in response.keys():
        if key == 'text':
            output_dict['text'] = anonymize_text(text=response['text'], anon_db_folder_path=anon_db_folder_path)
        elif key == 'id':
            output_dict['id'] = anonymize(data_dict=response, dict_key=key,
                                                                  object_type='tweet', anon_db_folder_path=anon_db_folder_path)
        elif key == 'author_id':
            output_dict['user_id'] = anonymize(data_dict=response, dict_key=key,
                                                                  object_type='user', anon_db_folder_path=anon_db_folder_path)
        elif key == 'in_reply_to_user_id':
            if len(response[key]) > 0:
                output_dict[key] = anonymize(data_dict=response, dict_key=key,
                                                                      object_type='tweet', anon_db_folder_path=anon_db_folder_path)
            else:
                output_dict[key] = ''
        elif key == 'username':
            output_dict['screen_name'] = anonymize(data_dict=response, dict_key=key,
                                                               object_type='user',
                                                               anon_db_folder_path=anon_db_folder_path)
        elif key == 'description':
            if len(response[key]) > 0:
                output_dict[key] = anonymize_text(text=response[key], anon_db_folder_path=anon_db_folder_path)
            else:
                output_dict[key] = ''
        elif key == 'url':
            if len(response['url']) > 0:
                output_dict[key] = anonymize(data_dict=response, dict_key=key,
                                                                   object_type='user',
                                                                   anon_db_folder_path=anon_db_folder_path)
            else:
                output_dict[key] = ''
        elif key == 'entities':
            output_dict[key] = dict()
            anonymized_mentions_list = list()
            for mention_dict in response[key]['mentions']:
                mention_dict['username'] = anonymize(data_dict=mention_dict, dict_key='username',
                                                               object_type='user',
                                                               anon_db_folder_path=anon_db_folder_path)
                mention_dict['id'] = anonymize(data_dict=mention_dict, dict_key='id',
                                                               object_type='user',
                                                               anon_db_folder_path=anon_db_folder_path)
                anonymized_mentions_list.append(mention_dict)
            output_dict[key]['mentions'] = anonymized_mentions_list
        elif key == 'referenced_tweets':
            referenced_tweets_list = response[key]
            anonymized_referenced_tweets_list = list()
            for count, referenced_tweet_dict in enumerate(referenced_tweets_list):
                referenced_tweet_dict['id'] = anonymize(data_dict=referenced_tweet_dict, dict_key='id',
                                                               object_type='tweet',
                                                               anon_db_folder_path=anon_db_folder_path)
                anonymized_referenced_tweets_list.append(referenced_tweet_dict)
            output_dict[key] = anonymized_referenced_tweets_list
        else:
            if not key == 'name':
                output_dict[key] = response[key]
    return output_dict



def main():
    args = get_args_from_command_line()
    consumer_key, consumer_secret, bearer_token = retrieve_keys(keys_folder_name=args.keys_folder_name)
    client = tweepy.Client(consumer_key=consumer_key,
                           consumer_secret=consumer_secret,
                           bearer_token=bearer_token,
                           wait_on_rate_limit=True)
    query = build_search_query_keywords(keywords_path=args.keywords_path, lang=args.lang)
    logger.info(f'Search query: {query}')
    search_arguments_dict = {'query': query,
                             'expansions': ['author_id', 'in_reply_to_user_id',
                                            'entities.mentions.username',
                                            'referenced_tweets.id', ],
                             'tweet_fields': ['created_at'],
                             'user_fields': ['username', 'public_metrics', 'location', 'url', 'description']}
    if os.path.exists(args.outfile):
        logger.info('Output file already exists')
        search_arguments_dict['end_time'] = get_timestamp_last_collected_tweet(outfile=args.outfile)
    if args.search_method == 'full_archive':
        start_time = f'{args.start_time}T00:00:00.000Z'
        search_arguments_dict['start_time'] = start_time
        old_month_str = None
        response = get_search_response(client, **search_arguments_dict)

        month_str = extract_and_save_data_from_response(response=response, outfile=args.outfile, anonymize=args.anonymize, anon_db_folder_path=args.anon_db_folder_path)
        old_month_str = log_month_string_if_new(month_str=month_str, old_month_str=old_month_str)
        while 'next_token' in response.meta.keys():
            search_arguments_dict['next_token'] = response.meta['next_token']
            response = get_search_response(client, **search_arguments_dict)
            month_str = extract_and_save_data_from_response(response=response, outfile=args.outfile, anonymize=args.anonymize, anon_db_folder_path=args.anon_db_folder_path)
            old_month_str = log_month_string_if_new(month_str=month_str, old_month_str=old_month_str)
            time.sleep(1)  # Full-archive has a 1 request / 1 second limit
    elif args.search_method == 'recent':
        for response in tweepy.Paginator(client.search_recent_tweets,
                                         **search_arguments_dict):
            extract_and_save_data_from_response(response=response, outfile=args.outfile, anonymize=args.anonymize, anon_db_folder_path=args.anon_db_folder_path)


if __name__ == '__main__':
    main()

# Initial approach below was returning tweepy.errors.TwitterServerError: 503 Service Unavailable
# meaning "The Twitter servers are up, but overloaded with requests. Try again later."

# if args.search_method == 'full_archive':
#     start_time = f'{args.start_time}T00:00:00.000Z'
#     search_arguments_dict['start_time'] = start_time
#     old_month_str = None
#     for response in tweepy.Paginator(client.search_all_tweets,
#                                      **search_arguments_dict):
#         month_str = extract_and_save_data_from_response(response=response, outfile=args.outfile)
#         if month_str:
#             if month_str != old_month_str:
#                 logger.info(f'Collecting data from {month_str}')
#             old_month_str = month_str
#         time.sleep(1)  # Full-archive has a 1 request / 1 second limit
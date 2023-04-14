# Import required modules
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pymongo import MongoClient
import psycopg2
from datetime import datetime

# Initialize the app
app = FastAPI()

# Connect to PostgreSQL
pg_conn = psycopg2.connect(
    host="localhost",
    database="twitter_db",
    user="postgres",
    password="password"
)

# Connect to MongoDB
mongo_conn = MongoClient('mongodb://localhost:27017/')
mongo_db = mongo_conn['twitter_db']

# Define pagination parameters
PAGE_SIZE = 10

# Define cache dictionary
cache = {}

# Define function to get user information
def get_user_info(user_id):
    with pg_conn.cursor() as cur:
        cur.execute("SELECT * FROM users_df WHERE id = %s", (user_id,))
        user_info = cur.fetchone()
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        user = {
            'id': user_info[0],
            'name': user_info[1],
            'screen_name': user_info[2],
            'location': user_info[3],
            'created_at': user_info[4],
            'followers_count': user_info[5],
            'friends_count': user_info[6],
            'statuses_count': user_info[7],
            'favorites_count': user_info[8]
        }
        return user

# Define function to search tweets
def search_tweets(query_params):
    # Check if query has been cached
    if query_params in cache:
        return cache[query_params]
    
    # Otherwise, search the database and cache the result
    tweets = []
    with mongo_conn.start_session() as session:
        with session.start_transaction():
            tweets_collection = mongo_db['tweets_collection']
            results = tweets_collection.find(query_params).sort('created_at', -1)
            for result in results:
                tweet = {
                    'id': result['_id'],
                    'text': result['text'],
                    'user_id': result['user_id'],
                    'created_at': result['created_at']
                }
                if 'retweet_id' in result:
                    tweet['retweet_id'] = result['retweet_id']
                if 'comment_id' in result:
                    tweet['comment_id'] = result['comment_id']
                tweets.append(tweet)
                
    # Cache the result
    cache[query_params] = tweets
    
    return tweets

# Define function to get retweets
def get_retweets(tweet_id):
    with mongo_conn.start_session() as session:
        with session.start_transaction():
            tweets_collection = mongo_db['tweets_collection']
            retweets = tweets_collection.find({'retweet_id': tweet_id}).sort('created_at', -1)
            retweets_list = []
            for retweet in retweets:
                retweets_list.append({
                    'id': retweet['_id'],
                    'text': retweet['text'],
                    'user_id': retweet['user_id'],
                    'created_at': retweet['created_at']
                })
            return retweets_list

# Define function to get comments
def get_comments(tweet_id):
    with mongo_conn.start_session() as session:
        with session.start_transaction():
            tweets_collection = mongo_db['tweets_collection']
            comments = tweets_collection.find({'comment_id': tweet_id}).sort('created_at', -1)
            comments_list = []
            for comment in comments:
                comments_list.append({
                    'id': comment['_id'],
                    'text': comment['text'],
                    'user_id': comment['user_id'],
                    'created_at': comment['created_at'].strftime("%Y-%m-%d %H:%M:%S")
                })
            return comments_list


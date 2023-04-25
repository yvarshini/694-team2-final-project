# importing required libraries
import psycopg2
from pymongo import MongoClient
from fastapi import HTTPException
from exceptions.exceptions import *
import requests
from utils.cacheClass import LRUCache
import getpass
import time
from logger.logger import logger

lrucache = LRUCache(100)

# connecting to the PostgreSQL database
try:
    p_conn = psycopg2.connect(
        dbname = "twitter",
        user = getpass.getuser(),
        password = "",
        host = "localhost",
        port = "5432"
    )
except psycopg2.OperationalError as e:
    # raise an error if the connection is unsuccessful
    print(f"Unable to connect to PostgreSQL: {e}")

# opening a cursor to perform database operations
p_cur = p_conn.cursor()

# print the PostgreSQL server information
print(p_conn.get_dsn_parameters(), "\n")

# connect to the MongoDB database
mongo_conn = MongoClient("mongodb+srv://vm574:twitter574@cluster0.nwilsw2.mongodb.net/?retryWrites=true&w=majority")
mongo_db = mongo_conn['final_db']
tweets_collection = mongo_db['tweets']

# creating index
tweets_collection.create_index([("text", "text")])

# function to get user information
def get_user_info(localusername, username):
    """
        This function returns the user information as a JSON object.
        Input:
            username (str): Twitter user ID which we want to look up
        Output:
            user_out (JSON object): user information corresponding to username
    """
    username = str(username)

    # check if the user information is in the cache
    user_out = lrucache.get(username)
    if user_out is not None:
        logger.info("get_user_info - query in cache")
        return user_out
    
    p_conn = psycopg2.connect(
        dbname = "twitter",
        user = localusername,
        password = "",
        host = "localhost",
        port = "5432"
    )
    p_cur = p_conn.cursor()
    
    p_cur.execute("SELECT * FROM TwitterUser WHERE screen_name = '{0}';".format(username))
    user_info = p_cur.fetchone()
    if user_info is None:
        # raise an exception if the user doesn't exist in the database
        raise HTTPException(status_code = UserNotFoundError.code, detail = UserNotFoundError.description)
    user_out = {
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
    lrucache.put(username, user_out)
    logger.info("get_user_info-" + str(username) + "-" + str(lrucache.display_cache()))
    
    p_cur.close()

    return user_out

# function to retreive tweets containing a specified keyword
def retrieve_tweets_keyword(limit, keyword: str, sort_criterion = 'popularity'):
    """
        Function to get the information of tweets based on a user-specified keyword.
        Input:
            keyword (str): user-specified keyword
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            out (list): list of tweets containing the keyword
    """
    # check if the tweet information is in the cache
    search_by_keyword = lrucache.get(limit + str + sort_criterion)
    if search_by_keyword is not None:
        logger.info("retrieve_tweets_keyword - query in cache")
        return search_by_keyword
    # check if sort_criterion is valid, if specified:
    if sort_criterion is not None:
        if sort_criterion not in ['oldestToNewest', 'newestToOldest', 'popularity']:
            raise HTTPException(status_code = InvalidSortCriterionError.code, detail = InvalidSortCriterionError.description)

    out = []
    query = {'$text': {'$search': keyword}}
    limit = int(limit)
    tweets_match = tweets_collection.find(query).limit(limit) # we can add .limit(PAGE_LIMIT) here, if needed
    for result in tweets_match:
        tweet = {
            'id': result['_id'],
            'text': result['text'],
            'user_id': result['user_id'],
            'quote_count': result['quote_count'],
            'reply_count': result['reply_count'],
            'retweet_count': result['retweet_count'],
            'favorite_count': result['favorite_count'],
            'created_at': result['timestamp'],
            'coordinates': result['coordinates']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        else:
            tweet['retweet'] = "No"

        
        out.append(tweet)

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        out = sorted(out, key = lambda x: time.strptime(x['created_at'], '%a %b %d %H:%M:%S %Y'), reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        out = sorted(out, key = lambda x: time.strptime(x['created_at'], '%a %b %d %H:%M:%S %Y'), reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        out = sorted(out, key = lambda x: int(x['favorite_count']), reverse = True)

    lrucache.put(str(limit) + str + sort_criterion, out)  
    logger.info("retrieve_tweets_keyword-" + str(keyword) + "-" + str(lrucache.display_cache()))  
    return out

# function to search tweets based on tweet id
def retrieve_tweet(tweet_id):
    """
        Function to get the information of a tweet based on a user-specified tweet ID.
        Input:
            tweet_id: user-specified tweet ID
        Output:
            tweet (JSON object): tweet corresponding to tweet_id
    """
    tweet_id = int(tweet_id)

    # check if the tweet information is in the cache
    search_by_tweetid = lrucache.get(tweet_id)
    if search_by_tweetid is not None:
        logger.info("retrieve_tweet - query in cache")
        return search_by_tweetid

    query = {'_id': tweet_id}
    result = tweets_collection.find_one(query)
    if result == {}:
        # raise an exception if the tweet doesn't exist in the database
        raise HTTPException(status_code = TweetNotFoundError.code, detail = TweetNotFoundError.description)
    tweet = {
        'id': result['_id'],
        'text': result['text'],
        'user_id': result['user_id'],
        'quote_count': result['quote_count'],
        'reply_count': result['reply_count'],
        'retweet_count': result['retweet_count'],
        'favorite_count': result['favorite_count'],
        'created_at': result['timestamp'],
        'coordinates': result['coordinates']
    }
    # add information on whether the tweet is a retweet
    if 'retweet' in result:
        tweet['retweet'] = "Yes"
    else:
        tweet['retweet'] = "No"

    lrucache.put(str(tweet_id), tweet)
    logger.info("retrieve_tweet-" + str(tweet_id) + "-" + str(lrucache.display_cache()))  
    return tweet

# function to retrieve all tweets by a user
def retrieve_tweets_user(limit, localusername, username = None, user_id = None, sort_criterion = 'popularity'):
    """
        Function to retrieve all tweets by a specific user (user-specified username)
        Input:
            username (str): user-specified username
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            tweets_list (list): list of tweets made by a user
    """
    # check if the user information is in the cache
    if username is not None:
        search_by_user = lrucache.get(limit + username + sort_criterion + "usertweets")
    elif user_id is not None:
        search_by_user = lrucache.get(limit + user_id + sort_criterion + "usertweets")
    if search_by_user is not None:
        logger.info("retrieve_tweets_user - query in cache")
        return search_by_user

    p_conn = psycopg2.connect(
        dbname = "twitter",
        user = localusername,
        password = "",
        host = "localhost",
        port = "5432"
    )
    p_cur = p_conn.cursor()
    
    if username is not None:
        # check if the username is valid
        p_cur.execute("SELECT * FROM TwitterUser WHERE screen_name = '{0}';".format(username))
        username_db = p_cur.fetchone()
        if username_db is None:
            # raise an exception if the user doesn't exist in the database
            raise HTTPException(status_code = UserNotFoundError.code, detail = UserNotFoundError.description)
        user_id = username_db[0]
        
        p_cur.close()

    else:
        # check if the user_id is valid
        p_cur.execute("SELECT * FROM TwitterUser WHERE id = '{0}';".format(int(user_id)))
        username_db = p_cur.fetchone()
        if username_db is None:
            # raise an exception if the user doesn't exist in the database
            raise HTTPException(status_code = UserNotFoundError.code, detail = UserNotFoundError.description)
    
        p_cur.close()

    # if the user exists, proceed to search MongoDB
    user_id = int(user_id) # convert user_id to int
    query = {'user_id': user_id}
    limit = int(limit)
    tweets_match = tweets_collection.find(query).limit(limit)
    
    if tweets_match == {}:
        return "This user has not tweeted anything yet."

    tweets_list = []
    for result in tweets_match:
        tweet = {
            'id': result['_id'],
            'text': result['text'],
            'user_id': result['user_id'],
            'quote_count': result['quote_count'],
            'reply_count': result['reply_count'],
            'retweet_count': result['retweet_count'],
            'favorite_count': result['favorite_count'],
            'created_at': result['timestamp'],
            'coordinates': result['coordinates']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        else:
            tweet['retweet'] = "No"

        tweets_list.append(tweet)

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        tweets_list = sorted(tweets_list, key = lambda x: time.strptime(x['created_at'], '%a %b %d %H:%M:%S %Y'), reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        tweets_list = sorted(tweets_list, key = lambda x: time.strptime(x['created_at'], '%a %b %d %H:%M:%S %Y'), reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        tweets_list = sorted(tweets_list, key = lambda x: int(x['favorite_count']), reverse = True)

    if username is not None:
        lrucache.put(str(limit) + username + sort_criterion + "usertweets", tweets_list)
        logger.info("retrieve_tweets_user-" + str(username) + "-" + str(lrucache.display_cache()))  
    elif user_id is not None:
        lrucache.put(str(limit) + str(user_id) + sort_criterion + "usertweets", tweets_list)
        logger.info("retrieve_tweets_user-" + str(user_id) + "-" + str(lrucache.display_cache()))  
        
    return tweets_list

# function to retreive the screen name from the user_id
def retreive_screen_name(localusername, user_id):
    """
        Function to retrieve tweets near a specified location.
        Input:
            user_id: user-specified user ID
        Output:
            username (str): username corresponding to the specified user_id
    """
    # check if the user information is in the cache
    search_by_user_id = lrucache.get(user_id)
    if search_by_user_id is not None:
        logger.info("retreive_screen_name - query in cache")
        return search_by_user_id

    p_conn = psycopg2.connect(
        dbname = "twitter",
        user = localusername,
        password = "",
        host = "localhost",
        port = "5432"
    )
    p_cur = p_conn.cursor()
    
    # check if the user id is valid
    p_cur.execute("SELECT screen_name FROM TwitterUser WHERE id = '{0}';".format(user_id))
    username_db = p_cur.fetchone()
    if username_db is None:
        # raise an exception if the user doesn't exist in the database
        raise HTTPException(status_code = UserNotFoundError.code, detail = UserNotFoundError.description)
    username = username_db[0]
    
    p_cur.close()
    lrucache.put(str(user_id), username)
    logger.info("retreive_screen_name-" + str(user_id) + "-" + str(lrucache.display_cache())) 
    return username

# function to retrieve tweets based on location
def retrieve_tweets_location(limit, location: str, distance = 100000, sort_criterion = 'popularity'):
    """
        Function to retrieve tweets near a specified location.
        Input:
            location (str): user-specified location
            distance (int): radius of the search (100 kilometers, by default)
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            tweets_list (list): list of tweets made from within the radius of the specified location
    """
    # # check if the location tweet information is in the cache
    search_by_location = lrucache.get(limit + location + distance + sort_criterion)
    if search_by_location is not None:
        logger.info("retrieve_tweets_location - query in cache")
        return search_by_location

    # getting the latitude and longitude of the location specified
    endpoint = "https://nominatim.openstreetmap.org/search"
    params = {"q": location, "format": "json", "limit": 1}
    # sending a request of the Nominatim API
    response = requests.get(endpoint, params=params)
    result = response.json()[0]
    # getting the latitude and longitude from the response of the API
    latitude = float(result["lat"])
    longitude = float(result["lon"])

    # creating a geospatial index on the coordinates field
    tweets_collection.create_index([("coordinates", "2dsphere")])
    distance = int(distance)
    query = {"coordinates": {"$near": {"$geometry": {"type": "Point", "coordinates": [longitude, latitude]}, "$maxDistance": distance}}}
    limit = int(limit)
    tweets_match = tweets_collection.find(query).limit(limit)
    
    if tweets_match == {}:
        return "There are no tweets near this location yet."

    tweets_list = []
    for result in tweets_match:
        tweet = {
            'id': result['_id'],
            'text': result['text'],
            'user_id': result['user_id'],
            'quote_count': result['quote_count'],
            'reply_count': result['reply_count'],
            'retweet_count': result['retweet_count'],
            'favorite_count': result['favorite_count'],
            'created_at': result['timestamp'],
            'coordinates': result['coordinates']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        else:
            tweet['retweet'] = "No"

        tweets_list.append(tweet)

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        tweets_list = sorted(tweets_list, key = lambda x: time.strptime(x['created_at'], '%a %b %d %H:%M:%S %Y'), reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        tweets_list = sorted(tweets_list, key = lambda x: time.strptime(x['created_at'], '%a %b %d %H:%M:%S %Y'), reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        tweets_list = sorted(tweets_list, key = lambda x: int(x['favorite_count']), reverse = True)

    lrucache.put(str(limit) + location + distance + sort_criterion, tweets_list) 
    logger.info("retrieve_tweets_location-" + str(location) +  "-" + str(lrucache.display_cache()))  
    return tweets_list

# function to retrieve tweets with matching hastags
def retrieve_tweets_hashtags(limit, hashtag, sort_criterion = 'popularity'):
    """
        Function to retrieve tweets containing one or more user-specified hashtags.
        Input:
            hashtag (str): user-specified hashtag(s). If multiple, they must be separated by spaces.
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            out (list): list of tweets containing the hashtag(s)
    """
    hashtags = hashtag.split()

    # # check if the tweet information is in the cache
    search_by_hashtag = lrucache.get(limit + hashtag + sort_criterion)
    if search_by_hashtag is not None:
        logger.info("retrieve_tweets_hashtags - query in cache")
        return search_by_hashtag

    out = []
    query = {"hashtags": {"$in": hashtags}}
    limit = int(limit)
    tweets_match = tweets_collection.find(query).limit(limit)
    for result in tweets_match:
        tweet = {
            'id': result['_id'],
            'text': result['text'],
            'user_id': result['user_id'],
            'quote_count': result['quote_count'],
            'reply_count': result['reply_count'],
            'retweet_count': result['retweet_count'],
            'favorite_count': result['favorite_count'],
            'created_at': result['timestamp'],
            'coordinates': result['coordinates']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        else:
            tweet['retweet'] = "No"

        
        out.append(tweet)

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        out = sorted(out, key = lambda x: time.strptime(x['created_at'], '%a %b %d %H:%M:%S %Y'), reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        out = sorted(out, key = lambda x: time.strptime(x['created_at'], '%a %b %d %H:%M:%S %Y'), reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        out = sorted(out, key = lambda x: int(x['favorite_count']), reverse = True)

    lrucache.put(str(limit) + hashtag + sort_criterion, out) 
    logger.info("retrieve_tweets_hashtags-" + str(hashtag) + "-" + str(lrucache.display_cache()))     
    return out

# function to get the top 10 most followed users
def top_10_users(localusername):

    # check if the top username information is in the cache
    search_by_localuser = lrucache.get(top_10_users)
    if search_by_localuser is not None:
        logger.info("top_10_users found in cache")
        return search_by_localuser

    # connect to the users database
    p_conn = psycopg2.connect(
        dbname = "twitter",
        user = localusername,
        password = "",
        host = "localhost",
        port = "5432"
    )
    p_cur = p_conn.cursor()

    # select the top 10 most-followed users
    p_cur.execute("SELECT * FROM TwitterUser ORDER BY followers_count DESC LIMIT 10;")
    users_list = p_cur.fetchall()
    
    user_info_list = []
    for user_info in users_list:
        user_out = {
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
        user_info_list.append(user_out)

    lrucache.put("top_10_users", user_info_list)  
    logger.info("top_10_users-" + str(lrucache.display_cache()))  
    return user_info_list

# function to get the trending tweets (most favorited, replied to and retweeted)
def trendingTweets():
        
    # check if the Trending tweet information is in the cache
    retrieve_trending_Tweet = lrucache.get("TrendingTweet")
    if retrieve_trending_Tweet is not None:
        logger.info("Trending tweets in cache")
        return retrieve_trending_Tweet
    
    pipeline = [
        {"$project": {
            "_id": 1,
            "text": 1,
            "user_id": 1,
            "quote_count": 1,
            "reply_count": 1,
            "retweet_count": 1,
            "favorite_count": 1,
            "timestamp": 1,
            "coordinates": 1,
            "retweet": {"$ifNull": ["$retweeted_status", False]},
            "sum": {"$sum": ["$favorite_count", "$retweet_count", "$reply_count"]}
        }},
        {"$sort": {"sum": -1}},
        {"$limit": 10}
    ]

    tweets_match = tweets_collection.aggregate(pipeline)

    tweets_list = []
    for result in tweets_match:
        tweet = {
            'id': result['_id'],
            'text': result['text'],
            'user_id': result['user_id'],
            'quote_count': result['quote_count'],
            'reply_count': result['reply_count'],
            'retweet_count': result['retweet_count'],
            'favorite_count': result['favorite_count'],
            'created_at': result['timestamp'],
            'coordinates': result['coordinates']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        else:
            tweet['retweet'] = "No"

        tweets_list.append(tweet)
    lrucache.put("TrendingTweet", tweets_list) 
    logger.info("trendingTweets-" + str(lrucache.display_cache()))  
    return tweets_list

# main search function
def search(username_for_user_info = None, user_id_for_tweets = None, username_tweets = None, user_id = None, tweet_id = None, keyword = None, hashtags = None, location = None, sort_criterion = 'popularity', distance = 100000, top10users = "no", trendingTweets = "no", limit = 10):
    params = [username_for_user_info, user_id_for_tweets, username_tweets, user_id, tweet_id, keyword, hashtags, location]

    # raise exception if no search parameters are specified
    if all(x is None for x in params):
        raise HTTPException(status_code = NoParametersGivenError.code, detail = NoParametersGivenError.description)
    # raise exception if too many search parameters are specified
    if params.count(None) < len(params) - 1:
        raise HTTPException(status_code = TooManyParametersGivenError.code, detail = TooManyParametersGivenError.description)
    
    # find the localusername
    localusername = getpass.getuser()

    if username_for_user_info is not None:
        return get_user_info(localusername, username_for_user_info)
    elif username_tweets is not None or user_id_for_tweets is not None:
        return retrieve_tweets_user(limit, localusername, username_tweets, user_id_for_tweets, sort_criterion)
    elif user_id is not None:
        return retreive_screen_name(localusername, user_id)
    elif tweet_id is not None:
        return retrieve_tweet(tweet_id)
    elif keyword is not None:
        return retrieve_tweets_keyword(limit, keyword, sort_criterion)
    elif hashtags is not None:
        return retrieve_tweets_hashtags(limit, hashtags, sort_criterion)
    elif location is not None:
        return retrieve_tweets_location(limit, location, distance, sort_criterion)
    elif top10users != "no":
        return top_10_users(localusername)
    else:
        return trendingTweets()
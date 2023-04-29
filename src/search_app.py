# importing required libraries
import psycopg2
from pymongo import MongoClient
from fastapi import HTTPException
from exceptions.exceptions import *
import requests
from utils.cacheClass import LRUCache
import getpass
from logger.logger import logger
from datetime import datetime, timedelta

lrucache = LRUCache(100, "cache.json")

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
mongo_db = mongo_conn['not_another_db']
tweets_collection = mongo_db['tweets']

# creating index
tweets_collection.create_index([("text", "text")])

# function to get user information
def get_user_info(localusername, username):
    """
        This function returns the user information as a JSON object.
        Input:
            localusername (str): automatically retrieved by Python; the local system's username.
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
    
    # connect to the PostgresSQL database
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
    # add the new search and result to the cache
    lrucache.put(username, user_out)
    logger.info("get_user_info-" + str(username) + "-" + str(lrucache.display_cache()))
    # close the cursor object
    p_cur.close()

    return user_out

# function to retreive tweets containing a specified keyword
def retrieve_tweets_keyword(limit, keyword: str, sort_criterion = 'popularity'):
    """
        Function to get the information of tweets based on a user-specified keyword.
        Input:
            limit (int): maximum number of results to be displayed
            keyword (str): user-specified keyword
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            out (list): list of tweets containing the keyword
    """
    # check if the tweet information is in the cache
    search_by_keyword = lrucache.get(limit + keyword + sort_criterion)
    if search_by_keyword is not None:
        logger.info("retrieve_tweets_keyword - query in cache")
        return search_by_keyword
    
    # check if sort_criterion is valid, if specified
    if sort_criterion is not None:
        if sort_criterion not in ['oldestToNewest', 'newestToOldest', 'popularity']:
            raise HTTPException(status_code = InvalidSortCriterionError.code, detail = InvalidSortCriterionError.description)

    out = []
    query = {'$text': {'$search': keyword}}
    limit = int(limit) # convert string limit to integer
    tweets_match = tweets_collection.find(query).limit(limit) # we can add .limit(PAGE_LIMIT) here, if needed
    for result in tweets_match:
        tweet = {
            'id_string': str(result['_id']),
            'text': result['text'],
            'user_id': result['user_id'],
            'tweet_pop': result['tweet_pop'],
            'created_at': result['timestamp']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        # add information about coordinates if the key exists
        if 'coordinates' in result:
            tweet['coordinates']: result['coordinates']
        
        out.append(tweet)

    # return a message if there are no matches
    if len(out) == 0:
        return "There are no tweets with this keyword."

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        out = sorted(out, key = lambda x: x['created_at'], reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        out = sorted(out, key = lambda x: x['created_at'], reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        out = sorted(out, key = lambda x: int(x['tweet_pop']), reverse = True)

    # add the search and result to the cache
    lrucache.put(str(limit) + keyword + sort_criterion, out)  
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
    # convert string to integer in order to query the database
    tweet_id = int(tweet_id)

    # check if the tweet information is in the cache
    search_by_tweetid = lrucache.get(str(tweet_id) + 'tweetsearchbytweetid')
    if search_by_tweetid is not None:
        logger.info("retrieve_tweet - query in cache")
        return search_by_tweetid

    query = {'_id': tweet_id}
    result = tweets_collection.find_one(query)
    if result == None:
        # raise an exception if the tweet doesn't exist in the database
        raise HTTPException(status_code = TweetNotFoundError.code, detail = TweetNotFoundError.description)
    
    tweet = {
        'id': str(result['_id']),
        'text': result['text'],
        'user_id': result['user_id'],
        'tweet_pop': result['tweet_pop'],
        'created_at': result['timestamp']
    }
    # add information on whether the tweet is a retweet
    if 'retweet' in result:
        tweet['retweet'] = "Yes"
    # add information about coordinates if the key exists
        if 'coordinates' in result:
            tweet['coordinates']: result['coordinates']

    # add the search and result to cache
    lrucache.put(str(tweet_id) + 'tweetsearchbytweetid', tweet)
    logger.info("retrieve_tweet-" + str(tweet_id) + "-" + str(lrucache.display_cache()))  

    return tweet

# function to retreieve tweets in a time range
def retrieve_tweets_time_range(limit, time_range: str, sort_criterion = 'popularity'):
    """
        Function to retrieve all tweets from a time window, counted from the current time
        Input:
            limit (int): maximum number of results to be displayed
            time_range (str): Can be '1 week', '1 month', '3 months', '6 months', '1 year', '5 years' or 'all time'
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            tweets_list (list): list of tweets made during the given time duration
    """

    # check if the tweet information is in the cache
    search_by_time = lrucache.get(time_range + 'timedsearch')
    if search_by_time is not None:
        logger.info("retrieve_tweets_time_range - query in cache")
        return search_by_time

    # get the current date
    current_date = datetime.utcnow()

    # the starting date is defined to be x days behind the current date
    # x = 7 for 1 week, 30 for 1 month, etc.
    if time_range == '1 week':
        start_date = current_date - timedelta(days=7)
    elif time_range == '1 month':
        start_date = current_date - timedelta(days=30)
    elif time_range == '3 months':
        start_date = current_date - timedelta(days=90)
    elif time_range == '6 months':
        start_date = current_date - timedelta(days=180)
    elif time_range == '1 year':
        start_date = current_date - timedelta(days=365)
    elif time_range == '5 years':
        start_date = current_date - timedelta(days=1825)
    elif time_range == 'all time':
        start_date = datetime(1900, 1, 1)
    else:
        # raise exception if an invalid time window is provided
        raise HTTPException(status_code = InvalidTimeWindowError.code, detail = InvalidTimeWindowError.description)

    # convert the date strings to timestamp objects
    start_date_unix = start_date.timestamp()
    current_date_unix = current_date.timestamp()

    # query for tweets with timestamp greater than or equal to the start date and less than the current date
    query = {'timestamp': {'$gte': start_date_unix, '$lt': current_date_unix}}
    limit = int(limit) # convert string limit to integer
    tweets_match = tweets_collection.find(query).limit(limit)

    tweets_list = []
    for result in tweets_match:
        tweet = {
            'id': str(result['_id']),
            'text': result['text'],
            'user_id': result['user_id'],
            'tweet_pop': result['tweet_pop'],
            'created_at': result['timestamp']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        # add information about coordinates if the key exists
        if 'coordinates' in result:
            tweet['coordinates']: result['coordinates']
        
        tweets_list.append(tweet)

    # return a custom message to the user if there are no matches
    if len(tweets_list) == 0:
        return "There are no tweets made in this time range."

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        tweets_list = sorted(tweets_list, key = lambda x: x['created_at'], reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        tweets_list = sorted(tweets_list, key = lambda x: x['created_at'], reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        tweets_list = sorted(tweets_list, key = lambda x: int(x['tweet_pop']), reverse = True) 

    # add the search and result to cache
    lrucache.put(time_range + 'timedsearch', tweets_list)
    logger.info("retrieve_tweets_time_range-" + time_range + "-" + str(lrucache.display_cache())) 

    return tweets_list

# function to retrieve all tweets by a user
def retrieve_tweets_user(limit, localusername, username = None, user_id = None, sort_criterion = 'popularity'):
    """
        Function to retrieve all tweets by a specific user (user-specified username)
        Input:
            limit (int): maximum number of results to be displayed
            localusername (str): automatically retrieved by Python; the local system's username
            username (str): user-specified username
            user_id (int): user-specified user_id
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            tweets_list (list): list of tweets made by a user
    """
    # check if the user information is in the cache
    if username is not None: # if username is specified
        search_by_user = lrucache.get(limit + username + sort_criterion + "usertweets")
    elif user_id is not None: # if user_id is specified
        search_by_user = lrucache.get(limit + user_id + sort_criterion + "usertweets")
    if search_by_user is not None:
        logger.info("retrieve_tweets_user - query in cache")
        return search_by_user

    # connect to the PostgresSQL database
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
        # get the user_id corresponding to the username
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
    user_id = int(user_id) # convert string user_id to integer
    query = {'user_id': user_id}
    limit = int(limit) # convert string limit to integer
    tweets_match = tweets_collection.find(query).limit(limit)

    tweets_list = []
    for result in tweets_match:
        tweet = {
            'id': str(result['_id']),
            'text': result['text'],
            'user_id': result['user_id'],
            'tweet_pop': result['tweet_pop'],
            'created_at': result['timestamp']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        # add information about coordinates if the key exists
        if 'coordinates' in result:
            tweet['coordinates']: result['coordinates']

        tweets_list.append(tweet)

    # return custom message to the user if there are no matches
    if len(tweets_list) == 0:
        return "This user has not tweeted anything yet."

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        tweets_list = sorted(tweets_list, key = lambda x: x['created_at'], reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        tweets_list = sorted(tweets_list, key = lambda x: x['created_at'], reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        tweets_list = sorted(tweets_list, key = lambda x: int(x['tweet_pop']), reverse = True)

    # add the search and result to cache
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
            localusername (str): automatically retrieved by Python; the local system's username
            user_id (int): user-specified user ID
        Output:
            username (str): username corresponding to the specified user_id
    """
    # check if the user information is in the cache
    search_by_user_id = lrucache.get(user_id)
    if search_by_user_id is not None:
        logger.info("retreive_screen_name - query in cache")
        return search_by_user_id

    # connect to the PostgreSQL database
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

    # put the search and result into cache
    lrucache.put(str(user_id), username)
    logger.info("retreive_screen_name-" + str(user_id) + "-" + str(lrucache.display_cache())) 

    return username

# function to retrieve tweets based on location
def retrieve_tweets_location(limit, location: str, distance = 100000, sort_criterion = 'popularity'):
    """
        Function to retrieve tweets near a specified location.
        Input:
            limit (int): maximum number of results to be displayed
            location (str): user-specified location
            distance (int): radius of the search (100 kilometers, by default)
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            tweets_list (list): list of tweets made from within the radius of the specified location
    """
    # check if the location tweet information is in the cache
    search_by_location = lrucache.get(str(limit) + location + str(distance) + sort_criterion)
    if search_by_location is not None:
        logger.info("retrieve_tweets_location - query in cache")
        return search_by_location

    # getting the latitude and longitude of the location specified
    endpoint = "https://nominatim.openstreetmap.org/search"
    params = {"q": location, "format": "json", "limit": 1}

    # sending a request to the Nominatim API
    response = requests.get(endpoint, params=params)
    result = response.json()[0]

    # getting the latitude and longitude from the response of the API
    latitude = float(result["lat"])
    longitude = float(result["lon"])

    # creating a geospatial index on the coordinates field
    tweets_collection.create_index([("coordinates", "2dsphere")])
    distance = int(distance) # converting string distance to integer
    query = {"coordinates": {"$near": {"$geometry": {"type": "Point", "coordinates": [longitude, latitude]}, "$maxDistance": distance}}}
    limit = int(limit) # converting string limit to integer
    tweets_match = tweets_collection.find(query).limit(limit)
    
    tweets_list = []
    for result in tweets_match:
        tweet = {
            'id': str(result['_id']),
            'text': result['text'],
            'user_id': result['user_id'],
            'tweet_pop': result['tweet_pop'],
            'created_at': result['timestamp']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        # add information about coordinates if the key exists
        if 'coordinates' in result:
            tweet['coordinates']: result['coordinates']

        tweets_list.append(tweet)

    # return custom message to the user if there are no matches
    if len(tweets_list) == 0:
        return "There are no tweets near this location yet."

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        tweets_list = sorted(tweets_list, key = lambda x: x['created_at'], reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        tweets_list = sorted(tweets_list, key = lambda x: x['created_at'], reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        tweets_list = sorted(tweets_list, key = lambda x: int(x['tweet_pop']), reverse = True)

    # add the search and result into cache
    lrucache.put(str(limit) + location + str(distance) + sort_criterion, tweets_list) 
    logger.info("retrieve_tweets_location-" + str(location) +  "-" + str(lrucache.display_cache())) 

    return tweets_list

# function to retrieve tweets with matching hastags
def retrieve_tweets_hashtags(limit, hashtag, sort_criterion = 'popularity'):
    """
        Function to retrieve tweets containing one or more user-specified hashtags.
        Input:
            limit (int): maximum number of results to be displayed
            hashtag (str): user-specified hashtag(s). If multiple, they must be separated by spaces.
            sort_criterion (str): criteria for sorting the results
                default: decreasing order of popularity (favorite count)
                valid inputs:
                    'oldestToNewest', 'newestToOldest', 'popularity'
        Output:
            out (list): list of tweets containing the hashtag(s)
    """
    # split hashtags separated by spaces and insert them as elements into a list
    hashtags = hashtag.split()

    # check if the tweet information is in the cache
    search_by_hashtag = lrucache.get(limit + hashtag + sort_criterion)
    if search_by_hashtag is not None:
        logger.info("retrieve_tweets_hashtags - query in cache")
        return search_by_hashtag

    out = []
    query = {"hashtags": {"$in": hashtags}}
    limit = int(limit) # convert string limit into integer
    tweets_match = tweets_collection.find(query).limit(limit)

    for result in tweets_match:
        tweet = {
            'id': str(result['_id']),
            'text': result['text'],
            'user_id': result['user_id'],
            'tweet_pop': result['tweet_pop'],
            'created_at': result['timestamp']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        # add information about coordinates if the key exists
        if 'coordinates' in result:
            tweet['coordinates']: result['coordinates']
        
        out.append(tweet)

    # return custom message to the user if there are no matches
    if len(out) == 0:
        return ("There are no tweets under this hastag.")

    # sort the results from oldest to newest before returning, if specified 'oldestToNewest'
    if sort_criterion == "oldestToNewest":
        out = sorted(out, key = lambda x: x['created_at'], reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        out = sorted(out, key = lambda x: x['created_at'], reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        out = sorted(out, key = lambda x: int(x['tweet_pop']), reverse = True)

    # add the search and result into cache
    lrucache.put(str(limit) + hashtag + sort_criterion, out) 
    logger.info("retrieve_tweets_hashtags-" + str(hashtag) + "-" + str(lrucache.display_cache())) 

    return out

# function to get the top 10 most followed users
def top_10_users(localusername):
    """
        Function to obtain the 10 most-followed users in the database.
        Input:
            localusername (str): automatically retrieved by Python; the local system's username
        Output:
            user_info_list (list): list containing user information of the top 10 most-followed users, ordered in the decreasing
                order of number of followers.
    """

    # check if the top username information is in the cache
    search_by_localuser = lrucache.get('top_10_users')
    if search_by_localuser is not None:
        logger.info("top_10_users found in cache")
        return search_by_localuser

    # connecting to the PostgreSQL database
    p_conn = psycopg2.connect(
        dbname = "twitter",
        user = localusername,
        password = "",
        host = "localhost",
        port = "5432"
    )
    p_cur = p_conn.cursor()

    # selecting the top 10 most-followed users
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

    # add the search and result into cache
    lrucache.put("top_10_users", user_info_list)  
    logger.info("top_10_users-" + str(lrucache.display_cache()))

    return user_info_list

# function to get the trending tweets (most favorited, replied to and retweeted)
def trendingTweets():
    """
        Function to obtain the trending tweets at any moment. The trending tweets are the tweets with the highest popularity score.
        Input:
            None
        Output:
            tweets_list (list): top 10 tweets with the highest popularity score, sorted in decreasing order.
    """
        
    # check if the Trending tweet information is in the cache
    retrieve_trending_Tweet = lrucache.get("TrendingTweet")
    if retrieve_trending_Tweet is not None:
        logger.info("Trending tweets in cache")
        return retrieve_trending_Tweet
    
    # create a pipeline to obtain 10 tweets with the highest popularity score
    pipeline = [
        {"$project": {
            "_id": 1,
            "text": 1,
            "user_id": 1,
            "tweet_pop": 1,
            "timestamp": 1,
            "coordinates": {"$ifNull": ["$coordinates", False]},
            "retweet": {"$ifNull": ["$retweeted_status", False]}
        }},
        {"$sort": {"tweet_pop": -1}},
        {"$limit": 10}
    ]

    tweets_match = tweets_collection.aggregate(pipeline)

    tweets_list = []
    for result in tweets_match:
        tweet = {
            'id': str(result['_id']),
            'text': result['text'],
            'user_id': result['user_id'],
            'tweet_pop': result['tweet_pop'],
            'created_at': result['timestamp']
        }
        # add information on whether the tweet is a retweet
        if 'retweet' in result:
            tweet['retweet'] = "Yes"
        # add information about coordinates if the key exists
        if 'coordinates' in result:
            tweet['coordinates']: result['coordinates']

        tweets_list.append(tweet)

    # add the search and result into cache
    lrucache.put("TrendingTweet", tweets_list) 
    logger.info("trendingTweets-" + str(lrucache.display_cache()))  

    return tweets_list

# main search function
def search(username_for_user_info = None, user_id_for_tweets = None, username_tweets = None, user_id = None, tweet_id = None, keyword = None, hashtags = None, location = None, time_range = None, sort_criterion = 'popularity', distance = 100000, top10users = "no", trending_tweets = "no", limit = 10):
    """
        The main search function that is called by the API router. This function calls relevant search functions based on the 
        parameters input by the user.
    """
    
    # create a list of mandatory parameters to be specified unless one of top10users and trending_tweets is not 'no'
    params = [username_for_user_info, user_id_for_tweets, username_tweets, user_id, tweet_id, keyword, hashtags, location, time_range]

    # if both top10users and trending_tweets are 'no', check whether one mandatory search parameter has been specified
    if (top10users == 'no' and trending_tweets == 'no'):
        # raise exception if no mandatory search parameters are specified
        if all(x is None for x in params):
            raise HTTPException(status_code = NoParametersGivenError.code, detail = NoParametersGivenError.description)
        # raise exception if too many mandatory search parameters are specified (more than one)
        if params.count(None) < len(params) - 1:
            raise HTTPException(status_code = TooManyParametersGivenError.code, detail = TooManyParametersGivenError.description)
    
    # find the localusername
    localusername = getpass.getuser()

    # call relevant search functions based on the input parameters
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
    elif time_range is not None:
        return retrieve_tweets_time_range(limit, time_range, sort_criterion)
    elif top10users != "no":
        return top_10_users(localusername)
    else:
        return trendingTweets()

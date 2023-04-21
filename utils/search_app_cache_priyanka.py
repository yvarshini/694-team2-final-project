# importing required libraries
import psycopg2
from pymongo import MongoClient
from fastapi import HTTPException
from exceptions.exceptions import *
import requests

'''
LRU cache is a cache removal algorithm where the least recently used items in a cache are removed to allocate space for new additions
Implementation : LRU supports the Fast item lookup, constant time (o(1)) insertion and deletion,Ordered storage.
HashMap - hold the keys and address of the Nodes of Doubly LinkedList.Doubly LinkedList will hold the values of keys.

'''
# Exception class
class ArgumentsError(Exception):
    def __init__(self, message):
        self.message = message
        
        
class Node:
    """
    Doubly linked list node for storing cached items.
    """
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None
        
class LRUCache:
    """
    LRU cache implementation using a doubly linked list and a hashmap.
    """
    def __init__(self, capacity):
        self.capacity = capacity
        self.size = 0
        self.head = None
        self.tail = None
        self.cache = {}
        
    def get(self, key):
        # Check if the key is in the cache
        if key in self.cache:
            # Move the node to the front of the list
            node = self.cache[key]
            self._move_to_front(node)
            return node.value
        else:
            return None
        
    def put(self, key, value):
        # Check if the key is already in the cache
        if key in self.cache:
            # Update the value and move the node to the front of the list
            node = self.cache[key]
            node.value = value
            self._move_to_front(node)
        else:
            # Create a new node and add it to the front of the list
            node = Node(key, value)
            self.cache[key] = node
            self._add_to_front(node)
            self.size += 1
            
            # If the cache is over capacity, remove the least recently used node
            if self.size > self.capacity:
                removed_node = self._remove_last()
                del self.cache[removed_node.key]
                self.size -= 1
                
    def _add_to_front(self, node):
        # Add a node to the front of the list
        if not self.head:
            self.head = node
            self.tail = node
        else:
            node.next = self.head
            self.head.prev = node
            self.head = node
        
    def _remove_last(self):
        # Remove the last node from the list and return it
        node = self.tail
        if self.tail.prev:
            self.tail = self.tail.prev
            self.tail.next = None
        else:
            self.head = None
            self.tail = None
        return node
        
    def _move_to_front(self, node):
        # Move a node to the front of the list
        if node == self.head:
            return
        elif node == self.tail:
            self.tail = node.prev
        else:
            node.prev.next = node.next
            node.next.prev = node.prev
        node.next = self.head
        node.prev = None
        self.head.prev = node
        self.head = node
        
if __name__ == '__main__':
    
    lrucache = LRUCache(100)


# <h3> <b>Caching - Current Trending Topics</b></h3>

# In[4]:


def get_trending_topics(self, topic):
        response = self.get(topic)
        if (response != null or response.isEmpty()):
            return response        
        else:
            # write code to make a DB call when requestdata not in cache
            response = retrieve_tweets_keyword(keyword = "corona", sort_criterion = 'oldestToNewest')
            self.put(topic,response)


# <h3><b>Caching - Tweet id</b></h3>

# In[5]:


def get_Tweets(self, tweetId):
        response = self.get(tweetId)
        if (response != null or response.isEmpty()):
            return response        
        else:
            # Make a DB call when requestdata not in cache
            response = retrieve_tweet(tweetId)
            self.put(tweetId,response)


# <h3><b>Caching - User Timelines </b></h3>

# In[6]:


def get_UserTimelines(self, tweetId):
        response = self.get(tweetId)
        if (response != null or response.isEmpty()):
            return response        
        else:
            # Make a DB call when requestdata not in cache
            response = retrieve_tweets_user(tweetId)
            self.put(tweetId,response)


# <h3><b>Caching - UserProfiles</b> </h3>

# In[7]:


def get_UserProfiles(self, username):
        response = self.get(username)
        if (response != null or response.isEmpty()):
            return response        
        else:
            # Make a DB call when requestdata not in cache
            response = get_user_info(tweetId)
            self.put(username,response)


# In[8]:


# function to get user information
def get_user_info(username):
    """
        This function returns the user information as a JSON object.
        Input:
            username (str): Twitter user ID which we want to look up
        Output:
            user_out (JSON object): user information corresponding to username
    """
    username = str(username)
    
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
    
    p_cur.close()

    return user_out


# In[9]:


# function to retrieve all tweets by a user
def retrieve_tweets_user(username: str, sort_criterion = 'popularity'):
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
    
    p_conn = psycopg2.connect(
        dbname = "twitter",
        user = "varshiniyanamandra",
        password = "",
        host = "localhost",
        port = "5432"
    )
    p_cur = p_conn.cursor()
    
    # check if the user id is valid
    p_cur.execute("SELECT * FROM TwitterUser WHERE screen_name = '{0}';".format(username))
    username_db = p_cur.fetchone()
    if username_db is None:
        # raise an exception if the user doesn't exist in the database
        raise HTTPException(status_code = UserNotFoundError.code, detail = UserNotFoundError.description)
    user_id = username_db[0]
    
    p_cur.close()

    # if the user exists, proceed to search MongoDB
    query = {'user_id': user_id}
    tweets_match = tweets_collection.find(query)
    
    if tweets_match is None:
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
        tweets_list = sorted(tweets_list, key = lambda x: int(x['created_at']), reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        tweets_list = sorted(tweets_list, key = lambda x: int(x['created_at']), reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        tweets_list = sorted(tweets_list, key = lambda x: int(x['favorite_count']), reverse = True)
        
    return tweets_list


# In[10]:


# function to search tweets based on tweet id
def retrieve_tweet(tweet_id):
    """
        Function to get the information of a tweet based on a user-specified tweet ID.
        Input:
            tweet_id: user-specified tweet ID
        Output:
            tweet (JSON object): tweet corresponding to tweet_id
    """
    query = {'_id': tweet_id}
    result = tweets_collection.find_one(query)
    if result is None:
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

    return tweet


# In[11]:


# function to retreive tweets containing a specified keyword
def retrieve_tweets_keyword(keyword: str, sort_criterion = None):
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

    # check if sort_criterion is valid, if specified:
    if sort_criterion is not None:
        if sort_criterion not in ['oldestToNewest', 'newestToOldest', 'popularity']:
            raise HTTPException(status_code = InvalidSortCriterionError.code, detail = InvalidSortCriterionError.description)

    out = []
    query = {'$text': {'$search': keyword}}
    tweets_match = tweets_collection.find(query).limit(10) # we can add .limit(PAGE_LIMIT) here, if needed
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
        out = sorted(out, key = lambda x: int(x['created_at']), reverse = False)
    elif sort_criterion == "newestToOldest":
        # otherwise sort the results from newest to oldest before returning if specified 'newestToOldest'
        out = sorted(out, key = lambda x: int(x['created_at']), reverse = True)
    else:
        # sort the output in the decreasing order of favorites (popularity), by default or if specified 'popularity'
        out = sorted(out, key = lambda x: int(x['favorite_count']), reverse = True)
        
    return out


# main search function
def search(username = None, username_tweets = None, user_id = None, tweet_id = None, keyword = None, location = None, sort_criterion = 'popularity', distance = 100000):
    params = [username, username_tweets, user_id, tweet_id, keyword, location]
    # raise exception if no search parameters are specified
    if all(x is None for x in params):
        raise HTTPException(status_code = NoParametersGivenError.code, detail = NoParametersGivenError.description)
    # raise exception if too many search parameters are specified
    if params.count(None) < len(params) - 1:
        raise HTTPException(status_code = TooManyParametersGivenError.code, detail = TooManyParametersGivenError.description)
    
    if username is not None:
        return get_user_info(username)
    elif username_tweets is not None:
        return retrieve_tweets_user(username_tweets, sort_criterion)
    elif tweet_id is not None:
        return retrieve_tweet(tweet_id)
    else:
        return retrieve_tweets_keyword(keyword, sort_criterion)
from fastapi import APIRouter
from search_app import search
import sys
import os

router = APIRouter()
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURR_DIR)

@router.post("/searchapp/")
def searchapp(username = None, username_tweets = None, user_id = None, tweet_id = None, keyword = None, location = None, sort_criterion = 'popularity', distance = 100000):
    output = search(username, username_tweets, user_id, tweet_id, keyword, location, sort_criterion, distance)
    return output
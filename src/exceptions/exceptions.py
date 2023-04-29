"""
    author: Varshini Yanamandra
"""

# defining custom exception classes

class UserNotFoundError(Exception):
    code = 404
    description = {"error message": "The user ID specified was not found in the database. Please check and try again."}

class TweetNotFoundError(Exception):
    code = 404
    description = {"error message": "The tweet specified using the tweet ID was not found in the database. Please check and try again."}

class InvalidSortCriterionError(Exception):
    code = 400
    description = {"error message": "The sort criterion specified is invalid. If you wish to sort your results, please specify one of 'oldestToNewest', 'newestToOldest' or 'popularity'."}

class UnsuccessfulConnectionPostgreSQL(Exception):
    code = 400
    description = {"error message": "Unable to connect to PostgreSQL. Please try again."}

class NoParametersGivenError(Exception):
    code = 400
    description = {"error message": "No search parameters specified. Please specify one of username_for_user_info, user_id_for_tweets, username_tweets, user_id, tweet_id, keyword, hashtags, location or time_range."}

class TooManyParametersGivenError(Exception):
    code = 400
    description = {"error message": "Too many search parameters specified. Please specify only one of username_for_user_info, user_id_for_tweets, username_tweets, user_id, tweet_id, keyword, hashtags, location or time range."}

class InvalidTimeWindowError(Exception):
    code = 400
    description = {"error message": "Invalid time window. Please provide one of '1 week', '1 month', '3 months', '6 months', '1 year', '5 years' or 'all time'."}

class BadDistanceError(Exception):
    code = 400
    description = {"error message": "Bad request. Please check your location or increase the distance and try again."}
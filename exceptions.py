# need to work on exception handling outside of the context of APIs.

class UserNotFoundError(Exception):
    code = 404
    description = {"error message": "The user ID specified was not found in the database. Please check and try again."}

class TweetNotFoundError(Exception):
    code = 404
    description = {"error message": "The tweet specified using the tweet ID was not found in the database. Please check and try again."}
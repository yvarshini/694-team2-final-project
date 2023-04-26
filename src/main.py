from routers import router
from fastapi import FastAPI
import uvicorn
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import time

tags_metadata = [
    {
        "name": "Twitter Search Application",
        "author": "Team 2"
    }
]

description = """
This is an application designed to search across a given twitter dataset based on the following parameters: username, username_tweets, user_id, tweet_id, keyword, location, sort_criterion, distance.
IMPORTANT:
Accepted options for certain fields are as follows:
    1. sort_criterion: accepts only 'popularity', 'oldestToNewest' or 'newestToOldest'
    2. top10users and trendingTweets: any value other than 'no' (default) is considered a yes
    3. distance and limit should be numeric values.
The distance is in meters.
"""

app = FastAPI(
    openapi_tags = tags_metadata,
    docs_url = "/docs",
    title = "team-2-search-application",
    version = "1.0",
    description = description,
    openapi_url = "/openapi.json",
    middleware = [
        Middleware(CORSMiddleware, allow_origins = ['*'])
    ]
)

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response: Response = await call_next(request)
        process_time = time.time() - start_time
        response.headers['X-Process-Time'] = str(process_time)
        return response

app.include_router(router.router)

app.add_middleware(TimingMiddleware)

if __name__ == "__main__":
    uvicorn.run(app)
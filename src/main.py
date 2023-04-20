from routers import router
from fastapi import FastAPI
import uvicorn

tags_metadata = [
    {
        "name": "Twitter Search Application",
        "author": "Team 2"
    }
]

description = """
This is an application designed to search across a given twitter dataset based on the following parameters: username, username_tweets, user_id, tweet_id, keyword, location, sort_criterion, distance.
"""

app = FastAPI(
    openapi_tags = tags_metadata,
    docs_url = "/docs",
    title = "team-2-api",
    version = "1.0",
    description = description,
    openapi_url = "/openapi.json"
)

app.include_router(router.router)

if __name__ == "__main__":
    uvicorn.run(app)
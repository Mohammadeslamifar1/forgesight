"""Run this file in PyCharm after following README setup."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("forgesight.api:app", host="127.0.0.1", port=8010)

# Telegram Chat Searcher
This program is made to replace Telegram Desktop's awful search feature. Telegram Desktop makes me (and all other Korean users) crazy when trying to search some messages written by Korean, since its search method only works if the keyword and word in message - divided by space - matches. For example, in Telegram Desktop, we can't search message '버스정류장' by keyword '버스'.   
pytelegramsearch uses MongoDB to cache the whole cached message (only text, not medias and files), since the query limit of Telegram API is very strict (100 message per second). Caching fetched messages will dramatically increase search performance.

## Requirements
- MongoDB installed and running on `localhost:27017`

## Installation
0. `brew install mongodb`
1. `mongod` (skip if mongodb instance is already running)
2. `pip install -r requirements.txt`

## How to run
- `python search.py <Chat Link>`
- Additional Options
  - `-d <filename>`: dumps search result to specified filename.
  - `-c`: searches message only from cached messages.

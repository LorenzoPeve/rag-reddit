from dotenv import load_dotenv
import json
import os
import requests
from requests.auth import HTTPBasicAuth

load_dotenv()



# url = 'https://www.reddit.com/api/v1/access_token'

# response = requests.post(
#     url,
#     auth=HTTPBasicAuth(
#         os.getenv('REDDIT_CLIENT_ID'),
#         os.getenv('REDDIT_CLIENT_SECRET')
#     ),
#     data={
#         "grant_type": "password",
#         "username": os.getenv('REDDIT_USER'), 
#         "password": os.getenv('REDDIT_USER_PASSWORD')
#     },
#     headers={"User-Agent": os.getenv('USER_AGENT')}
# )

# print(response.json())




response = requests.get(
    "https://oauth.reddit.com/api/v1/me",
    headers={
        'Authorization': f"bearer {os.getenv('TOKEN')}",
        "User-Agent": os.getenv('USER_AGENT')
    }
)

with open('response.json', 'w') as f:
    json.dump(response.json(), f, indent=4)


print(response.json())
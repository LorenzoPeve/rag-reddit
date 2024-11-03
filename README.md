 https://www.reddit.com/prefs/apps

https://github.com/reddit-archive/reddit/wiki/OAuth2


## 

Your username is: reddit_bot
Your password is: snoo
Your app's client ID is: p-jcoLKBynTLew
Your app's client secret is: gko_LXELoV07ZBNUXrvWZfzE3aI

```
reddit@reddit-VirtualBox:~$ curl -X POST -d 'grant_type=password&username=reddit_bot&password=snoo' --user 'p-jcoLKBynTLew:gko_LXELoV07ZBNUXrvWZfzE3aI' https://www.reddit.com/api/v1/access_token
{
    "access_token": "J1qK1c18UUGJFAzz9xnH56584l4", 
    "expires_in": 3600, 
    "scope": "*", 
    "token_type": "bearer"
}
```

```
In [1]: import requests
In [2]: import requests.auth
In [3]: client_auth = requests.auth.HTTPBasicAuth('p-jcoLKBynTLew', 'gko_LXELoV07ZBNUXrvWZfzE3aI')
In [4]: post_data = {"grant_type": "password", "username": "reddit_bot", "password": "snoo"}
In [5]: headers = {"User-Agent": "ChangeMeClient/0.1 by YourUsername"}
In [6]: response = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, data=post_data, headers=headers)
In [7]: response.json()
Out[7]: 
    {u'access_token': u'fhTdafZI-0ClEzzYORfBSCR7x3M',
    u'expires_in': 3600,
    u'scope': u'*',
    u'token_type': u'bearer'}
```

## Dev Environment

```bash
docker compose -p reddit_stack up -d --build
docker compose -p reddit_stack down --volumes
docker compose down --volumes
```


## Reddit API

### Reddit Glossary
Here is a list of the six different types of objects returned from Reddit:    
- `t1` These objects represent Comments
- `t2` These objects represent Redditors           
- `t3` These objects represent Submissions (i.e., posts)
- `t4` These objects represent Messages
- `t5` These objects represent Subreddits   
- `t6` These objects represent Awards

### Querying Subreddits

#### About a subreddit
```python
response = requests.get(
    "https://oauth.reddit.com/r/dataengineering/about",
    headers={
        'Authorization': f"bearer {os.getenv('TOKEN')}",
        "User-Agent": os.getenv('USER_AGENT'),
    },
)
```
Another informational endpoint:
- `https://oauth.reddit.com/r/dataengineering/about/moderators`


```json
{
    "kind": "t5",
    "data": {
        "display_name": "dataengineering",
        "header_img": null,
        "title": "Data Engineering",
        "allow_galleries": true,
        "icon_size": null,
        "primary_color": "",
        "active_user_count": 63,
        "icon_img": "",
        "display_name_prefixed": "r/dataengineering",
        "accounts_active": 63,
        "public_traffic": false,
        "subscribers": 218387,
        "user_flair_richtext": [],
        "videostream_links_count": 0,
        "name": "t5_36en4",
        ...
    }
}
```
#### Listing submissions a.ka. Posts
Use the following endpoints
- `[/r/subreddit]/hot`
- `[/r/subreddit]/new`
- `[/r/subreddit]/random`
- `[/r/subreddit]/rising`
- `[/r/subreddit]/top`
- `[/r/subreddit]/controversial`

Take it with a grain of salt but this is how each endpoint works

- `hot` = `upvotes/time` what's been getting a lot up upvotes/comments recently
- `new` sorts post by the time of submission with the newest at the top of the page
- `random` is a random post from the subreddit
- `rising` is what is getting a lot of activity (comments/upvotes) right now
- `top` = `upvotes - downvotes`
- `controversial` those that that have a high number of upvotes and downvotes, indicating a division in opinion among users.

##### Default is hot
These two endpoints are equivalent
- "https://oauth.reddit.com/r/dataengineering/"
- "https://oauth.reddit.com/r/dataengineering/hot"

##### `t` parameter is only possible for `top` and `controversial`
- As expected we cannot add `new`, `hot`, and `rising` do not have (as expected)
- t is one of (hour, day, week, month, year, all)

#### Pagination Limitations
- Reddit’s API uses pagination to retrieve posts. You can fetch a limited number of posts in a single request (up to 100 at a time), and to get more, you have to make subsequent requests using `after` and `before` tokens to get the next "page" of posts.

#### Dynamic nature of the platform
- New posts are being created all the time in active subreddits. As users continuously submit new content, the most recent posts are always changing. If you are trying to scrape or retrieve all posts in a subreddit, by the time you make multiple API requests, new posts may have been added.
  - **This means that the list of posts you're pulling can become outdated as you progress through your API requests.**
- Similarly, posts can also be updated or removed (by moderators or the original poster), or they might receive new comments and upvotes
  - **causing them to shift in rank or popularity**

####  Historical Data Accessibility:
- Reddit's API prioritizes recent content, so after a certain point, very old posts may no longer be available via the API, especially for large subreddits. You can access only a limited timeframe of posts from the API due to the way data is stored and indexed.
- For very old or archived posts, the API might not return them, even if you paginate through all the available content.

#### Searching a subreddit

### Tags  

On Reddit, tags are labels used to categorize and organize posts within a subreddit. They help users quickly identify the type of content or the topic of the post.

Below are the tags for the data engineering subreddit. To increase data quality
those post tagged as `Meme` are not included in the dataset.

![alt text](_docs/tags.png)


### 💡 Future Work

💡 What about focusing on different 


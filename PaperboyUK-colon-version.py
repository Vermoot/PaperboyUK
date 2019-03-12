import datetime
import tweepy
import imgurpython
import praw
import re


# Tweepy setup
TWEEPY_CONSUMER_KEY = 'Tww4BA61Kysxd7NF501Z5oU4d'
TWEEPY_CONSUMER_SECRET = 'ccAVb7xayTQiFryYpbojDwK7cwbkNfoCeW1HizYz0BRIm6a5ce'
TWEEPY_ACCESS_TOKEN = '31172325-kryUxxGBZVHRndlTR7LY98YxJTefhJmUsWXfzY7la'
TWEEPY_ACCESS_TOKEN_SECRET = 'uSlHX9WjIbdk6IZv6il5vHu8faq8lZPvBRoLghSUJ3FTd'
tweepy_auth = tweepy.OAuthHandler(TWEEPY_CONSUMER_KEY, TWEEPY_CONSUMER_SECRET)
tweepy_auth.set_access_token(TWEEPY_ACCESS_TOKEN, TWEEPY_ACCESS_TOKEN_SECRET)
tw = tweepy.API(tweepy_auth)

# imgurpython setup
imgur_client_id = "ead7ce771e178d2"
imgur_client_secret = "196a777f20644b5d610a5dfa0d44663026188b45"
imgur_access_token = "6e7cba4ce264bd0abed0df98e525e99ca11b853e"
imgur_refresh_token = "769076576f11632c6621e3f1376a489afdeb19f7"
imgur = imgurpython.ImgurClient(imgur_client_id, imgur_client_secret, imgur_access_token, imgur_refresh_token)

# praw (Reddit Python API) setup
reddit = praw.Reddit(client_id='L5usbKU_UnkPOQ',
                     client_secret='ZDvGyzsD-pAY42hZH7QRaYRzPuY',
                     refresh_token="261991416840-7A-g7GlzZeV_8gT5K2Ru1-19JZY",
                     user_agent='/r/ukpolitics Paperboy by Vermoot',
                     username='PaperboyUK')

dt = datetime

# Date in D/M/Y format for use in imgur album name and other places
today = "%02i/%02i/%02i" % (dt.date.today().day,
                            dt.date.today().month,
                            dt.date.today().year)

day_of_the_week = datetime.datetime.today().strftime('%A')

# Get @BBCNews, @AllieHBNews and @MsHelicat's last 100 tweets
BBCtimeline = (tw.user_timeline("BBCNews", count=100, tweet_mode="extended", page=1,
                                include_rts="false", exclude_replies="true") +
               tw.user_timeline("AllieHBNews", count=100, tweet_mode="extended", page=1,
                                include_rts="false", exclude_replies="true") +
               tw.user_timeline("MsHelicat", count=100, tweet_mode="extended", page=1,
                                include_rts="false", exclude_replies="true") +
               tw.user_timeline("hendopolis", count=100, tweet_mode="extended", page=1,
                                include_rts="false", exclude_replies="true"))

# Get the last 300 #tomorrowspaperstoday tweets (about a day)
tpt_search = tweepy.Cursor(tw.search, q="#tomorrowspaperstoday", tweet_mode="extended", exclude="retweets").items(300)

errors = ""


def is_recent_enough(tweet):  # Verify the tweet isn't too old, to avoid fetching yesterday's front page
    max_age = 12  # In hours
    if dt.datetime.utcnow() - tweet.created_at < dt.timedelta(hours=max_age):
        return True


class Paper:

    def __init__(self, name, aliases=None, account=None, front_page_url=None, source=None, tweet_link=None):
        self.name = name  # Full name for debug purposes
        self.aliases = aliases  # Abbreviated name for search in tweets
        self.account = account  # Official Twitter account
        self.front_page_url = front_page_url  # What we're after
        self.source = source  # Where the front page was found (account)
        self.tweet_link = tweet_link  # Where the front page was found (tweet)

    def debug(self, tweet):  # Print stuff in the console to verify the front pages
        print(self.name, ": ", end="")
        print("\n\n" + tweet.full_text)
        print("\n" + tweet.extended_entities["media"][0]["media_url"])
        print("From", self.source)
        print("Tweet :", self.tweet_link)
        print("\n --- \n")

    def has_frontpage(self, tweet):  # To be used only in the paper's own twitter account
        global errors
        if is_recent_enough(tweet):  # Make sure not to get yesterday's papers
            if tweet.author.screen_name == self.account:  # Only on th paper's own twitter page:
                if(re.search(r"front\s?page", tweet.full_text, re.IGNORECASE) and  # If tweet contains "front[]page"
                   "sport" not in tweet.full_text):  # No "Sport" issues
                        return True  # The tweet has a front page.
                if(re.search(r"front\s?page", tweet.full_text, re.IGNORECASE) and  # If tweet contains "front[]page"
                   "sport" in tweet.full_text):  # Debug in case the sport escape produces problems
                        errors += "%s : [Tweet](%s) was skipped because \"Sport\" was in there, check for a false negative.  \n"\
                                  % (self.name, "https://twitter.com/" + tweet.author.screen_name + "/status/" + str(tweet._json["id"]))
            for alias in self.aliases:  # Test for each alias of the paper
                if ((re.match(r"%s(:| :)" % alias, tweet.full_text, re.IGNORECASE) or  # "[Paper]:" in tweet
                     re.search(r"(Tomorrow|Today|%s)['‘’]s %s\b" % (day_of_the_week, alias),  # Pretty regex
                               tweet.full_text, re.IGNORECASE)) and
                    "sport:" not in tweet.full_text.lower()):  # Don't want Sport issues
                        return True

    def process_fp(self, tweet):
        global errors
        try:
            self.source = "%s (@%s)" % (tweet.author.name, tweet.author.screen_name)
            self.tweet_link = "https://twitter.com/" + tweet.author.screen_name + "/status/" + str(tweet._json["id"])
            self.debug(tweet)
            return tweet.extended_entities["media"][0]["media_url"]  # Front page picture URL got.
        except AttributeError:
            error = "%s : False positive for a front page here : %s  \n"\
                      % (self.name, "https://twitter.com/" + tweet.author.screen_name + "/status/" + str(tweet._json["id"]))
            print(error)
            errors += error
            return None

    def get_frontpage(self):  # Get the fontpage picture for the paper from Twitter

        # Look for a front page on the paper's official Twitter account
        paper_TL = tw.user_timeline(self.account, count=200, tweet_mode="extended",
                                    include_rts="false", exclude_replies="true")  # Get the paper's Twitter TL

        search_scope = paper_TL + BBCtimeline + list(tpt_search)

        for tweet in search_scope:  # Check for every tweet in the paper's TL
            if self.has_frontpage(tweet):
                return self.process_fp(tweet)

        # Nothing was found
        print(self.name + " : Nothing found")
        print("\n --- \n")


# Class init for each wanted paper #
DailyStar = Paper("Daily Star", ["Star", "Daily Star"], "Daily_Star")
DailyMirror = Paper("Daily Mirror", ["Mirror", "Daily Mirror", "Sunday Mirror"], "DailyMirror")
TheSun = Paper("The Sun", ["Sun", "Sun on Sunday"], "TheSun")
ScottishSun = Paper("The Scottish Sun", ["Scottish Sun", "Scottish Sun on Sunday"], "scottishsun")
Metro = Paper("Metro", ["Metro"], "MetroUK")
DailyMail = Paper("Daily Mail", ["Daily Mail", "Mail", "Mail on Sunday"], "MailOnline")
DailyExpress = Paper("Daily Express", ["Daily Express", "Express", "Sunday Express"], "daily_express")
iNews = Paper("i News", ["i", "i weekend"], "theipaper")
Independent = Paper("The Independent", ["Independent", "Independent on Sunday"], "Independent")
Telegraph = Paper("The Telegraph", ["Daily Telegraph", "Telegraph", "Sunday Telegraph"], "TelegraphNews")
Times = Paper("The Times", ["Times", "Sunday Times"], "thetimes")
Guardian = Paper("The Guardian", ["Guardian"], "guardian")
FinancialTimes = Paper("The Financial Times", ["Financial Times", "FT"], "FT")
TheNational = Paper("The National", ["National"], "ScotNational")
CityAM = Paper("City A.M.", ["City A.M."], "cityam")
MorningStar = Paper("Morning Star", ["Morning Star"], "M_Star_Online")
TheHerald = Paper("The Herald", ["Herald"], "heraldscotland")
TheScotsman = Paper("The Scotsman", ["Scotsman"], "TheScotsman")
# TODO Lymington Times, Refional Standard, Regional Observer, Western Morning News, Birmingham Mail,
#  Manchester Evening News, Daily Echo (Southampton), Yorkshire Post, YNP
# TODO Sunday Post, Jewish Chronicles,
# TODO Belfast Telegraph, Irish News

# Round them all up
Papers = [TheSun, ScottishSun, DailyStar, DailyMirror, Metro, DailyMail, DailyExpress, Times, FinancialTimes, Guardian,
          Telegraph, iNews, Independent, MorningStar, CityAM, TheNational, TheHerald, TheScotsman]

# Search for a frontpage image for each paper
for paper in Papers:
    paper.front_page_url = paper.get_frontpage()

# Get the collage from @cfbcity
Collage = Paper("Front pages Collage", account="cfbcity", source="https://www.twitter.com/cfbcity")
cfb_tl = tw.user_timeline("cfbcity", count=30, tweet_mode="extended", include_rts="false", exclude_replies="true")
for tweet in cfb_tl:
    if ("front page newspaper collage" in tweet.full_text.lower() and
            is_recent_enough(tweet)):
        Collage.front_page_url = tweet.extended_entities["media"][0]["media_url"]
        Collage.tweet_link = "https://twitter.com/cfbcity/status/" + str(tweet._json["id"])
        break
Papers.insert(0, Collage)

# Special treatment for WalesOnline papers
wales_online_names = ["South Wales Echo", "Western Mail"]
this_wo_paper = ""
for tweet in tw.user_timeline("walesonline", count=100, tweet_mode="extended"):
    if ("front page" in tweet.full_text.lower() and  # Tweet contains "front page" (case insensitive)
            is_recent_enough(tweet)):
        for name in wales_online_names:
            if name.lower() in tweet.full_text.lower():
                this_wo_paper = name
        Papers.append(Paper(name=this_wo_paper,
                            source="%s (@%s)" % (tweet.author.name, tweet.author.screen_name),
                            tweet_link="https://twitter.com/walesonline/status/" + str(tweet._json["id"]),
                            front_page_url=tweet.extended_entities["media"][0]["media_url"]))
        print(this_wo_paper + " :")
        print("\n" + tweet.full_text)
        print("\n" + tweet.extended_entities["media"][0]["media_url"])
        print("\nSource tweet : " + Papers[-1].tweet_link)
        print("From the special WalesOnline treatment")
        print("\n --- \n")

# Special treatment for P&J regional papers  # TODO redo special treatments properly
PnJnames = ["Aberdeen and Aberdeenshire", "Aberdeen", "North-East", "North East", "Moray",
            "Inverness, Highlands and Islands", "Highlands and Islands", "Highlands", "Inverness"]
thisPnjPaper = ""
for tweet in tw.user_timeline("pressjournal", count=100, tweet_mode="extended"):
    if ("front page" in tweet.full_text.lower() and  # Tweet contains "front page" (case insensitive)
            is_recent_enough(tweet)):
        for name in PnJnames:
            if name.lower() in tweet.full_text.lower():
                thisPnjPaper = name
        Papers.append(Paper(name=("P&J " + thisPnjPaper),
                            source="%s (@%s)" % (tweet.author.name, tweet.author.screen_name),
                            tweet_link="https://twitter.com/pressjournal/status/" + str(tweet._json["id"]),
                            front_page_url=tweet.extended_entities["media"][0]["media_url"]))
        print("Press & Journal (" + thisPnjPaper + ") :")
        print("\n" + tweet.full_text)
        print("\n" + tweet.extended_entities["media"][0]["media_url"])
        print("\nSource tweet : " + Papers[-1].tweet_link)
        print("From the special P&J treatment")
        print("\n --- \n")



def recap():
    for paper in Papers:
        if paper.front_page_url is not None:
            print(paper.name + " : " + paper.front_page_url)
        else:
            print(paper.name + " : No front page found")


recap()

# Upload Papers on IMGUR

album = None


def upload_frontpages():
    global album
    album = imgur.create_album({"title": "The Papers (" + today + ")"})
    print("Created the \"The Papers (" + today + ")\" album at https://www.imgur.com/a/" + album["id"] + ".")
    for paper in Papers:
        if paper.front_page_url is not None:
            imgur.upload_from_url(url=paper.front_page_url, config={"title": paper.name, "album": album["id"]},
                                  anon=False)
            print("Uploaded the front page for " + paper.name)
        else:
            print("There was no image to upload for " + paper.name + ".")


upload_frontpages()


def post_album_on_reddit():
    yesterdays_album_url = "http://www.imgur.com/a/" + imgur.get_account_album_ids("UkPoliticsPapers")[1]
    sources_url = ""
    for paper in Papers:
        if paper.front_page_url is not None and paper.source is not None:
            sources_url += (paper.name + " : " + paper.tweet_link + "  \n")
    global album
    global errors
    post = reddit.subreddit("ukpolitics").submit(title="The Papers (" + today + ")",
                                           url=("http://www.imgur.com/a/" + album["id"]))
    comment = ("Tomorrow's front pages rehosted on Imgur.\n\n" +
               "All from twitter:\n\n" +
               sources_url +
               "[Yesterday's papers](" + yesterdays_album_url + ")\n\n" +
               "---\n"+
               "This post and comment have been created by the PaperboyUK bot, written by Vermoot with help from /u/FordTippex.\n\n"+
               "If you find an error in the album, such as a paper being mislabeled or an image that isn't a newspaper front page, reply to this comment and mention Vermoot so he can see it.\n\n")

    if errors != "":
        comment += "Here are problems PaperboyUK has had today (Hey /u/Vermoot! Get on it!)\n\n"+errors

    reddit.submission(id=post.id).reply(comment)

    print("Posted the album on reddit : "+)

post_album_on_reddit()


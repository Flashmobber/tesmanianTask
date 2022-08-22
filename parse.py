from dataclasses import dataclass
from datetime import datetime
from time import sleep
from urllib.parse import urljoin

import redis
import requests
from bs4 import BeautifulSoup, Tag


@dataclass
class News:
    title: str
    url: str
    author: str
    date: str


BASE_URL = "https://www.tesmanian.com/"
TELEGRAM_URL = "https://api.telegram.org/bot"
TOKEN = "5178301325:AAFXQP3EkdAan6mkDyOAc1ScxbWeM5z00Dg"
CHAT_ID = "-1001485855922"
SECONDS_FOR_NEXT_PARSE = 15
headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:72.0) Gecko/20100101 Firefox/72.0"}


def login():
    login_data = {"form_type": "customer_login",
                  "utf8": "✓",
                  "customer[email]": "****d@gmail.com",
                  "customer[password]": "*****",
                  "return_url": "/account"}
    with requests.Session() as session:
        session.get(BASE_URL)
        url = urljoin(BASE_URL, login_data["return_url"])
        response = session.get(url)

        soup = BeautifulSoup(response.text, "html.parser")
        login_data["recaptcha-token"] = str(
            soup.find("input",
                      attrs={"type": "hidden", "name": "recaptcha-token"})[
                "value"
            ]
        )

        headers["cookie"] = "; ".join(
            [cookie.name + "=" + cookie.value for cookie in session.cookies])

        sleep(1)
        session.post(url, data=login_data, headers=headers)
        print(headers["cookie"])
        print(session.cookies)


def parse_one_news(news_soup: Tag):
    return News(
        title=news_soup.select_one(".sub_title > a").text,
        url=urljoin(BASE_URL, news_soup.select_one(".sub_title > a")["href"]),
        author=news_soup.select_one(".blog_meta > span > a").text.removeprefix(
            "by "),
        date=news_soup.select_one(".blog_meta").findAll("span")[1].text,
    )


def parse_all_news():
    soup = None
    while soup is None:
        try:
            soup = BeautifulSoup(requests.get(BASE_URL, headers).content,
                                 "html.parser")
        except OSError as e:
            print(f"Connection error: {e}. Automatic retry after 5 sec.")
            sleep(5)
    print("Parsed at:", datetime.now())
    return soup.select(
        "div.sixteen.columns.medium-down--one-whole > div.article.clearfix"
    )


def send_fresh_news_to_channel():
    with redis.Redis(host="localhost", port=6379, db=0) as rd:
        while True:
            news_list = parse_all_news()
            start = datetime.now()
            for news in news_list:
                news = parse_one_news(news)
                if rd.get(name=hash(news.title)) is None:
                    rd.set(name=hash(news.title), value=news.title)
                    print(news.title)
                    requests.get(
                        TELEGRAM_URL
                        + TOKEN
                        + "/sendMessage?chat_id="
                        + CHAT_ID
                        + "&text="
                        + f"<a href='{news.url}'>{news.title}</a>"
                          f"\n{news.author} {news.date}" + "&parse_mode=HTML"
                    )

            sleep(15)


send_fresh_news_to_channel()

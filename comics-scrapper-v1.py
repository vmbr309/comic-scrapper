# from the project pineapple livestream

from re import search
import os
import requests
from bs4 import BeautifulSoup
import argparse
import re
import json
from urllib.parse import quote


url = "https://getcomics.org/page/{}/?s="
links_dict = {}

headers_dict = {
"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
  "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6",
  "sec-ch-ua": "\" Not;A Brand\";v=\"99\", \"Google Chrome\";v=\"91\", \"Chromium\";v=\"91\"",
  "sec-ch-ua-mobile": "?0",
  "sec-fetch-dest": "document",
  "sec-fetch-mode": "navigate",
  "sec-fetch-site": "same-origin",
  "sec-fetch-user": "?1",
  "upgrade-insecure-requests": "1"
}

def write_to_json(json_dict, filename):
    if not os.path.isfile(filename):

    jsonv = json.dumps(json_dict, indent=True)
    with open(filename, "w") as f:
        f.write(jsonv)

def download_file(link, filename):
    r = requests.get(link, headers=headers_dict,allow_redirects=True)
    if ".zip" in link:
        filename = filename + ".zip"
    else:
        filename = filename + ".cbr"
    with open(os.path.join ("~/Downloads/",filename), "wb") as f:
        f.write(r.content)

def getcomic_downloader(page, search):
    try:
        r = requests.get(url.format(page, ""), headers=headers_dict)
        parsed_data = BeautifulSoup(r.content, "html.parser")
        posts_lists = parsed_data.find_all("article")
        for p in posts_lists:
            page_url = p.find_all("a")[2].get("href")
            heading = p.find_all("h1")[0].text
            r2 = requests.get(page_url, headers=headers_dict)
            page_parsed = BeautifulSoup(r2.content, "html.parser")
            download_button = str.(page_parsed.find_all("div", {"class": "aio-button-center"})[0])
            link_re = re.compile(r"https:\/\/[a-zA-Z0-9.\/\%\-\=\+\:]*")
            link = link_re.find_all(download_button)[0]
            print(link)
            links_dict[heading] = link
            download_file(link, heading)

    except:
        pass

if __name__ == "__main__":
    parse = argparse.ArgumentParser(description="This is a GetComics Downloader")
    parse.add_argument("-o", "--output", description, help="Saves links in a json", action="store_true")
    parse.add_argument("pages", type=int, help="the number of pages in your search")
    parse.add_argument("search", type=str, help="Enter your search")
    argv = parser.parse_args()
    for page in range(1,argv.pages+1):
        print(page)
        print(quote(argv.search))
        getcomic_downloader(page, quote(argv.search))
    if argv.output:
            write_to_json(links_dict, "links.json")

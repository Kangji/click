from abc import ABCMeta, abstractmethod
import ssl
from typing import Callable, Optional

import urllib.request

import requests

import http.client

import pyautogui
from datetime import datetime, timedelta

protocol = "https"

host = "sugang.snu.ac.kr"
# host = "keyescape.co.kr"

endpoint = "/sugang/cc/cc300.action"
# endpoint = "/web/home.php"
not_found_endpoint = "/dummy"

target_url = protocol + "://" + host + endpoint
not_found_url = protocol + "://" + host + not_found_endpoint


def suppressexception(func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f'[debug] {args[0].__class__.__name__} failed with exception {e.__class__}: {e.__class__.__name__}')
            return None
    
    return wrapper


class TimeFetcherCompare:
    __time_fetchers = dict()

    @classmethod
    def compare(cls):
        measurement = dict()
        num_iter = 10
        for (k, v) in cls.__time_fetchers.items():
            measurement[k] = {
                "min": timedelta(seconds=10),
                "max": timedelta(),
                "sum": timedelta(),
                "succ": 0,
            }
        for i in range(num_iter):
            for (k, v) in cls.__time_fetchers.items():
                tm, success = v.measure_performance()
                measurement[k]["min"] = min(measurement[k]["min"], tm)
                measurement[k]['max'] = max(measurement[k]["max"], tm)
                measurement[k]["sum"] += tm
                if success:
                    measurement[k]["succ"] += 1
                else:
                    print(f"[debug] {k.__name__} failed on iter #{i}")

        for (k, v) in measurement.items():
            print(f'{k.__name__}: sum={v["sum"].total_seconds()}, avg={v["sum"].total_seconds() / num_iter}, min={v["min"].total_seconds()}, max={v["max"].total_seconds()}, succ={v["succ"]}')

    @classmethod
    def add_time_fetcher(cls, time_fetcher):
        if time_fetcher.__class__ not in cls.__time_fetchers:
            cls.__time_fetchers[time_fetcher.__class__] = time_fetcher


class TimeFetcher(metaclass=ABCMeta):
    def __init__(self):
        self._setup()
        TimeFetcherCompare.add_time_fetcher(self)

    @abstractmethod
    def _setup(self):
        pass

    @abstractmethod
    def fetch_raw_time(self) -> Optional[str]:
        pass

    def fetch_utc_now(self) -> Optional[datetime]:
        raw_time_now = self.fetch_raw_time()

        if raw_time_now is None:
            return None
        
        time_now = datetime.strptime(raw_time_now, "%a, %d %b %Y %H:%M:%S %Z")
        return time_now

    def measure_performance(self) -> tuple[timedelta, bool]:
        start = datetime.now()
        now = self.fetch_utc_now()
        end = datetime.now()
        return end - start, False if now is None else True


class UrllibTimeFetcher(TimeFetcher):
    def _setup(self):
        self._context = ssl._create_unverified_context()

    @suppressexception
    def fetch_raw_time(self) -> Optional[str]:
        return urllib.request.urlopen(target_url, context=self._context).headers["Date"]


class RequestsTimeFetcher(TimeFetcher):
    def _setup(self):
        self._session = requests.Session()

    @suppressexception
    def fetch_raw_time(self) -> Optional[str]:
        return self._session.get(not_found_url).headers["Date"]


class HttpClientTimeFetcher(TimeFetcher):
    def _setup(self):
        self._context = ssl._create_unverified_context()
        self._connection = http.client.HTTPSConnection(host, context=self._context)
    
    @suppressexception
    def fetch_raw_time(self) -> Optional[str]:
        try:
            self._connection.request('GET', not_found_endpoint)
            res = self._connection.getresponse()
            res.read()
            return res.headers["Date"]
        except Exception as e:
            self._connection.close()
            self._connection.connect()
            raise e


def get_target_time() -> datetime:
    target_time = input("type target date & time in KST in specific format. ex) 2022-02-10 08:30:00 : ")
    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
    target_time = target_time - timedelta(hours=9)
    return target_time


def click(time_fetcher: TimeFetcher) -> None:
    target_time = get_target_time()
    print(target_time)
    now = time_fetcher.fetch_utc_now()
    while now is None or now < target_time:
        now = time_fetcher.fetch_utc_now()
    pyautogui.click()


if __name__ == "__main__":
    # urllib_time_fetcher = UrllibTimeFetcher()  # too slow
    # requests_time_fetcher = RequestsTimeFetcher()
    http_client_time_fetcher = HttpClientTimeFetcher()

    # click
    click(http_client_time_fetcher)

    # performance measurement
    # TimeFetcherCompare.compare()
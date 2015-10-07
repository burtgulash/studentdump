#!/usr/bin/python3
# -*- coding: utf-8 -*-


from urllib.request import urlopen, HTTPError, URLError
import lxml.html
import threading
import sys
import re
import signal
from queue import Queue


class Selector:

    def __init__(self, *es):
        self.elems = es

    def select(self, xpath_expr):
        return Selector(*[item for e in self.elems for item in e.xpath(xpath_expr)])

    def __iter__(self):
        return iter(Selector(e) for e in self.elems)

    def all(self):
        return self.elems

    def one(self):
        return self.all()[0]



class Bot:

    def __init__(self, n):
        self.jobs = Queue()
        self.output = Queue()
        self.running = True

        self.workers = []
        for i in range(n):
            worker = threading.Thread(target=self.run)
            worker.start()
            self.workers.append(worker)

    def run(self):
        while self.running:
            self.fetch()

    def stop(self):
        self.running = False

    def fetch(self):
        base_url = "http://ovavt.lfp.cuni.cz/user/view.php?id={}"
        url = base_url.format(self.jobs.get())
        result = None

        try:
            html = urlopen(url).read()
        except (HTTPError, URLError) as err:
            print(err, url, file=sys.stderr)
            self.output.put(result)
            return
        except Exception as err:
            print(err, file=sys.stderr)
            self.output.put(result)
            return

        root = Selector(lxml.html.fromstring(html))
        content = root.select("//div[@id='content']")
        h2 = content.select("h2/text()").all()

        if len(h2) == 1:
            result = h2[0]

        self.output.put(result)


def signal_handler(signal, frame):
    print("INTERRUPTED")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    fetcher = Bot(10)
    for id in range(1, 5000):
        fetcher.jobs.put(id)

    for i in range(500):
        result = fetcher.output.get()
        if result:
            print(i, result)


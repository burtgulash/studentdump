#!/usr/bin/python3

"""usage: ./vse_person_dump USERNAME"""

import sys
import os
import getpass
import imghdr
import queue
import urllib.request
import threading
import time


PERSON_URL  = r"https://isis.vse.cz/auth/lide/clovek.pl?id={};lang=cz"
VCARD_URL   = r"https://isis.vse.cz/auth/lide/clovek.pl?export_osoby=1;id={};lang=cz"
PICTURE_URL = r"https://isis.vse.cz/auth/lide/foto.pl?id={};lang=cz"

class Person:

    def __init__(self, _id):
        self._id = _id
        self.full_name = None
        self.first_name  = None
        self.second_name = None
        self.title_before = None
        self.title_after = None
        self.email = None
        self.url   = None
        self.photo = None

        self.failed = False

    def __str__(self):
        return "{} ({})".format(self.full_name, self.email)

    def parse_vcard(self, vcard):
        if vcard:
            for lin in vcard:
                line = lin.decode("iso-8859-2").strip()
                try:
                    key, value = line.split(":", 1)
                    key = key.split(";", 1)[0]

                    if key == "N":
                        value = value.split(";")
                        self.first_name = value[1]
                        self.second_name = value[0]
                        self.title_before = value[3]
                        self.title_after = value[4]
                    elif key == "FN":
                        self.full_name = value
                    elif key == "EMAIL":
                        self.email = value
                    elif key == "URL":
                        self.url = value
                except ValueError:
                    self.failed = True



def fetch_person(person_id):
    # urllib authentication - See first answer:
    # http://stackoverflow.com/questions/395451/how-to-download-a-file-over-http-with-authorization-in-python-3-0-working-aroun
    #
    # or official Py3k docs:
    # https://docs.python.org/3/library/urllib.request.html#examples

    person = Person(person_id)

    try:
        vcard = urllib.request.urlopen(VCARD_URL.format(person_id))
    except IOError as e:
        print(e, file=sys.stderr)
        person.failed = True
        return person

    person.parse_vcard(vcard)

    if not person.failed:
        picname = str(person_id) + ".jpg"
        try:
            urllib.request.urlretrieve(PICTURE_URL.format(person_id), picname)
        except IOError as e:
            print("Error downloading picture:", e, file=sys.stderr)
            picname = None

        if imghdr.what(picname) == "png":
            os.rename(picname, picname.replace(".jpg", ".png", 1))
        person.photo = picname

    return person


def init_urllib(auth_user, auth_passwd):
    auth_handler = urllib.request.HTTPBasicAuthHandler()
    auth_handler.add_password(realm="ISIS VSE",
                  uri="http://isis.vse.cz/",
                       user=auth_user,
                  passwd=auth_passwd)

    opener = urllib.request.build_opener(auth_handler)
    opener.addheaders = [("User-agent", "Mozilla/5.0")]

    urllib.request.install_opener(opener)


def run(job_queue, result):
    while True:
        person_id_job = job_queue.get()
        if person_id_job < 0:
            break

        downloaded_person = fetch_person(person_id_job)
        result.put(downloaded_person)

        # time.sleep(.3)



if __name__ == "__main__":
    example_id = 108510

    try:
        username = sys.argv[1]
        passwd   = getpass.getpass("Password for {}: ".format(username))
    except (IndexError, ValueError):
        print(__doc__)
        sys.exit(1)

    init_urllib(username, passwd)


    job_queue = queue.Queue()
    result_queue = queue.Queue()

    threads = []
    for t_id in range(10):
        t = threading.Thread(target=run, args=(job_queue, result_queue))
        t.start()
        threads += [t]


    from_id = 1
    to_id = 116500
    for person_id in range(from_id, to_id):
        job_queue.put(person_id)

    print("Fetching persons {} to {}...".format(from_id, to_id))

    counter = to_id - from_id
    while counter > 0:
        person = result_queue.get()

        if person.failed:
            print("Failed to download : {}".format(person._id or person), file=sys.stderr)
        else:
            print("Downloaded   :", person._id, person, file=sys.stderr)

        counter -= 1

    print("Processed all {} persons.".format(to_id - from_id))
    for t in range(len(threads)):
        job_queue.put(-1)
    for t in threads:
        t.join()


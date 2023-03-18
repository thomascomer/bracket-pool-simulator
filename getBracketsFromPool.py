from splinter import browser
import splinter
import os
import re


def getBfromP(groupID: str, path="html_sources/", year="2019", entry_limit=40):
    print("Connecting...", end=' ')
    with browser.Browser(headless=True) as b:
        if path == "html_sources/":
            path += groupID + '/'
        print("Connecting...", end=' ')
        myurl = "http://fantasy.espn.com/tournament-challenge-bracket/" + str(year) + "/en/group?groupID=" + groupID + "&_301_=" + str(year)
        b.visit(myurl)
        group_html = b.html_snapshot()
        with open(group_html) as f:
            group_text = f.read()
            try:
                re.search(r"<header class=\"group-header\">.*?</header>", group_text)[0][29:-9] + '/'
            except TypeError:
                raise ValueError("This pool is not publicly accessible, therefore the program cannot run")
        mylinks = []
        links = b.links.find_by_partial_href("entry?entryID=")
        for i, j in enumerate(links):
            mylinks.append(j.value)
        if len(mylinks) > entry_limit:
            raise ValueError("This program is intended for small groups. It is too expensive to visit " + len(mylinks) + " URLs.")
        linkcount = 0
        for i in mylinks:
            linkcount += 1
            if linkcount % 10 == 1:
                print("\nProgress: " + str(linkcount) + '/' + str(len(mylinks)), end=' ')
            else:
                print(str(linkcount) + '/' + str(len(mylinks)), end=' ')
            try:
                b.links.find_by_text(i).click()
                if "game" in b.url:
                    ID = re.search(r"entryID=\d*", b.url)[0]
                    urlBase = "http://fantasy.espn.com/tournament-challenge-bracket/" + str(year) + "/en/entry?"
                    b.visit(urlBase + ID)
                notFound = False
            except splinter.exceptions.ElementDoesNotExist:
                print('\n' + i, "could not be found")
                notFound = True
            screenshot_path = b.html_snapshot()
            with open(screenshot_path) as f1:
                entryName = b.title.split(' -')[0]
                if notFound is True:
                    entryName = i
                entryName = entryName.replace('/', '_')
                try:
                    with open(path + entryName, 'w') as f2:
                        if notFound is False:
                            all_text = f1.read()
                            f2.write(all_text)
                        else:
                            f2.write(i + " could not be found")
                except (FileNotFoundError, NotADirectoryError):
                    try:
                        os.mkdir(path)
                    except (FileNotFoundError, NotADirectoryError):
                        os.mkdir(path.split('/')[0])
                        os.mkdir(path)
                    with open(path + entryName, 'w') as f2:
                        if notFound is False:
                            all_text = f1.read()
                            f2.write(all_text)
                        else:
                            f2.write(i + " could not be found")
            b.visit(myurl)
        print('\n', end='')


if __name__ == "__main__":
    getBfromP("5013")

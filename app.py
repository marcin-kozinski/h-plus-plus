from urllib2 import urlopen
import xml.etree.ElementTree as ET
import re
import jinja2
import os

from webapp2 import RequestHandler, WSGIApplication
from google.appengine.ext import db

jinja_environment = jinja2.Environment(
    loader = jinja2.FileSystemLoader(os.path.dirname(__file__)))

class Episode(db.Model):
    '''
    Model for one episode of the show holding all extra content.
    '''
    number = db.IntegerProperty(required = True)
    title = db.StringProperty()
    url = db.LinkProperty()
    locations = db.ListProperty(unicode)
    photo = db.StringProperty()
    photo_preview = db.StringProperty()
    video = db.LinkProperty()
    text = db.TextProperty()

class RefreshRequestHandler(RequestHandler):
    MAP_DATA_URL = "http://www.hplusdigitalseries.com/xml/MapData.xml"

    def get(self):
        response = urlopen(self.MAP_DATA_URL)
        xml = ET.parse(response)
        episodes = xml.find('episodes')

        title_prefix = re.compile("Episode (?P<number>\d+): (?P<title>.*)")

        number = 0
        for episode in episodes:
            number += 1
            has_aired = episode.find('hasaired').text
            if has_aired != "1":
                continue

            episode_model = Episode.get_or_insert(str(number), number = number)

            title = episode.find('title').text
            match_result = title_prefix.match(title)
            if match_result is not None:
                groups = match_result.groupdict()
                if groups['number'] != str(number):
                    raise Exception("Parsing episode nubmer %d, "
                            "but title suggests %s (%s)"
                            % (number, groups['number'], title))
                episode_model.title = groups['title']
            else:
                episode_model.title = title

            episode_model.url = episode.find('episodeurl').text

            episode_model.locations = [unicode(location.text)
                    for location
                    in episode.find('locations')]

            content = episode.find('content')
            episode_model.photo = content.find('photodownload').text
            episode_model.photo_preview = content.find('photopreview').text
            episode_model.text = content.find('text').text
            episode_model.video = content.find('videourl').text

            episode_model.put()

        self.response.out.write("Refreshed!")


class RootRequestHandler(RequestHandler):
    def get(self):
        episodes = Episode.all().order("number").run()
        template = jinja_environment.get_template("episodes.html")
        self.response.out.write(template.render({"episodes": episodes}))

app = WSGIApplication([
            ('/', RootRequestHandler),
            ('/refresh', RefreshRequestHandler)],
        debug = True)

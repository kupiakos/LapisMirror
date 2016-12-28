# The MIT License (MIT)

# Copyright (c) 2015 kupiakos

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import json
import re
import logging
from urllib.parse import urlencode, urlsplit
import traceback

import mimeparse
import requests
import praw
from bs4 import BeautifulSoup


class DeviantArtPlugin:
    """A deviantArt import plugin.

    Supports GIFs and single images.
    Will try to seek out the best possible image if it can be done.
    Ignores Flash media.
    """

    def __init__(self, useragent: str, **options):
        """Initialize the deviantArt import API.

        :param useragent: The useragent to use for the deviantArt API
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.da')
        self.regex = re.compile(r'^(.*?\.)?((deviantart\.(com|net))|(fav\.me))$')
        self.regex_direct = re.compile(r'^((www\.)|(orig.*\.))?(deviantart\.net)$')
        self.useragent = useragent
        self.headers = {'User-Agent': self.useragent}

    def read_url(self, url: str) -> str:
        """Download text from a URL.

        :param url: The URL to download from.
        :return: The data downloaded, as a Unicode string.
        """
        return requests.get(url, headers=self.headers).text

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """Import a submission from deviantArt. Ignores flash content.

        Uses a combination of the DA backend and HTML scraping.

        This function will define the following values in its return data:
        - author: The author of the image.
        - source: The submission URL.
        - importer_display/header
        - import_urls


        :param submission: A reddit submission to parse.
        :return: None if no import, an import info dictionary otherwise.
        """
        try:
            if self.regex_direct.match(urlsplit(submission.url).netloc):
                r = requests.head(submission.url, headers=self.headers)
                mime_text = r.headers.get('Content-Type')
                mime = mimeparse.parse_mime_type(mime_text)
                if mime[0] == 'image':
                    self.log.debug('DA link is a direct image')
                    data = {'author': 'An unknown DA author',
                            'source': submission.url,
                            'import_urls': [submission.url],
                            'importer_display':
                                {'header': 'Mirrored deviantArt image '
                                           'by an unknown author:\n\n'}}
                    return data
            if not self.regex.match(urlsplit(submission.url).netloc):
                return None
            query_url = 'http://backend.deviantart.com/oembed?{}'.format(
                urlencode({'format': 'json', 'url': submission.url}))
            self.log.debug('%s is valid DA url.', submission.url)
            self.log.debug('Querying DA API %s', query_url)

            response = json.loads(self.read_url(query_url))

            if response['type'] not in ('link', 'photo'):
                self.log.debug('Response is not link or photo')
                return None
            self.log.debug('Author name: %s', response['author_name'])

            # Using the official DA API
            data = {'author': response['author_name'],
                    'source': submission.url,
                    'importer_display':
                        {'header': 'Mirrored deviantArt image by the author "{}":\n\n'.format(
                            response['author_name'])}}
            if response['type'] == 'link':
                data['import_urls'] = [response['fullsize_url']]
                self.log.debug('Found DA API url %s', data['import_urls'])

            try:
                # Trying to scrape manually
                bs = BeautifulSoup(self.read_url(submission.url), "html.parser")

                # Checking for flash animation, because mirroring a preview
                # for a flash animation is stupid
                is_flash = bool(bs.select('iframe[class~=flashtime]'))
                is_madefire = bool(bs.select('iframe[class~=madefire-player]'))
                if is_flash or is_madefire:
                    self.log.info('DA url is flash, no preview needed.')
                    return None
                # Seems to alternate between the two
                full_view = (bs.select('img[class~=fullview]') or
                             bs.select('img[class~=dev-content-full]'))
                if full_view:
                    full_url = full_view[0]['src']
                    self.log.debug('Found full DA image url: %s', full_url)
                    data['import_urls'] = [full_url]
            except Exception as e:
                self.log.error(traceback.format_exc())

            if 'import_urls' not in data:
                self.log.debug('No url found for DA image.')
                return None

            return data

        except Exception as e:
            self.log.error('Deviantart Error: %s', traceback.format_exc())
            return None


__plugin__ = DeviantArtPlugin

# END OF LINE.

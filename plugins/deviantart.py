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
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit

from bs4 import BeautifulSoup


class DeviantArtPlugin:
    def __init__(self, useragent, **options):
        self.log = logging.getLogger('lapis.da')
        self.regex = re.compile(r'^(.*?\.)?((deviantart\.(com|net))|(fav\.me))$')
        self.regex_direct = re.compile(r'^(www\.)?(deviantart\.net)$')
        self.useragent = useragent

    def read_url(self, url):
        r = Request(url, data=None, headers={'User-Agent': self.useragent})
        with urlopen(r) as u:
                return u.read().decode('utf-8')

    def import_submission(self, submission):
        try:
            if self.regex.match(urlsplit(submission.url).netloc):
                r = Request(submission.url,
                            data=None,
                            headers={'User-Agent': self.useragent})
                with urlopen(r) as u:
                    if u.headers['content-type'].startswith('image'):
                        self.log.debug('DA link is a direct image')
                        return submission.url
            if not self.regex.match(urlsplit(submission.url).netloc):
                return None
            query_url = 'http://backend.deviantart.com/oembed?{}'.format(
                urlencode({'format': 'json', 'url': submission.url}))
            self.log.debug('%s is valid DA url.', submission.url)

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
                bs = BeautifulSoup(self.read_url(submission.url))

                # Checking for flash animation, because mirroring a preview
                # for a flash animation is stupid
                is_flash = bool(bs.select('iframe[class~=flashtime]'))
                is_madefire = bool(bs.select('iframe[class~=madefire-player]'))
                if is_flash or is_madefire:
                    self.log.info('DA url is flash, no preview needed.')
                    return None
                full_view = (bs.select('img[class~=fullview]') or
                             bs.select('img[class~=dev-content-full]'))
                if full_view:
                    full_url = full_view[0]['src']
                    self.log.debug('Found full DA image url: %s', full_url)
                    data['import_urls'] = [full_url]
            except Exception as e:
                self.log.error(str(e))

            if 'import_urls' not in data:
                self.log.debug('No url found for DA image.')
                return None

            return data

        except Exception as e:
            self.log.error(str(e))
            return None


__plugin__ = DeviantArtPlugin

# END OF LINE.

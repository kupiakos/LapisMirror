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

import logging
import re
import html
from urllib.parse import urlsplit

import requests
import mimeparse
import bs4
import traceback


class TinypicPlugin:
    def __init__(self, useragent, **options):
        self.log = logging.getLogger('lapis.tinypic')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(r'^(.*?\.)?tinypic\.com$')

    def import_submission(self, submission):
        try:
            url = html.unescape(submission.url)
            if not self.regex.match(urlsplit(url).netloc):
                return None
            data = {'author': 'an anonymous Tinypic user',
                    'source': url,
                    'importer_display':
                        {'header': '~~Liberated~~Mirrored tinypic image:\n\n'}}
            r = requests.head(url, headers=self.headers)
            if r.status_code == 301:  # Moved Permanently
                return None
            mime_text = r.headers.get('Content-Type')
            mime = mimeparse.parse_mime_type(mime_text)
            if mime[0] == 'image':
                image_url = url
            else:
                r = requests.get(url, headers=self.headers)
                bs = bs4.BeautifulSoup(r.content.decode('utf-8'))
                matched = bs.select('div#imgFrame img')
                if not matched:
                    self.log.warning('Could not find locate Tinypic image to scrape.')
                    return None
                image_url = matched[0]['src']
            assert image_url
            data['import_urls'] = [image_url]
            return data
        except Exception:
            self.log.error('Could not import tinypic URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = TinypicPlugin

# END OF LINE.

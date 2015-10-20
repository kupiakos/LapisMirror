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
import traceback

import requests
import mimeparse
import bs4
import praw


class DrawcrowdPlugin:
    """A tiny import plugin for drawcrowd.com
    """

    def __init__(self, useragent: str, **options):
        """Initialize the drawcrowd import API.

        :param useragent: The useragent to use for querying tinypic.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.drawcrowd')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(r'^(.*?\.)?drawcrowd\.com$')

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """Import a submission from drawcrowd. Uses raw HTML scraping.

        As it turns out, drawcrowd likes to provide different data
        (all in <meta> tags) to non-web-browser requests.
        Since it provides enough information anyways, we don't bother getting
        around it and just parse that.

        This function will define the following values in its return data:
        - author: The author of the post
        - source: The url of the submission
        - importer_display/header
        - import_urls

        :param submission: A reddit submission to parse.
        """
        try:
            url = html.unescape(submission.url)
            if not self.regex.match(urlsplit(url).netloc):
                return None
            data = {'source': url}
            r = requests.head(url, headers=self.headers)
            if r.status_code == 301:  # Moved Permanently
                return None
            mime_text = r.headers.get('Content-Type')
            mime = mimeparse.parse_mime_type(mime_text)
            if mime[0] == 'image':
                data['author'] = 'An unknown drawcrowd user'
                image_url = url
            else:
                # Note: Drawcrowd provides different content to non-web-browsers.
                r = requests.get(url, headers=self.headers)
                bs = bs4.BeautifulSoup(r.content.decode('utf-8'))
                matched = bs.find(property='og:image')
                if not matched:
                    self.log.warning('Could not find locate drawcrowd image to scrape.')
                    return None
                image_url = matched['content']
                matched = bs.find(property='og:title')
                if matched:
                    data['author'] = matched['content']
                else:
                    data['author'] = 'an unknown drawcrowd author'
                data['importer_display'] = {'header': 'Mirrored image from {}:\n\n'.format(data['author'])}
            assert image_url
            data['import_urls'] = [image_url]
            return data
        except Exception:
            self.log.error('Could not import drawcrowd URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = DrawcrowdPlugin

# END OF LINE.

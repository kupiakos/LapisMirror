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
import praw


class FourChanPlugin:
    """
    Because 4chan's image host (i.4cdn.org) will take down images
    over time, sometimes quickly, this plugin will mirror from 4chan.
    """

    def __init__(self, useragent: str, **options):
        """Initialize the 4chan import API.

        :param useragent: The useragent to use for querying tinypic.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.4chan')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(r'^i\.4cdn\.org$')

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """Import a submission from 4chan's i.cdn.org.

        Because this downloads the page and tries to scrape the HTML,
        we are at significant risk of the image ID on the DOM changing.
        Therefore, this plugin is liable to break.

        This function will define the following values in its return data:
        - author: simply "an anonymous user on 4chan"
        - source: The url of the submission
        - importer_display/header
        - import_urls

        :param submission: A reddit submission to parse.
        """
        try:
            url = html.unescape(submission.url)
            if not self.regex.match(urlsplit(url).netloc):
                return None
            data = {'author': 'the famed 4chan Anonymous',
                    'source': url,
                    'importer_display':
                        {'header': 'Mirrored 4chan image, as it will inevitably 404:\n\n'}}
            r = requests.head(url, headers=self.headers)
            mime_text = r.headers.get('Content-Type')
            mime = mimeparse.parse_mime_type(mime_text)
            if mime[0] == 'image':
                image_url = url
            else:
                self.log.warning('4chan URL posted that is not an image: %s', submission.url)
                return None
            data['import_urls'] = [image_url]
            return data
        except Exception:
            self.log.error('Could not import 4chan URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = FourChanPlugin

# END OF LINE.

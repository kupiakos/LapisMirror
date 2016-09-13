# The MIT License (MIT)

# Copyright (c) 2016 HeyItsShuga

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

import json
import requests
import mimeparse
import praw


class DerpibooruPlugin:
    """
    Mirrors Derpibooru images.
    Created by /u/HeyItsShuga

    """

    def __init__(self, useragent: str, **options):
        """Initialize the Derpibooru importer.

        :param useragent: The useragent to use for querying derpibooru.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.derpibooru')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(r'(www\.)?(derpiboo\.ru)|(derpibooru\.org)|(trixiebooru\.org)|(derpicdn\.net)$')

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """Import a submission from Derpibooru.

        This function will define the following values in its return data:
        - author: simply "an anonymous user on Derpibooru"
        - source: The url of the submission
        - importer_display/header
        - import_urls

        After we define that, we need to get the image. Since Derpibooru has an API,
        we use that to try to get the image if the image is a non-CDN URL. If it is
        a CDN, we take the image directory and upload *that* to Imgur.

        image_url is the variable of the image to upload.

        :param submission: A reddit submission to parse.
        """
        try:
            url = html.unescape(submission.url)
            if not self.regex.match(urlsplit(url).netloc):
                return None
            r = requests.head(url, headers=self.headers)
            mime_text = r.headers.get('Content-Type')
            mime = mimeparse.parse_mime_type(mime_text)
            # if mime[0] == 'image':
            self.log.debug('Initiating Derpibooru plugin')
            jsonUrl = 'http://derpiboo.ru/oembed.json?url=' + url  # The API endpoint
            callapi = requests.get(jsonUrl)  # Fetch the API's JSON file.
            json = callapi.json()
            img = 'http:' + (json['thumbnail_url'])
            author = (json['author_name'])
            provider_url = (json['provider_url'])
            data = {'author': author,
                    'source': img,
                    'importer_display':
                        {'header': 'Mirrored [image](' + provider_url + ') by Derpibooru artist \
                        [' + author + '](https://derpiboo.ru/tags/artist-colon-' + author + '):\n\n'}}
            image_url = img
            data['import_urls'] = [image_url]
            return data
        except Exception:
            self.log.error('Could not import Derpibooru URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = DerpibooruPlugin

# END OF LINE.

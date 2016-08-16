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

import html
import logging
import re
import traceback
from urllib.parse import urlsplit, urlunsplit

import mimeparse
import praw
import requests


class DerpibooruPlugin:
    """Mirrors Derpibooru images.
    Created by /u/HeyItsShuga

    """

    def __init__(self, useragent: str, **options):
        """Initialize the Derpibooru importer.

        :param useragent: The useragent to use for querying derpibooru.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.derpibooru')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(r'(www\.)?(derpiboo\.ru)|(derpibooru\.org)|(derpicdn\.net)$')

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
            if mime[0] == 'image':
                self.log.debug('Is CDN, no API needed')
                data = {'author': 'a Derpibooru user',
                        'source': url,
                        'importer_display':
                            {'header': 'Mirrored Derpibooru image:\n\n'}}
                image_url = url
            else:
                self.log.debug('Not CDN, will use API')
                # If the URL ends with a slash (/), remove it so the API works properly.
                url = url.rstrip('/')
                # Removes query and fragment from URL.
                urlunsplit(urlsplit(url)[:3] + ('', ''))
                # Use the JSON API endpoint.
                endpoint = url + '.json'
                self.log.debug('Will use API endpoint at ' + endpoint)
                # Use the API endpoint and get the direct image URL to upload.
                call_api = requests.get(endpoint)
                json = call_api.json()
                img = 'http:' + json['image']
                uploader = json['uploader']
                data = {'author': 'a Derpibooru user',
                        'source': url,
                        'importer_display':
                            {'header': 'Mirrored Derpibooru image uploaded by ' +
                                       uploader + ':\n\n'}}
                image_url = img
            data['import_urls'] = [image_url]
            return data
        except Exception:
            self.log.error('Could not import Derpibooru URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = DerpibooruPlugin

# END OF LINE.

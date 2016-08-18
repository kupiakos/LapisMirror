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

import requests
import mimeparse
import praw


class E621Plugin:
    """
    Mirrors e621 images using either their API or using their CDN links.
    Created by /u/HeyItsShuga
    """

    def __init__(self, useragent: str, **options):
        """Initialize the e621 importer.

        :param useragent: The useragent to use for querying e621.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.e621')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(
            r'^https?://(((?:www\.)?(?:static1\.)?'
            r'(?P<service>(e621)|(e926))\.net/(data/.+/(?P<cdn_id>\w+))?'
            r'(post/show/(?P<post_id>\d+)/?)?.*))$')

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """Import a submission from e621.

        This function will define the following values in its return data:
        - author: simply "an anonymous user on e621"
        - source: The url of the submission
        - importer_display/header
        - import_urls

        After we define that, we need to get the image. Since e621 has an
        API, we use that to try to get the image if the image is a non-CDN URL.
        If it is a CDN URL, we take the image directory and upload *that* to
        Imgur.

        image_url is the variable of the image to upload.

        :param submission: A reddit submission to parse.
        """
        try:
            url = html.unescape(submission.url)
            match = self.regex.match(submission.url)
            if not match:
                return None
            r = requests.head(url, headers=self.headers)
            mime_text = r.headers.get('Content-Type')
            mime = mimeparse.parse_mime_type(mime_text)
            if mime[0] == 'image':
                self.log.debug('Using the CDN')
                service = match.group('service')
                data = {'author': 'a e926 user',
                        'source': url,
                        'importer_display':
                            {'header': 'Mirrored ' + service + ' image:\n\n'}}
                image_url = url
            else:
                self.log.debug('Using the e621 API')
                # For non-CDN links, the plugin attempts to get the post_id
                # out of the URL using regex.
                post_id = match.group('post_id')
                service = match.group('service')
                endpoint = 'http://e621.net/post/show.json?id=' + post_id
                self.log.debug('Will use API endpoint at %s', endpoint)
                # We will use the e621 API to get the image URL.
                callapi = requests.get(endpoint)
                json = callapi.json()
                img = json['file_url']
                uploader = json['author']
                data = {'author': uploader,
                        'source': url,
                        'importer_display':
                            {'header': 'Mirrored ' + service + ' image by ' + uploader + ':\n\n'}}
                image_url = img
            data['import_urls'] = [image_url]
            return data
        except Exception:
            self.log.error('Could not import e621 URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = E621Plugin

# END OF LINE.

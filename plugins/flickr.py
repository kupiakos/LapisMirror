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


__author__ = 'Sora Havok'

import re
import logging
import traceback
from urllib.parse import urlsplit
import urllib

import requests
import mimeparse
import praw


class FlickrPlugin:
    """A flickr.com import plugin.

    flickr.com is a site for quickly uploading screen shots.
    """

    def __init__(self, useragent: str, **options):
        """Initialize the flickr import API.

        :param useragent: The useragent to use for querying flickr.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.flickr')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(r'^(.*?\.)?flickr\.com$')

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """ Import a submission from flickr. Uses their oEmbed API.

        flickr.com was nice enough to provide us with an oEmbed API.
        Apparently these guys also support video, so we should also make sure
        to not try to parse that.

        This function will define the following values in its return data:
        - author: simply "a flickr.com user"
        - source: The url of the submission
        - importer_display/header
        - import_urls

        :param submission: A reddit submission to parse.
        """
        try:
            if not self.regex.match(urlsplit(submission.url).netloc):
                return None
            url = submission.url
            data = {'author': 'a flickr.com user',
                    'source': url,
                    'importer_display':
                        {'header': 'Imported flickr.com image:\n\n'}}
            r = requests.head(url, headers=self.headers)
            if r.status_code == 301:
                return None

            mime_text = r.headers.get('Content-Type')
            mime = mimeparse.parse_mime_type(mime_text)
            # If we're already given an image...
            if mime[0] == 'image':
                # Use the already given URL
                image_url = submission.url
            else:
                # Otherwise, find the image in the html
                 self.log.info("Getting submission.url: " + url)
                 html = urllib.request.urlopen(url).read().decode('utf-8')
                 image_urls = re.findall(r'farm[\d]\.[a-z0-9/.\\/_]*', html)
                 if image_urls:
                     image_url = 'http://' + image_urls[-1].replace('\\', '')
                     self.log.info("Got image url %s", image_url)
                 else:
                     self.log.error('Could not find any flickr URL %s', submission.url)
                     return None
                 
            assert image_url
            data['import_urls'] = [image_url]
            return data
        except Exception:
            self.log.error('Could not import flickr URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = FlickrPlugin

# END OF LINE.

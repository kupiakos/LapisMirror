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
import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import traceback
import bs4
import praw


class TumblrPlugin:
    """A Tumblr import plugin.

    Supports single images, multiple images, inline images,
    and GIFs. (with a soft J)
    Does not support videos yet.

    See https://www.tumblr.com/docs/en/api/v2 for information on
    getting Tumblr API keys.
    """

    api_key = None

    def __init__(self, useragent: str, tumblr_api_key: str, **options):
        """Initialize the Tumblr import API.

        :param useragent: The useragent to use for the Tumblr API.
        :param tumblr_api_key: The API key to use for the Tumblr API.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.tumblr')
        self.useragent = useragent
        # Maybe we should be saving and distinguishing between post and image?
        self.regex = re.compile(
            r'^https?://([a-z0-9\-]+\.tumblr\.com)/(?:post|image)/(\d+)(?:/.*)?$',
            re.IGNORECASE)
        self.api_key = tumblr_api_key

    def read_url(self, url: str) -> str:
        """Download text from a URL.

        :param url: The URL to download from.
        :return: The data downloaded, parsed using UTF-8.
        """
        r = Request(url, data=None, headers={'User-Agent': self.useragent})
        with urlopen(r) as u:
            return u.read().decode('utf-8')

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """Import a submission from Tumblr. Does not parse videos yet.

        Uses version 2 of the Tumblr API.

        This function will define the following values in its return data:
        - author: The name of the Tumblr blog.
        - source: The submission URL.
        - importer_display/header
        - import_urls

        :param submission: A reddit submission to parse.
        :return: None if no import, an import info dictionary otherwise.
        """
        try:
            match = self.regex.match(submission.url)
            if not match:
                return None
            blog_name, post_id = match.groups()
            self.log.debug('%s is a valid Tumblr url.', submission.url)
            # Query the Tumblr API directly. The Python wrapper sucks.
            query_url = 'http://api.tumblr.com/v2/blog/{blog_name}/posts?{query}'.format(
                blog_name=blog_name,
                query=urlencode({'filter': 'raw', 'id': post_id, 'api_key': self.api_key}))
            self.log.debug('Querying Tumblr API %s', query_url)
            response = json.loads(self.read_url(query_url))
            data = {'source': submission.url, 'importer_display': {}}
            # response['response']['blog']['title']
            # response['response']['posts'][0]['photos'][i]['original_size']['url']

            if not response:
                self.log.error('No response returned')
                return None
            elif response['meta']['status'] != 200:
                self.log.error('Non-success status returned')

            data['author'] = response['response']['blog']['title']
            data['importer_display']['header'] = \
                'Mirrored post from the tumblr blog "{}":\n\n'.format(data['author'])

            # In the cases of a video, the post object will not have a photos entry.
            # We should silently fail.
            data['import_urls'] = [photo['original_size']['url']
                                   for photo in
                                   response['response']['posts'][0].get('photos', [])]

            # There are strange cases in which the URLs will not be provided by the Tumblr
            # API, but it will still return the HTML body that contains the links.
            # I *think* this happens when there are inline pictures. *shrugs*
            if not data['import_urls']:
                bs = bs4.BeautifulSoup(response['response']['posts'][0].get('body'))
                data['import_urls'] = [img['src'] for img in bs.select('img')]
                if not data['import_urls']:
                    return None
            return data

        except Exception:
            self.log.error(traceback.format_exc())
            return None


__plugin__ = TumblrPlugin

# END OF LINE.

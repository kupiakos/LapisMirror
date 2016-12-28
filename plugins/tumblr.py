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
from urllib.parse import urlencode
import traceback

import bs4
import praw
import requests


class TumblrPlugin:
    """A Tumblr import plugin.

    Supports single images, multiple images, inline images,
    and GIFs. (with a soft J)
    Now with video support!

    See https://www.tumblr.com/docs/en/api/v2 for information on
    getting Tumblr API keys.
    """

    api_key = None

    def __init__(self, useragent: str, tumblr_api_key: str='', **options):
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
        self.headers = {'User-Agent': self.useragent}

    def read_url(self, url: str) -> str:
        """Download text from a URL.

        :param url: The URL to download from.
        :return: The data downloaded, as a Unicode string.
        """
        return requests.get(url, headers=self.headers).text

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
        if not self.api_key:
            return None
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

            video_url = response['response']['posts'][0].get('video_url')
            if video_url:
                data['video'] = True
                data['import_urls'] = [video_url]
                return data

            post = response['response']['posts'][0]
            data['import_urls'] = [photo['original_size']['url']
                                   for photo in
                                   post.get('photos', [])]

            # In the case that the author opts to just do a text post with inline images,
            # we can capture that as well. Sometimes authors do this without even knowing.
            # However, we may capture extraneous images. I've opted to let this happen
            # anyways. [](#su-dealwithit)
            if not data['import_urls']:
                if 'body' in post:
                    html = post['body']
                elif 'answer' in post:
                    html = post['answer']
                    if 'question' in post:
                        data['importer_display']['header'] += (
                            'Question from the post:  \n{}\n\n'.format(post['question'])
                        )
                else:
                    self.log.warning('Unknown post format!')
                    return None
                bs = bs4.BeautifulSoup(html)
                data['import_urls'] = [img['src'] for img in bs.select('img')]
                if not data['import_urls']:
                    self.log.info('Could not find any URLs to import!')
                    return None
            else:
                try:
                    # It is not uncommon for certain blog posts with many images
                    # to exceed the technical Tumblr maximum of 10 images in a photoset.
                    # They usually do this by inserting inline images into their caption.
                    # This scans the caption's HTML and extracts non-duplicated images.
                    # It's already been downloaded anyways.
                    # In the case that an extra images is copied, no harm no foul;
                    # it's better for more data to be captured than less.
                    bs = bs4.BeautifulSoup(response['response']['posts'][0].get(
                        'caption', ''))
                    other_urls = [img['src']
                                  for img in bs.find_all('img')
                                  if img['src'] not in data['import_urls']]
                    self.log.debug('Found %d additional images in the caption',
                                   len(other_urls))
                    data['import_urls'].extend(other_urls)
                except Exception:
                    self.log.warning('Ran into problem finding additional URLs: %s',
                                     traceback.format_exc())
            return data

        except Exception:
            self.log.error('Error in tumlbr: %s', traceback.format_exc())
            return None


__plugin__ = TumblrPlugin

# END OF LINE.

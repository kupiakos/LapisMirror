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
import traceback
import re

import tweepy
import praw


class TwitterPlugin:
    """An Twitter import plugin.

    Imports images posted on Twitter.
    """
    client = None
    auth = None

    def __init__(self,
                 twitter_api_key: str='',
                 twitter_api_secret: str='',
                 twitter_access_token: str='',
                 twitter_access_token_secret: str='',
                 **options):
        """Initialize the Twitter Import Plugin.

        :param twitter_api_key: The API key to connect to Twitter with.
        :param twitter_api_secret: The API secret to connect to Twitter with.
        :param twitter_access_token: The Access Token to use.
        :param twitter_access_token_secret: The Access Token Secret to use.
        :param options: Other options passed. Ignored.
        """
        self.log = logging.getLogger('lapis.twitter')
        self.api_key = twitter_api_key
        self.api_secret = twitter_api_secret
        self.access_token = twitter_access_token
        self.access_token_secret = twitter_access_token_secret
        self.regex = re.compile(
            r'https?://(mobile\.)?twitter.com/(?P<user>\w+?)/status/(?P<id>\d+)/?')

    def login(self):
        """Attempt to log into the Twitter API."""
        self.log.info('Logging into Twitter...')
        self.auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
        self.auth.set_access_token(self.access_token, self.access_token_secret)
        self.client = tweepy.API(self.auth)

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """Import a submission from Twitter. Uses the Twitter API 1.1.

        This function will define the following values in its return data:
        - author: a note containing the Twitter user and their handle
        - source: The url of the submission
        - importer_display/header
        - import_urls

        :param submission: A reddit submission to parse.
        """
        if not self.client:
            return None
        try:
            match = self.regex.match(submission.url)
            if not match:
                return None

            status = self.client.get_status(id=int(match.groupdict()['id']))
            author = status.author.name
            handle = status.author.screen_name
            body = status.text

            image_urls = []
            for medium in status.entities['media']:
                if medium['type'] != 'photo':
                    continue
                url_base = medium['media_url']
                # Find the largest size available
                size = max(medium['sizes'],
                           key=lambda x: medium['sizes'][x]['w'])
                url = '{}:{}'.format(url_base, size)
                image_urls.append(url)

            data = {'author': 'the Twitter user {0} (@{1})'.format(author, handle),
                    'source': submission.url,
                    'importer_display': {
                        'header': 'Mirrored Twitter image from {0} (@{1}):\n\n'.format(
                            author, handle)},
                    # For some reason, Reddit is marking posts as spam with this enabled
                        # 'footer': 'Body:  \n{}'.format(body)},
                    'import_urls': image_urls}

            return data
        except Exception:
            self.log.error('Could not import twitter URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = TwitterPlugin

# END OF LINE.

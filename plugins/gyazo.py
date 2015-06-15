__author__ = 'kevin'

import re
import logging
import traceback
from urllib.parse import urlsplit

import requests
import mimeparse
import praw


class GyazoPlugin:
    """A gyazo.com import plugin.

    gyazo.com is a site for quickly uploading screen shots.
    """

    def __init__(self, useragent: str, **options):
        """Initialize the gyazo import API.

        :param useragent: The useragent to use for querying gyazo.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.gyazo')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(r'^(.*?\.)?gyazo\.com$')

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """ Import a submission from gyazo. Uses their oEmbed API.

        gyazo.com was nice enough to provide us with an oEmbed API.
        Apparently these guys also support video, so we should also make sure
        to not try to parse that.

        This function will define the following values in its return data:
        - author: simply "a gyazo.com user"
        - source: The url of the submission
        - importer_display/header
        - import_urls

        :param submission: A reddit submission to parse.
        """
        try:
            if not self.regex.match(urlsplit(submission.url).netloc):
                return None
            data = {'author': 'a gyazo.com user',
                    'source': submission.url,
                    'importer_display':
                        {'header': 'Imported gyazo.com image:\n\n'}}
            r = requests.head(submission.url, headers=self.headers)
            if r.status_code == 301:
                return None

            mime_text = r.headers.get('Content-Type')
            mime = mimeparse.parse_mime_type(mime_text)
            # If we're already given an image...
            if mime[0] == 'image':
                # Use the already given URL
                image_url = submission.url
            else:
                # Otherwise, use the gyazo oEmbed API.
                response = requests.get(
                    'https://api.gyazo.com/api/oembed/',
                    {'url': submission.url},
                    headers=self.headers).json()
                if response.get('type') == 'photo':
                    image_url = response.get('url')
                else:
                    # This is something that is not a photo. Do not scrape.
                    return None

            assert image_url
            data['import_urls'] = [image_url]
            return data
        except Exception:
            self.log.error('Could not import gyazo URL %s (%s)',
                           submission.url, traceback.format_exc())
            return None


__plugin__ = GyazoPlugin

# END OF LINE.

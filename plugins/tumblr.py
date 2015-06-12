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


class TumblrPlugin:
    api_key = None

    def __init__(self, useragent, tumblr_api_key, **options):
        self.log = logging.getLogger('lapis.tumblr')
        self.useragent = useragent
        self.regex = re.compile(
            r'^https?://([a-z0-9\-]+\.tumblr\.com)/(?:post|image)/(\d+)(?:/.*)?$',
            re.IGNORECASE)
        self.api_key = tumblr_api_key

    def read_url(self, url):
        r = Request(url, data=None, headers={'User-Agent': self.useragent})
        with urlopen(r) as u:
            return u.read().decode('utf-8')

    def import_submission(self, submission):
        try:
            match = self.regex.match(submission.url)
            if not match:
                return None
            blog_name, post_id = match.groups()
            self.log.debug('%s is a valid Tumblr url.', submission.url)
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
            data['import_urls'] = [photo['original_size']['url']
                                   for photo in
                                   response['response']['posts'][0].get('photos', [])]
            return data

        except Exception:
            self.log.error(traceback.format_exc())
            return None


__plugin__ = TumblrPlugin

# END OF LINE.

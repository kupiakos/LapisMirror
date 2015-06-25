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

import requests
import mimeparse


class RawVideoPlugin:
    """An export plugin that only tries to post the raw source of a video.
    """

    def __init__(self, useragent: str, **options):
        """ This plugin requires no initialization other than useragent.

        :param useragent: The useragent to use to perform HTTP HEAD requests.
        :param options:
        :return:
        """
        self.log = logging.getLogger('lapis.rawvideo')
        self.useragent = useragent
        self.headers = {'User-Agent': self.useragent}

    def export_submission(self,
                          import_urls: list,
                          video: bool=False,
                          **import_info) -> dict:
        """Check if something reported as a video is a raw video, then
        post the direct link if it is.

        This function will define the following values in the export data:
        - link_display

        :param import_urls: A set (of one?) of links to videos.
        :param video: Whether the imported data is a video or not.
        :param import_info: Other importing information passed. Ignored.
        :return: None if no export, an export info dictionary otherwise.
        """
        if not video:
            return None
        self.log.debug('Attempting to upload raw video URL.')
        links = []
        for url in import_urls:
            req = requests.head(url, headers=self.headers)
            if not req.ok:
                self.log.debug('URL %s was not valid.', url)
                continue
            try:
                mime_text = req.headers.get('Content-Type')
                mime = mimeparse.parse_mime_type(mime_text)
            except Exception:
                self.log.debug('Error parsing MIME for URL %s', url)
                continue
            if mime[0] != 'video':
                self.log.debug('URL %s is not a video!', url)
                continue
            links.append('[Direct video](%s)  \n' % url)
        if not links:
            self.log.info('No direct video links found!')
            return None
        return {'link_display': ''.join(links)}

__plugin__ = RawVideoPlugin

# END OF LINE.

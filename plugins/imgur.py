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
import urllib.request
import urllib.error
import traceback

import imgurpython
from imgurpython.helpers.error import ImgurClientRateLimitError


class ImgurPlugin:
    """An Imgur export plugin. This is where the real magic happens.

    Will upload single images and albums of images, animated or not.
    See https://api.imgur.com/oauth2/addclient for information on
    getting Imgur API keys.
    """
    client = None

    def __init__(self, useragent: str, imgur_app_id: str='',
                 imgur_app_secret: str='', reddit_user: str='', **options):
        """Initialize the Imgur export API.

        :param useragent: The useragent to use for the Imgur API.
        :param imgur_app_id: The app id to use for the Imgur API.
        :param imgur_app_secret: The app secret to use for the Imgur API.
        :param options: Other passed options. Unused.
        """
        self.log = logging.getLogger('lapis.imgur')
        self.useragent = useragent
        self.app_id = imgur_app_id
        self.app_secret = imgur_app_secret
        self.username = reddit_user

    def login(self):
        """Attempt to log into the Imgur API."""
        self.log.info('Logging into imgur...')
        self.client = imgurpython.ImgurClient(
            self.app_id, self.app_secret)

    def export_submission(self,
                          import_urls: list,
                          author: str='an Unknown Author',
                          source: str='an Unknown Source',
                          video: bool=False,
                          **import_info) -> dict:
        """Upload one or multiple images to Imgur. Cannot support videos.

        Uses the imgurpython library.

        This function will define the following values in the export data:
        - exporter
        - link_display

        :param import_urls: A set of direct links to images to upload.
        :param author: The author to note in the description.
        :param source: The source to note in the description.
        :param video: Whether the imported data is a video or not.
        :param import_info: Other importing information passed. Ignored.
        :return: None if no export, an export info dictionary otherwise.
        """
        # imgur does not support videos.
        if not self.client:
            return None
        if video:
            return None
        description = ('This is a mirror uploaded by /u/%s, '
                       'originally made by %s, located at %s' %
                       (self.username, author, source))
        results = {'exporter': self.__class__.__name__}
        config = {}
        album = {}
        image = {}

        # Should we do an album?
        if len(import_urls) == 0:
            self.log.warning('An import gave no urls.')
            return None
        elif len(import_urls) == 1:
            self.log.debug('A single image will be uploaded.')
            is_album = False
            config['description'] = description
        else:
            self.log.debug('An album will be uploaded.')
            try:
                album = self.client.create_album({'description': description})
            except ImgurClientRateLimitError:
                self.log.error('Ran into imgur rate limit!')
                return None
            except Exception:
                self.log.error('Could not create album! %s', traceback.format_exc())
                return None
            config['album'] = album['deletehash']
            is_album = True

        try:
            # Try to upload each image given.
            images = []
            try:
                for import_url in import_urls:
                    self.log.debug('Uploading URL "%s" to imgur', import_url)
                    image = self.client.upload_from_url(import_url, config)
                    self.log.debug('Uploaded image: %s', str(image))
                    images.append(image)
                if is_album:
                    results['link_display'] = '[Imgur Album](https://imgur.com/a/%s)  \n' % album['id']
                else:
                    results['link_display'] = '[Imgur](%s)  \n' % images[0]['link'].replace('http', 'https')
            except ImgurClientRateLimitError:
                self.log.error('Ran into imgur rate limit!')
                return None
            except Exception:
                # If we fail, we have to try to clean up what we've already uploaded.
                self.log.error('Error uploading! Will attempt to delete uploaded images.\n%s',
                               traceback.format_exc())
                for image in images:
                    if not self.delete_export(image['deletehash']):
                        self.log.error('Could not delete image %s, %s',
                                       image['url'], image['deletehash'])
                if is_album:
                    self.log.error('Deleting album')
                    if not self.delete_export(album['deletehash']):
                        self.log.error('Could not delete album %s,%s',
                                       image['id'], image['deletehash'])
        except ImgurClientRateLimitError:
            self.log.error('Ran into imgur rate limit!')
            return None
        except Exception:
            self.log.error('Broken exception catch %s', traceback.format_exc())
            if is_album:
                self.log.error('Try to delete album!')
                self.delete_export(album['deletehash'])
        return results

    @staticmethod
    def delete_export(delete_info: str) -> bool:
        """Will delete an export if given the image deletehash"""
        try:
            urllib.request.urlopen('http://api.imgur.com/2/delete/' + delete_info)
        except urllib.error.URLError:
            return False
        return True


__plugin__ = ImgurPlugin

# END OF LINE.

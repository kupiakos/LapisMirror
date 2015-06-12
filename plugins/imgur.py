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


class ImgurPlugin:
    def __init__(self, useragent, imgur_app_id, imgur_app_secret, **options):
        self.log = logging.getLogger('lapis.imgur')
        self.useragent = useragent
        self.client = imgurpython.ImgurClient(imgur_app_id, imgur_app_secret)

    def export_submission(self,
                          import_urls,
                          author='an Unknown Author',
                          source='an Unknown Source',
                          **options):
        description = ('This is a mirror uploaded by LapisMirror, '
                       'originally made by %s, located at %s' %
                       (author, source))
        results = {'exporter': 'ImgurPlugin'}
        config = {}
        album = {}
        image = {}

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
            except Exception:
                self.log.error('Could not create album! %s', traceback.format_exc())
                return None
            config['album'] = album['deletehash']
            is_album = True

        try:
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
            except Exception:
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
        except Exception:
            self.log.error('Broken exception catch %s', traceback.format_exc())
            if is_album:
                self.log.error('Try to delete album!')
                self.delete_export(album['deletehash'])

        return results

    @staticmethod
    def delete_export(delete_info):
        try:
            urllib.request.urlopen('http://api.imgur.com/2/delete/' + delete_info)
        except urllib.error.URLError:
            return False
        return True


__plugin__ = ImgurPlugin

# END OF LINE.

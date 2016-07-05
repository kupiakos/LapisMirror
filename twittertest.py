import tweepy
auth = tweepy.OAuthHandler('vcH4lCZHqVYGu55bHzkLE0OHO', 'ZTtTaSVVsR9wDVrgLYfjYC4K6VI4LGXa5ChjiNM1c4Heiy7w5r')
auth.set_access_token('586141708-bNzYqO97PjsqhYocn8cOAFD3lbJ7D1WHBBcjQKFi', 'lJu2jE93gvQJVZ2t4N4m2GklOhWxOKRCGAGv2MkjHTByu')
api = tweepy.API(auth)
status = api.get_status(735195779229306880)

image_urls = []
#print(status.entities['media'])
for medium in status.entities['media']:
    print(medium)
    if medium['type'] != 'photo':
        continue
    url_base = medium['media_url']
    print(url_base)
    size = max(medium['sizes'],
        key=lambda x: medium['sizes'][x]['w'])
    url = '{}:{}'.format(url_base, size)
    image_urls.append(url)
print(image_urls)
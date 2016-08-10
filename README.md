# Lapis Lazuli Mirroring System
_Lapis Lazuli's Mirror didn't disappear; it just ascended into cyberspace._

LapisMirror is a plugin-based service that imports posted images on a specific subreddit,
exports the images onto a mirroring service, then replies with the mirror links.

Currently, Lapis Mirror imports from the following sites:
* Tumblr (images, photosets, and videos)
* deviantArt
* tinypic
* gyazo
* i.4cdn.org (4chan image hosting)
* Twitter Images
* Artstation
* Drawcrowd
* gifs.com
* puu.sh
* flickr
* FurAffinity

It also exports to the following sites:
* imgur for images
* vid.me for videos (in addition to a direct link to the video)

Lapis Mirror imports modules from a plugin directory dynamically and loads them.
I would recommend reading the class documentation in lapis.py to learn more.

To configure for testing, copy lapis.conf.example to lapis.conf and begin editing.
lapis.conf is the location for all configuration settings for Lapis.

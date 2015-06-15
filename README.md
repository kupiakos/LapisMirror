# Lapis Lazuli Mirroring System
_Lapis Lazuli's Mirror didn't disappear; it just ascended into cyberspace._

LapisMirror is a plugin-based service that imports posted images on a specific subreddit,
exports the images onto a mirroring service, then replies with the mirror links.

Currently, Lapis Mirror imports from the following sites:
* Tumblr
* deviantArt
* tinypic
* gyazo

It also exports to the following sites:
* imgur

Lapis Mirror imports modules from a plugin directory dynamically and loads them.
I would recommend reading the class documentation in lapis.py to learn more.

To configure for testing, copy lapis.conf.example to lapis.conf and begin editing.
lapis.conf is the location for all configuration settings for Lapis.

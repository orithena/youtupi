#!/usr/bin/python
# -*- coding: utf-8 -*-

import web
import os
import signal
import sys
import subprocess
import json
from StringIO import StringIO

urls = (
	'/(.*)/', 'redirect',
	'/playlist', 'playlist',
	'/control/(.*)', 'control',
	'/', 'index'
)
app = web.application(urls, globals())

player = None
videos = list()

class Video:
	def __init__(self, vid, data, url):
		self.vid = vid
		self.data = data
		self.url = url
		self.played = False

class redirect:
	def GET(self, path):
		web.seeother('/' + path)

class index:
	def GET(self):
		web.seeother('/static/youtupi.html')

# curl -i -X POST -d '{"id": "M8GrahQw4zw", "type": "youtube", "format": "18"}' http://192.168.1.2:8080/playlist 
class playlist:
	def GET(self):
		removeOldVideosFromPlaylist()
		autoPlay()
		playlistVideos = list()
		for video in videos:
			playlistVideos.append(video.data)
		
		return json.dumps(playlistVideos, indent=4)
	
	def POST(self):
		data = json.load(StringIO(web.data()))
		if not isVideoOnPlaylist(data['id']):
			if(data['type'] == "youtube"):
				url = getYoutubeUrl(data['id'], data['format'])
				video = Video(data['id'], data, url)
				videos.append(video)
		
		web.seeother('/playlist')
		
	def DELETE(self):
		global videos
		videos = list()
		web.seeother('/playlist')

def isVideoOnPlaylist(vid):
	for video in videos:
		if video.vid == vid:
			return True
	return False

def removeOldVideosFromPlaylist():
	global videos
	viewedVideos = filter(lambda video:video.played==True, videos)
	if isProcessRunning(player):
		for vv in viewedVideos[:-1]:
			videos.remove(vv)
	else:
		for vv in viewedVideos:
			videos.remove(vv)

def removeVideoFromPlaylist(vid):
	global videos
	videos = filter(lambda video:video.vid!=vid, videos)

def playNextVideo():
	global player
	if isProcessRunning(player):
		os.killpg(player.pid, signal.SIGTERM)
	for video in videos:
		if not video.played:
			player = subprocess.Popen(['omxplayer', '-ohdmi', video.url], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, preexec_fn=os.setsid)
			video.played = True
			break

def autoPlay():
	if (not isProcessRunning(player)) and (len(videos) > 0):
		playNextVideo()

class control:
	def GET(self, action):
		if action == "play":
			playNextVideo()
		else:
			if isProcessRunning(player):
				if action == "stop":
					global player
					player.stdin.write("q")
					player = None
				if action == "pause":
					player.stdin.write("p")
				if action == "volup":
					player.stdin.write("+")
				if action == "voldown":
					player.stdin.write("-")
				if action == "forward":
					player.stdin.write("\x1B[C")
				if action == "backward":
					player.stdin.write("\x1B[D")
		web.seeother('/playlist')

def isProcessRunning(process):
	if process:
		if process.poll() == None:
			return True
	return False

def getYoutubeUrl(video, vformat = None):
	url = "http://www.youtube.com/watch?v=" + video
	if not vformat: 
		args = ['youtube-dl', '-g', url]
	else:
		args = ['youtube-dl', '-f', vformat, '-g', url]
	
	yt_dl = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	(url, err) = yt_dl.communicate()
	if yt_dl.returncode != 0:
		sys.stderr.write(err)
		raise RuntimeError('Error getting URL.')
		
	return url.decode('UTF-8').strip()

if __name__ == "__main__":
	app.run()

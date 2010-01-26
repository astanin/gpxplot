#!/usr/bin/env python
# vim: set fileencoding=utf-8 noexpandtab ts=4 sw=4 :

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.runtime.apiproxy_errors import OverQuotaError

from django.utils import simplejson as json

import urllib2
import logging

from gpxplot import parse_gpx_data,google_chart_url,var_dist,var_ele

max_gpx_size = 1048576

class GPXSizeError (Exception):
	pass

class NoAltitudeData (Exception):
    pass

def plot_on_request(request):
	"Process POST request with GPX data. Return a URL of the plot."
	imperial=request.get('imperial')
	if imperial == 'on':
		metric=False
	else:
		metric=True
	logging.debug('metric='+str(metric))
	try:
		url=request.get("gpxurl")
		if url: # fetch GPX data
			logging.debug('fetching GPX from '+url)
			reader=urllib2.urlopen(url)
			gpxsize = int(reader.headers["Content-Length"])
			logging.debug('gpxsize=%d' % gpxsize)
			if gpxsize > max_gpx_size:
				raise GPXSizeError("File is too large")
			gpxdata=reader.read()
		else:
			logging.debug('using submitted GPX data')
			gpxdata=request.get("gpxfile")
			gpxsize=len(gpxdata)
			logging.debug('gpxsize=%d' % gpxsize)
			if gpxsize > max_gpx_size:
				raise GPXSizeError("File is too large")
		logging.debug('gpxdata='+gpxdata[:320])
	except Exception, e:
		logging.debug(unicode(e))
		raise e
	if len(gpxdata) == 0:
		raise Exception("There is no GPX data to plot!")
	# reduce number of points gradually, to fit URL length
	npoints=700
	url=None
	while not url:
		try:
			trk=parse_gpx_data(gpxdata,npoints=npoints)
			y=var_ele
			max_ele=max([max([p[y] for p in s]) for s in trk if len(s) > 0])
			min_ele=min([min([p[y] for p in s]) for s in trk if len(s) > 0])
			if abs(max_ele) < 1e-3 and abs(min_ele) < 1e-3:
				msg = 'File does not contain altitude data ' \
						+ 'or it is flat sea level. Nothing to plot.'
				raise NoAltitudeData(msg)
			url=google_chart_url(trk,var_dist,var_ele,metric=metric)
		except OverflowError, e:
			npoints -= 100
			if npoints <= 0:
				raise e
	return url

class MainPage(webapp.RequestHandler):
	def get(self):
		content={'title':'Visualize GPX profile online',
				'form':True,'bg':'#efefff'}
		self.response.out.write(template.render('index.html',content))

	def post(self):
		content={'title':'Elevation–distance profile','form':False, 'bg':'#fff'}
		try:
			url=plot_on_request(self.request)
			content['imgsrc']=url
		except GPXSizeError, e:
			msg = 'File is too large to be processed on gpxplot.appspot.com. ' + \
				  '<br/>Reduce file size with gpsbabel or plot it offline with a ' + \
				  'stand-alone version of gpxplot.'
			content['error'] = msg
			logging.error(e)
		except NoAltitudeData, e:
			content['error'] = e.message
			logging.error(e)
		except OverQuotaError, e:
			msg = 'Application exceeded free quota. Try again later.'
			content['error'] = msg
			logging.error(e)
		except Exception, e:
			msg = 'Your GPX track cannot be processed. Sorry.'
			msg += '<br/>'+unicode(e)
			content['error'] = msg
			content['bugreportme'] = True
			logging.error(e)
		self.response.out.write(template.render('index.html',content))

class ApiHandler(webapp.RequestHandler):
	"Return a URL of the image in a file."
	def get(self):
		return self.post()
	def post(self):
		try:
			url=plot_on_request(self.request)
			format=self.request.get("output","json")
			if format == "json":
				self.response.headers['Content-Type']='application/json'
				self.response.out.write(json.dumps({'url':url}))
			elif format == "png":
				self.redirect(url)
			else:
				raise Exception("Output format not supported.")
		except Exception, e:
			self.response.set_status(400,message='Exception: '+unicode(e))

application = webapp.WSGIApplication(
		 [('/', MainPage),
		  (r'/api/0.1/plot',ApiHandler),
		  (r'/api/0.1.1/plot',ApiHandler),
		  (r'/api/0.1.2/plot',ApiHandler),
		 ], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()

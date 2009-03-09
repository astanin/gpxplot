#!/usr/bin/env python
# vim: set fileencoding=utf-8 ts=4 sw=4:

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

import logging

from gpxplot import parse_gpx_data,google_chart_url,var_dist,var_ele

class MainPage(webapp.RequestHandler):
	def get(self):
		content={'title':'Visualize GPX profile online',
				'form':True,'bg':'#efefff'}
		self.response.out.write(template.render('index.html',content))

	def post(self):
		content={'title':'Elevation–distance profile','form':False, 'bg':'#fff'}
		try:
			imperial=self.request.get('imperial')
			if imperial == 'on':
				metric=False
			else:
				metric=True
			gpxdata=self.request.get("gpxfile")
			# reduce number of points gradually, to fit URL length
			npoints=800
			url=None
			while not url:
				try:
					trk=parse_gpx_data(gpxdata,npoints=npoints)
					url=google_chart_url(trk,var_dist,var_ele,metric=metric)
				except OverflowError, e:
					npoints -= 100
					if npoints <= 0:
						raise e
			content['imgsrc']=url
		except Exception, e:
			msg = 'Your GPX track cannot be processed. Sorry :-('
			msg += '<br/>Exception: '+unicode(e)
			content['error'] = msg
			logging.error('Exception: '+unicode(e))
		self.response.out.write(template.render('index.html',content))

application = webapp.WSGIApplication(
		 [('/', MainPage)],
		 debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()

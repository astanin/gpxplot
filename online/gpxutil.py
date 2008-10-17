#!/usr/bin/env python
# vim: set fileencoding=utf8 ts=4 sw=4:

# (c) Sergey Astanin <s.astanin@gmail.com> 2008

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import datetime
from string import join
from math import sqrt,sin,cos,asin,pi,ceil

import logging
debug=logging.debug

NS='{http://www.topografix.com/GPX/1/0}'
dateformat='%Y-%m-%dT%H:%M:%SZ'

R=6371.0008 # Earth volumetric radius
milesperkm=0.621371192
feetperm=3.2808399

strptime=datetime.datetime.strptime

var_time=2
var_ele=3
var_dist=4
var_vel=5

var_names={ 't': var_time,
			'time': var_time,
			'd': var_dist,
			'dist': var_dist,
			'distance': var_dist,
			'ele': var_ele,
			'elevation': var_ele,
			'a': var_ele,
			'alt': var_ele,
			'altitude': var_ele,
			'v': var_vel,
			'vel': var_vel,
			'velocity': var_vel,
			}

EXIT_EOPTION=1
EXIT_EDEPENDENCY=2
EXIT_EFORMAT=3

def haversin(theta):
	return sin(0.5*theta)**2

def distance(p1,p2):
	lat1,lon1=[a*pi/180.0 for a in p1]
	lat2,lon2=[a*pi/180.0 for a in p2]
	deltalat=lat2-lat1
	deltalon=lon2-lon1
	h=haversin(deltalat)+cos(lat1)*cos(lat2)*haversin(deltalon)
	dist=2*R*asin(sqrt(h))
	return dist

def read_all_segments(trksegs,tzname=None):
	trk=[]
	for seg in trksegs:
		s=[]
		prev_lat,prev_lon,prev_time=None,None,None
		trkpts=seg.findall(NS+'trkpt')
		for pt in trkpts:
			lat=float(pt.attrib['lat'])
			lon=float(pt.attrib['lon'])
			time=pt.findtext(NS+'time')
			if time:
				time=strptime(time,dateformat)
				#if tzname:
				#	time=time.replace(tzinfo=pytz.utc)
				#	time=time.astimezone(pytz.timezone(tzname))
			ele=pt.findtext(NS+'ele')
			if ele: ele=float(ele)
			s.append([lat, lon, time, ele])
		trk.append(s)
	return trk

def reduce_points(trk,npoints=None):
	count=sum([len(s) for s in trk])
	if npoints:
		ptperpt=1.0*count/npoints
	else:
		ptperpt=1.0
	skip=int(ceil(ptperpt))
	debug('ptperpt=%f skip=%d'%(ptperpt,skip))
	newtrk=[]
	for seg in trk:
		if len(seg) > 0:
			newseg=seg[:-1:skip]+[seg[-1]]
			newtrk.append(newseg)
	debug('original: %d pts, filtered: %d pts'%\
			(count,sum([len(s) for s in newtrk])))
	return newtrk

def eval_dist_velocity(trk):
	dist=0.0
	newtrk=[]
	for seg in trk:
		if len(seg)>0:
			newseg=[]
			prev_lat,prev_lon,prev_time,prev_ele=None,None,None,None
			for pt in seg:
				lat,lon,time,ele=pt
				if prev_lat and prev_lon:
					delta=distance([lat,lon],[prev_lat,prev_lon])
					if time and prev_time:
						vel=3600*delta/((time-prev_time).seconds)
					else: 
						vel=0.0
				else: # new segment
					delta=0.0
					vel=0.0
				dist=dist+delta
				newseg.append([lat,lon,time,ele,dist,vel])
				prev_lat,prev_lon,prev_time=lat,lon,time
			newtrk.append(newseg)
	return newtrk

def read_gpx_trk(gpxdata,tzname=None,npoints=None):
	import xml.etree.ElementTree as ET
	gpx=gpxdata
	etree=ET.XML(gpx)
	trksegs=etree.findall('.//'+NS+'trkseg')
	trk=read_all_segments(trksegs,tzname=tzname)
	trk=reduce_points(trk,npoints=npoints)
	trk=eval_dist_velocity(trk)
	return trk

def google_ext_encode(i):
	"""Google Charts' extended encoding,
	see http://code.google.com/apis/chart/mappings.html#extended_values"""
	enc='ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	enc=enc+enc.lower()+'0123456789-.'
	i=int(i)%4096 # modulo 4096
	figure=enc[int(i/len(enc))]+enc[int(i%len(enc))]
	return figure

def google_text_encode_data(trk,x,y,min_x,max_x,min_y,max_y,metric=True):
	if metric:
		mlpkm,fpm=1.0,1.0
	else:
		mlpkm,fpm=milesperkm,feetperm
	xenc=lambda x: "%.1f"%x
	yenc=lambda y: "%.1f"%y
	data='&chd=t:'+join([ join([xenc(p[x]*mlpkm) for p in seg],',')+\
				'|'+join([yenc(p[y]*fpm) for p in seg],',') \
			for seg in trk if len(seg) > 0],'|')
	data=data+'&chds='+join([join([xenc(min_x),xenc(max_x),yenc(min_y),yenc(max_y)],',') \
			for seg in trk if len(seg) > 0],',')
	return data

def google_ext_encode_data(trk,x,y,min_x,max_x,min_y,max_y,metric=True):
	if metric:
		mlpkm,fpm=1.0,1.0
	else:
		mlpkm,fpm=milesperkm,feetperm
	xenc=lambda x: google_ext_encode((x-min_x)*4095/(max_x-min_x))
	yenc=lambda y: google_ext_encode((y-min_y)*4095/(max_y-min_y))
	data='&chd=e:'+join([ join([xenc(p[x]*mlpkm) for p in seg],'')+\
				','+join([yenc(p[y]*fpm) for p in seg],'') \
			for seg in trk if len(seg) > 0],',')
	return data

def google_chart_url(trk,x,y,metric=True):
	if x != var_dist or y != var_ele:
		print 'only distance-elevation profiles are supported in --google mode'
		return
	if metric:
		ele_units,dist_units='m','km'
		mlpkm,fpm=1.0,1.0
	else:
		ele_units,dist_units='ft','miles'
		mlpkm,fpm=milesperkm,feetperm
	urlprefix='http://chart.apis.google.com/chart?chtt=gpxplot.appspot.com&chts=cccccc,9&'
	url='chs=600x400&chco=9090FF&cht=lxy&chxt=x,y,x,y&chxp=2,100|3,100&'\
			'chxl=2:|distance, %s|3:|elevation, %s|'%(dist_units,ele_units)
	min_x=0
	max_x=mlpkm*(max([max([p[x] for p in seg]) for seg in trk if len(seg) > 0]))
	max_y=fpm*(max([max([p[y] for p in seg]) for seg in trk if len(seg) > 0]))
	min_y=fpm*(min([min([p[y] for p in seg]) for seg in trk if len(seg) > 0]))
	range='&chxr=0,0,%s|1,%s,%s'%(int(max_x),int(min_y),int(max_y))
	data=google_ext_encode_data(trk,x,y,min_x,max_x,min_y,max_y,metric)
	url=urlprefix+url+range+data
	if len(url) > 2048:
		raise OverflowError("URL too long, reduce number of points: "+(url))
	return url

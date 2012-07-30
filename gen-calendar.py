import math
import sys
import xml.dom
from datetime import date, timedelta

year=2012
daysInYear = (date(year + 1, 1, 1) - date(year, 1, 1)).days

center=('50%', '50%')
innerRadius = 700
outerRadius = 800

# Return a point on a circle centered in the page as a pair (x, y), where:
# - 'angle' is between 0 and 1, giving the proportion of the distance around the
#   circle from the top, going clockwise
# - 'radius' is the radius.
def radial(angle, radius):
    return (1728/2 + math.sin(2*math.pi * angle) * radius,
            1728/2 - math.cos(2*math.pi * angle) * radius)

# Given an 'out' value ranging from 0 to 1, return a radius length ranging
# from the inner radius to the outer radius.
def mainRadius(out): return innerRadius + out * float(outerRadius - innerRadius)

def setAttributesByDict(element, d):
    for (key, value) in d.items():
        element.setAttribute(key, str(value))

def circle((cx, cy), r):
    c = doc.createElement('circle')
    setAttributesByDict(c, { 'cx': cx, 'cy': cy, 'r': r })
    return c

def line((x1, y1), (x2, y2)):
    l = doc.createElement('line')
    setAttributesByDict(l, { 'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2 })
    return l

# A section from angle a1 to a2, and radius r1 to r2.
def section(a1, a2, r1, r2):
    d =  "M %d %d"             %             radial(a1, r1)  \
      + " A %d %d 0 0 0 %d %d" % ((r1, r1) + radial(a2, r1)) \
      + " L %d %d"             %             radial(a2, r2)  \
      + " A %d %d 0 0 0 %d %d" % ((r2, r2) + radial(a1, r2)) \
      + " Z"
    s = doc.createElement('path')
    s.setAttribute('d', d)
    return s

impl = xml.dom.getDOMImplementation()
doc = impl.createDocument('http://www.w3.org/2000/svg', 'svg',
                          impl.createDocumentType('svg', '-//W3C//DTD SVG 1.1//EN',
                                                  'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd'))
root = doc.documentElement
root.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
root.setAttribute('version', '1.1')
root.setAttribute('width', '24in')
root.setAttribute('height', '24in')
root.setAttribute('viewBox', '0 0 1728 1728') # user unit is pt

# Background: white
background = doc.createElement('rect')
setAttributesByDict(background, { 'fill':'white', 'stroke':'none',
                                  'x1':'0', 'x2':'0', 'width':'1728', 'height':'1728' })

# Frame: circles, week lines.
frame = doc.createElement('g')
frame.setAttribute('fill', 'none')
frame.setAttribute('stroke', 'black')
frame.setAttribute('stroke-width', '4')

frame.appendChild(circle(center, innerRadius))
frame.appendChild(circle(center, outerRadius))

# Day/week lines.
for i in xrange(0, daysInYear):
    a = (float(i) / daysInYear)
    d = date(year, 1, 1) + timedelta(i)
    if i != 0 and d.weekday():
        frame.appendChild(line(radial(a, mainRadius(.4)), radial(a, mainRadius(.6))))
    else:
        frame.appendChild(line(radial(a, innerRadius), radial(a, outerRadius)))

# Week sections
weekgroup = doc.createElement('g')
setAttributesByDict(weekgroup, { 'stroke':'none', 'fill':'rgb(220,220,220)'})

def dateAngle(d):
    n = (d - date(year, 1, 1)).days
    return float(n) / daysInYear

d = date(year, 1, 1)
while d.year == year:
    start = d.weekday()
    nextStart = min(d + timedelta(7 - start), date(year + 1, 1, 1))
    weekgroup.appendChild(section(dateAngle(d), dateAngle(nextStart),
                                  innerRadius, outerRadius))
    d = d - timedelta(start) + timedelta(14)

# Put it all together.
root.appendChild(background)
root.appendChild(weekgroup)
root.appendChild(frame)

with open('calendar.svg', 'w') as f:
    doc.writexml(f, addindent='  ', newl='\n')
    print >> f

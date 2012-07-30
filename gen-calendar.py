import math
import sys
import xml.dom
from datetime import date, timedelta

year=2011
daysInYear = (date(year + 1, 1, 1) - date(year, 1, 1)).days

center=('50%', '50%')

innerRadius0 = 570
outerRadius0 = 670

innerRadius1 = 700
outerRadius1 = 800

# Proportion p of the way from x1 to x2.
def interp(x1, x2, p): return x1 + p * (x2 - x1)

# Spiral coordinates are:
# - an angle a, from 0 to 1, top to top clockwise; and
# - a radius r, from 0 (inner edge) to 1 (outer edge).

# Return the length of the radius for (a, r).
def radius(a, r):
    inner = interp(innerRadius0, innerRadius1, a)
    outer = interp(outerRadius0, outerRadius1, a)
    return interp(inner, outer, r)

# Convert (a, r) to cartesian coordinates.
def spiral(a, r):
    r = radius(a, r)
    return (1728/2 + math.sin(2*math.pi * a) * r,
            1728/2 - math.cos(2*math.pi * a) * r)

def setAttributesByDict(element, d):
    for (key, value) in d.items():
        element.setAttribute(key, str(value))

def line((x1, y1), (x2, y2)):
    l = doc.createElement('line')
    setAttributesByDict(l, { 'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2 })
    return l

# A path command for a spiral segment from a1 to a2, at radius r, This
# assumes that the current path position is spiral(a1, r). Command ends
# with a space.
def spiralSegment(a1, a2, r):
    # Return a circle segment, starting and ending at the right place, and
    # with a radius halfway between our start and end radii. This is kind
    # of a punt, since spiral segments are not circle segments, but it
    # doesn't look too bad as long as the radius is big enough.
    rpx = radius((a1+a2)/2, r)
    return ("A %d %d 0 0 %d %d %d "
            % ((rpx, rpx, (1 if a2 > a1 else 0))
               + spiral(a2, r)))

# A section from angle a1 to a2, and radius r1 to r2.
def section(a1, a2, r1, r2):
    d =  ("M %d %d " % spiral(a1, r1)
          + spiralSegment(a1, a2, r1)
          + "L %d %d " % spiral(a2, r2)
          + spiralSegment(a2, a1, r2)
          + "Z")
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

# Frame: spirals, day lines.
frame = doc.createElement('g')
frame.setAttribute('fill', 'none')
frame.setAttribute('stroke', 'black')
frame.setAttribute('stroke-width', '4')

# Spirals.
def frameSpiral(r):
    s = 12
    d = "M %d %d " % spiral(-1/float(s), r)
    for i in xrange(-1, s+1):
        a0 = float(i)   / s
        a1 = float(i+1) / s
        d = d + spiralSegment(a0, a1, r)
    s = doc.createElement('path')
    s.setAttribute('d', d)
    return s

frame.appendChild(frameSpiral(0))
frame.appendChild(frameSpiral(1))

# Day/week lines.
for i in xrange(-30, daysInYear + 30):
    a = (float(i) / daysInYear)
    d = date(year, 1, 1) + timedelta(i)
    if d.weekday():
        frame.appendChild(line(spiral(a, .4), spiral(a, .6)))
    else:
        frame.appendChild(line(spiral(a, 0), spiral(a, 1)))

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
                                  0, 1))
    d = d - timedelta(start) + timedelta(14)

# Put it all together.
root.appendChild(background)
# root.appendChild(weekgroup)
root.appendChild(frame)

with open('calendar.svg', 'w') as f:
    doc.writexml(f, addindent='  ', newl='\n')
    print >> f

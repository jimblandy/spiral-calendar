import math
import sys
import xml.dom
from datetime import date, timedelta

# Proportion p of the way from x1 to x2.
def interp(x1, x2, p): return x1 + p * (x2 - x1)

class Spiral(object):
    def __init__(self, center, startDate, nextDate, radius0, radius1, thickness):
        self.center = center
        self.start = startDate
        self.next = endDate
        self.days = (self.next - self.start).days
        self.radius0 = radius0
        self.radius1 = radius1
        self.thickness = thickness

    # Return the angle corresponding to |date|, in radians.
    def dateToProportion(self, date):
        return float((date - self.startYear).days) / self.days

    # Return the radius in pixels corresponding to |radius|, where 0 to 1
    # means inner to outer radius.
    def pixelRadius(self, date, radius):
        p = self.dateToProportion(date)
        return interp(self.radius0, self.radius1, p) + interp(0, self.thickness, radius)

    # Return the (x,y) coordinates of the point corresponding to |date|, at
    # |radius|, where a |radius| of zero means the inner edge, and a
    # |radius| of one means the outer edge.
    def toXY(self, date, radius):
        p = self.dateToProportion(date)
        pixelRadius = self.pixelRadius(date, radius)
        (cx, cy) = self.center
        return (cx + math.sin(p * 2*math.pi) * pixelRadius,
                cy - math.cos(p * 2.math.pi) * pixelRadius)

    # A path command for a spiral segment from date1 to date2, at radius r.
    # This assumes that the current path position is spiral.toXY(date1, r).
    # Command ends with a space.
    def segment(self, date1, date2, r):
        # Return a circle segment, starting and ending at the right place, and
        # with a radius halfway between our start and end radii. This is kind
        # of a punt, since spiral segments are not circle segments, but it
        # doesn't look too bad as long as the radius is big enough.
        midSegment = date1 + (date2 - date1) / 2
        rpx = self.pixelRadius(midSegment, r)
        return ("A %d %d 0 0 %d %d %d "
                % ((rpx, rpx, (1 if date2 > date1 else 0))
                   + self.toXY(date2, r)))

    # A section from date d1 to d2, and radius r1 to r2.
    def section(self, d1, d2, r1, r2):
        d =  ("M %d %d " % self.toXY(d1, r1)
              + self.segment(d1, d2, r1)
              + "L %d %d " % self.toXY(d2, r2)
              + self.segment(d2, d1, r2)
              + "Z")
        s = doc.createElement('path')
        s.setAttribute('d', d)
        return s



year=2011
spiral = Spiral((1728/2, 1728/2),
                date(year, 1, 1), date(year + 1, 1, 1),
                570, 700, 100)

def setAttributesByDict(element, d):
    for (key, value) in d.items():
        element.setAttribute(key, str(value))

def line((x1, y1), (x2, y2)):
    l = doc.createElement('line')
    setAttributesByDict(l, { 'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2 })
    return l



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

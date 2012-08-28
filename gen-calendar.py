import math
import sys
import xml.dom
from datetime import date, timedelta

# Proportion p of the way from x1 to x2, where p=0 yields x1, and p=1 yields x2.
def interp(x1, x2, p): return x1 + p * (x2 - x1)

# Yield a series of dates starting with |start|, stepping by |step|, and ending with |end|.
# If |step| is not a timedelta instance, it's treated as a number of days.
def dateRange(start, end, step):
    if not isinstance(step, timedelta):
        step = timedelta(step)
    while start < end:
        yield start
        start = start + step
    yield end

def setAttributes(element, **d):
    for (key, value) in d.items():
        element.setAttribute(key, str(value))
    return element

# Bookkeeping helpers for an SVG XML document. self.root is an xml.dom
# document element in the document self.doc.
class SVGPicture(object):
    def __init__(self, (realWidth, realHeight), pixelWidthHeight):
        impl = xml.dom.getDOMImplementation()
        doctype = impl.createDocumentType('svg', '-//W3C//DTD SVG 1.1//EN',
                                          'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd')
        self.doc = impl.createDocument('http://www.w3.org/2000/svg', 'svg', doctype)
        self.root = self.doc.documentElement
        self.root.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
        self.root.setAttribute('version', '1.1')
        self.root.setAttribute('width', realWidth)
        self.root.setAttribute('height', realHeight)
        self.root.setAttribute('viewBox', '0 0 %d %d' % pixelWidthHeight) # user unit is pt

    def line(self, (x1, y1), (x2, y2), **attributes):
        attributes.update({'x1':x1, 'y1':y1, 'x2':x2, 'y2':y2})
        return setAttributes(self.doc.createElement('line'), **attributes)

    def rect(self, (x, y), (width, height), **attributes):
        attributes.update({'x':x, 'y':y, 'width':width, 'height':height})
        return setAttributes(self.doc.createElement('rect'), **attributes)

    def group(self, **attributes):
        return setAttributes(self.doc.createElement('g'), **attributes)

    def path(self, d, **attributes):
        attributes['d'] = d
        return setAttributes(self.doc.createElement('path'), **attributes)

# A coordinate transformation, taking dates and radii to cartesian points on a spiral.
#
# In the domain (input) coordinate system:
#
# - Points on the "horizontal axis" are dates. The interesting portion of
#   the horizontal axis runs from |topDate| to |nextTopDate|, instances of
#   datetime.date.
#
# - Points on the "vertical axis" are radii. The interesting radii run from
#   zero to one.
#
# We map this points to cartesian coordinates on a spiral as follows:
#
# - The point |topDate,0| maps to |topRadius| pixels due north of |center|,
#   while the point |nextTopdate,0| maps to |nextTopRadius| pixels due
#   north of |center|. Thus, |nextTopDate| - |topDate| is the time that
#   must elapse to bring the spiral |nextTopRadius| - |topRadius| pixels
#   outward, and one full revolution around.
#
# - We map domain points progressing from |topDate| to |nextTopDate| to
#   cartesian points moving clockwise around the spiral.
#
# - The point |d,1| is |thickness| pixels further from |center| than the
#   point |d,0|. Thus, |thickness| establishes the relationship between
#   "vertical axis" values and radii.
#
# Ideally, all we'd need is a function to take |date,radius| pairs to |x,y|
# pairs. (This is what the toXY method does.) To produce good SVG, however,
# we also need methods to generate circle arcs that roughly match
# "horizontal" lines on the spiral.
#
# This class provides methods for computing path commands, but we stay out
# of the business of actually constructing nodes. (Is that a meaningful
# division of labor?)
class Spiral(object):
    def __init__(self, center, topDate, nextTopDate, topRadius, nextTopRadius, thickness):
        self.center = center
        self.top = topDate
        self.nextTop = nextTopDate
        self.circumDays = (self.nextTop - self.top).days
        self.topRadius = topRadius
        self.nextTopRadius = nextTopRadius
        self.thickness = thickness

    # Return the angle corresponding to |date|, in revolutions (1 means one
    # full circuit around the spiral).
    def dateToProportion(self, date):
        return float((date - self.top).days) / self.circumDays

    # Return the distance from the center of the point |date|, |radius|.
    def pixelRadius(self, date, radius):
        p = self.dateToProportion(date)
        return interp(self.topRadius, self.nextTopRadius, p) + interp(0, self.thickness, radius)

    # Return the (x,y) coordinates of the point corresponding to (|date|, |radius|).
    def toXY(self, date, radius):
        (cx, cy) = self.center
        p = self.dateToProportion(date)
        pixelRadius = self.pixelRadius(date, radius)
        return (cx + math.sin(p * 2*math.pi) * pixelRadius,
                cy - math.cos(p * 2*math.pi) * pixelRadius)

    # A path command for a spiral segment from date1 to date2, at radius r.
    # This assumes that the current path position is spiral.toXY(date1, r).
    # Command ends with a space.
    def segment(self, date1, date2, r):
        # Return a circle segment, starting and ending at the right place,
        # and with a radius halfway between our start and end radii. This
        # is kind of a punt, since spiral segments are not circle segments,
        # but it doesn't look too bad as long as the radius is big enough.
        # Could we do better with a spline?
        midSegment = date1 + (date2 - date1) / 2
        rpx = self.pixelRadius(midSegment, r)
        return ("A %.1f %.1f 0 0 %d %.1f %.1f "
                % ((rpx, rpx, (1 if date2 > date1 else 0))
                   + self.toXY(date2, r)))

    # A path command for a section from date d1 to d2, and radius r1 to r2.
    def section(self, date1, date2, r1, r2):
        return ("M %.1f %.1f " % self.toXY(date1, r1)
                + self.segment(date1, date2, r1)
                + "L %.1f %.1f " % self.toXY(date2, r2)
                + self.segment(date2, date1, r2)
                + "Z")

    # A path command for a line radiating out from the center at date d,
    # starting at radius r1, and ending at radius r2.
    def radial(self, d, r1, r2):
        return "M %.1f %.1f L %.1f %.1f " % (self.toXY(d, r1) + self.toXY(d, r2))

class Calendar(object):
    def __init__(self, picture, spiral, startDate, endDate):
        self.picture = picture
        self.spiral = spiral
        self.startDate = startDate
        self.endDate = endDate

    def draw(self):
        self.picture.root.appendChild(self.frame())

    # The "frame": spirals, day lines.
    def frame(self):

        def spiral(r):
            dates = dateRange(self.startDate, self.endDate, 10)
            prev = dates.next()
            d = "M %.1f %.1f " % self.spiral.toXY(prev, r)
            for t in dates:
                d = d + self.spiral.segment(prev, t, r)
                prev = t
            return self.picture.path(d)

        f = picture.group()
        f.setAttribute('fill', 'none')
        f.setAttribute('stroke', 'black')
        f.setAttribute('stroke-width', '1')

        f.appendChild(spiral(0))        # inner spiral edge
        f.appendChild(spiral(1))        # outer spiral edge

        # Day/week lines.
        for d in dateRange(self.startDate, self.endDate, 1):
            if d.weekday():
                f.appendChild(self.picture.path(self.spiral.radial(d, 0.4, 0.6)))
            else:
                f.appendChild(self.picture.path(self.spiral.radial(d, 0.0, 1.0)))

        return f

# The whole picture.
picture = SVGPicture(('8.5in', '11in'), (1728, 2236))

# Background.
picture.root.appendChild(picture.rect((0, 0), (1728, 2236), fill='white', stroke='none'))

# Madoka's calendar.
center = (1728/2, 2236/2)
Calendar(picture,
         Spiral(center=center,
                topDate = date(2012,1,1), nextTopDate = date(2013,1,1),
                topRadius = 700, nextTopRadius = 750, thickness = 20),
         date(2002,6,24), date(2013,1,1)).draw()

# Mika's calendar.
Calendar(picture,
         Spiral(center=center,
                topDate = date(2012,1,1), nextTopDate = date(2013,1,1),
                topRadius = 725, nextTopRadius = 775, thickness = 20),
         date(2005,9,18), date(2013,1,1)).draw()

with open('calendar.svg', 'w') as f:
    picture.doc.writexml(f, addindent='  ', newl='\n')
    print >> f

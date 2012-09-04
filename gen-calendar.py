import math
import sys
import xml.dom
from datetime import date, datetime, timedelta

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

def toDatetime(d):
    if isinstance(d, datetime):
        return d
    else:
        return datetime(d.year, d.month, d.day)

def toFractionalDays(delta):
    return delta.days + float(delta.seconds) / (24 * 60 * 60)

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
        self.root.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
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

    def textPath(self, content, **attributes):
        tp = self.doc.createElement('textPath')
        tp.appendChild(self.doc.createTextNode(str(content)))
        setAttributes(tp, **attributes)
        return tp

    def text(self, content=None, **attributes):
        t = self.doc.createElement('text')
        if content:
            t.appendChild(self.doc.createTextNode(str(content)))
        setAttributes(t, **attributes)
        return t

    def defs(self):
        return self.doc.createElement('defs')

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
        return toFractionalDays(toDatetime(date) - toDatetime(self.top)) / self.circumDays

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

    # A path command to move to |date|, |radius|. The command has no
    # trailing or leading spaces.
    def moveTo(self, date, radius):
        return "M %.1f %.1f" % self.toXY(date, radius)

    # A path command to draw a straight line from the current position to
    # |date|, |radius|. The command starts with a space.
    def lineTo(self, date, radius):
        return " L %.1f %.1f" % self.toXY(date, radius)

    # A path command for a spiral segment from date1 to date2, at radius r.
    # This assumes that the current path position is spiral.toXY(date1, r).
    # The command begins with a space.
    def segment(self, date1, date2, r):
        # Return a circle segment, starting and ending at the right place,
        # and with a radius halfway between our start and end radii. This
        # is kind of a punt, since spiral segments are not circle segments,
        # but it doesn't look too bad as long as the radius is big enough.
        # Could we do better with a spline?
        midSegment = date1 + (date2 - date1) / 2
        rpx = self.pixelRadius(midSegment, r)
        return (" A %.1f %.1f 0 0 %d %.1f %.1f"
                % ((rpx, rpx, (1 if date2 > date1 else 0))
                   + self.toXY(date2, r)))

    # A path command for a section from date d1 to d2, and radius r1 to r2.
    def section(self, date1, date2, r1, r2):
        return (self.moveTo(date1, r1)
                + self.segment(date1, date2, r1)
                + self.lineTo(date2, r2)
                + self.segment(date2, date1, r2)
                + " Z")

    # A path command for a line radiating out from the center at date d,
    # starting at radius r1, and ending at radius r2.
    def radial(self, d, r1, r2):
        return self.moveTo(d, r1) + self.lineTo(d, r2)

class Calendar(object):
    def __init__(self, picture, spiral, startDate, endDate):
        self.picture = picture
        self.spiral = spiral
        self.startDate = startDate
        self.endDate = endDate

    def element(self):
        g = self.picture.group()
        g.appendChild(self.monthSections())
        g.appendChild(self.monthLabels())
        g.appendChild(self.frame())
        return g

    # Return the start of the next month after |date|.
    @classmethod
    def nextMonth(self, date):
        if date.month < 12:
            return date.replace(month=date.month + 1)
        else:
            return date.replace(year=date.year + 1, month=1)

    # Yield (start, end) pairs for each month that overlaps the period
    # starting at |start| and ending at |end|. Clip the pairs to lie within
    # |start|..|end|.
    @classmethod
    def months(self, start, end):
        d = start
        while d < end:
            n = Calendar.nextMonth(d)
            yield(d, min(n, end))
            d = n

    # Draw alternating gray and white backgrounds for the months.
    def monthSections(self):
        g = self.picture.group()
        gray=True
        for (sectionStart, sectionEnd) in Calendar.months(self.startDate, self.endDate):
            p = self.picture.path(self.spiral.section(sectionStart, sectionEnd, 0, 1))
            setAttributes(p, stroke='none', fill='rgb(230,230,230)' if gray else 'white')
            g.appendChild(p)
            gray = not gray
        return g

    # Labels for the months.
    def monthLabels(self):
        g = self.picture.group(fill='rgb(190,190,190)')
        g.setAttribute('font-size', "40")

        def monthId(date, prefix=""):
            return "%smonth-%d-%d" % (prefix, date.year, date.month)

        # Create paths for each month's label to follow.
        d = self.picture.defs()
        for (start, end) in Calendar.months(self.startDate, self.endDate):
            # Stretch out the interval to cover the whole month's span. Use
            # day numbers acceptable in all months.
            start = start.replace(day=5)
            end = end.replace(day=28)
            # Give these lines stroke and stroke width, even though they're
            # in a 'defs'; we occasionally like to see them for debugging.
            p = self.picture.path(self.spiral.moveTo(start, 1.2)
                                  + self.spiral.segment(start, end, 1.2),
                                  id=monthId(start), stroke='black', fill='none')
            p.setAttribute('stroke-width', '4')
            d.appendChild(p)

        g.appendChild(d)

        # Create the month labels.
        for (start, end) in Calendar.months(self.startDate, self.endDate):
            text = start.strftime("%B %Y" if start.month == 1 else "%B")
            tp = self.picture.textPath(text)
            tp.setAttribute('xlink:href', monthId(start, "#"))
            t = self.picture.text(None)
            t.appendChild(tp)
            g.appendChild(t)

        return g

    # The "frame": spirals, day lines, Monday dates
    def frame(self):

        def spiral(r):
            dates = dateRange(self.startDate, self.endDate, 10)
            prev = dates.next()
            d = self.spiral.moveTo(prev, r)
            for t in dates:
                d = d + self.spiral.segment(prev, t, r)
                prev = t
            return self.picture.path(d)

        def weekId(date, prefix=""):
            iso = date.isocalendar()
            return "%sweek-%d-%d" % (prefix, iso[0], iso[1])

        f = picture.group()
        f.setAttribute('fill', 'none')
        f.setAttribute('stroke', 'black')
        f.setAttribute('stroke-width', '1')

        f.appendChild(spiral(0))        # inner spiral edge
        f.appendChild(spiral(1))        # outer spiral edge

        # A defs element, to hold the paths for the Monday date labels.
        ld = self.picture.defs()
        f.appendChild(ld)

        # Day/week lines.
        for d in dateRange(self.startDate, self.endDate, 1):
            if d.weekday():
                p = self.picture.path(self.spiral.radial(d, 0.4, 0.6))
            else:
                p = self.picture.path(self.spiral.radial(d, 0.0, 1.0))
            if d == date.today():
                p.setAttribute('stroke-width', '4')
            f.appendChild(p)

            # If this day is a Monday, label its day within the month.
            if d.weekday() == 0:
                # Create a path for the label to follow. (Convert to
                # datetime, so we can space in by fractional days.)
                labelStart = toDatetime(d) + timedelta(0.3)
                i = (self.spiral.moveTo(labelStart, .8)
                     + self.spiral.section(labelStart, labelStart + timedelta(7), .8, .8))
                lp = self.picture.path(i, id=weekId(d))
                ld.appendChild(lp)
                # Create a day-of-month label, on that path.
                tp = self.picture.textPath(" %d" % (d.day,))
                tp.setAttribute('xlink:href', weekId(d, '#'))
                t = self.picture.text(None)
                t.appendChild(tp)
                f.appendChild(t)

        return f

# Dimensions of the page, in inches
pageSizeInches = ('24in', '24in')
pageSize = (1728, 1728)
center = (pageSize[0]/2, pageSize[1]/2)

# The whole picture.
picture = SVGPicture(pageSizeInches, pageSize)

# Background.
picture.root.appendChild(picture.rect((0, 0), pageSize, fill='white', stroke='none'))

year = 2013
topDate = date(year,1,1)
yearLength = timedelta(365 + (1.0/4) - (1.0/100) + (1.0/400))
startDate = date(2012, 8, 27)
endDate =   date(2013, 9, 2)
picture.root.appendChild(Calendar(picture,
                                  Spiral(center=center,
                                         topDate = topDate, nextTopDate = topDate + yearLength,
                                         topRadius = 550, nextTopRadius = 675, thickness = 70),
                                  startDate, endDate)
                         .element());

with open('calendar.svg', 'w') as f:
    picture.doc.writexml(f, addindent='  ', newl='\n')
    print >> f

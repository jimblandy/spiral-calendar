# -*- coding: utf-8 -*-
import codecs, math

from gen_calendar import SVGPicture, interp, setAttributes

# A coordinate transformation, taking angles and radii to cartesian points
# on a circular band.
#
# The circular band itself has |center| (cartesian) as its center; the
# inner edge of the band is |radius| units from the center; the outer edge
# is |thickness| units further.
#
# angles range from 0 to |cycle|; both mean the top, and travel towards
# increasing numbers means clockwise travel.
#
# radii range from 0 to 1; 0 means the inner edge of the band, and 1 means
# the outer edge of the band.
class CircularBand(object):
    def __init__(self, center, radius, thickness, cycle):
        self.center = center
        self.radius = radius
        self.thickness = thickness
        self.cycle = cycle

    # Return the radius in pixels corresponding to |radius|.
    def pixelRadius(self, radius):
        return interp(self.radius, self.radius + self.thickness, radius)

    def toXY(self, angle, radius):
        (cx, cy) = self.center
        pxr = self.pixelRadius(radius)
        a = float(angle) / self.cycle * 2 * math.pi
        return (cx + math.sin(a) * pxr, cy - math.cos(a) * pxr)

    # A path command to move to |angle|, |radius|. The command has no
    # trailing or leading spaces.
    def moveTo(self, angle, radius):
        return "M %.1f %.1f" % self.toXY(angle, radius)

    # A path command to draw a straight line from the current position to
    # |angle|, |radius|. The command starts with a space.
    def lineTo(self, angle, radius):
        return " L %.1f %.1f" % self.toXY(angle, radius)

    # A path command for a circular arc from angle1 to angle2, at radius r.
    # This assumes that the current path position is spiral.toXY(angle1,
    # r). The command begins with a space.
    def segment(self, angle1, angle2, r):
        pxr = self.pixelRadius(r)
        return (" A %.1f %.1f 0 0 %d %.1f %.1f"
                % ((pxr, pxr, (1 if angle2 > angle1 else 0)) + self.toXY(angle2, r)))

    # A path command for a section from angle d1 to d2, and radius r1 to r2.
    def section(self, angle1, angle2, r1, r2):
        return (self.moveTo(angle1, r1)
                + self.segment(angle1, angle2, r1)
                + self.lineTo(angle2, r2)
                + self.segment(angle2, angle1, r2)
                + " Z")

    # A path command for a line radiating out from the center at angle d,
    # starting at radius r1, and ending at radius r2.
    def radial(self, d, r1, r2):
        return self.moveTo(d, r1) + self.lineTo(d, r2)

class Week(object):
    def __init__(self, picture, band):
        self.picture = picture
        self.band = band
        self.nextId = 0

    def element(self):
        g = self.picture.group()
        g.appendChild(self.daySections())
        g.appendChild(self.dayLabels())
        return g

    def freshId(self, prefix):
        self.nextId = self.nextId + 1
        return "%s-%d" % (prefix, self.nextId)

    # Build a label on a circular arc. Display |text| on a path from
    # |start| to |end| at |radius|. Add the path as a child of |defs|, and
    # add the label itself as a child of |labels|.
    def arcLabel(self, text, start, end, radius, defs, labels):
        id = self.freshId('arcLabelPath')

        # First, the path. Give these lines stroke and stroke width, even
        # though they're in a 'defs'; we occasionally like to see them for
        # debugging.
        p = self.picture.path(self.band.moveTo(start, radius)
                              + self.band.segment(start, end, radius),
                              id=id, stroke='black', fill='none')
        p.setAttribute('stroke-width', '4')

        # Then, the label text.
        tp = self.picture.textPath(text)
        tp.setAttribute('xlink:href', '#' + id)
        t = self.picture.text(None)
        t.appendChild(tp)

        defs.appendChild(p)
        labels.appendChild(t)

    def daySections(self):
        g = self.picture.group()
        setAttributes(g, stroke='black', fill='none')
        g.setAttribute('stroke-width', '4')
        for i in xrange(7):
            p = self.picture.path(self.band.section(i, i+1, 0, 1))
            g.appendChild(p)
        return g

    def dayLabels(self):
        g = self.picture.group(fill='rgb(220,220,220)')

        d = self.picture.defs()
        g.appendChild(d)

        english_days = ['Monday', 'Tuesday',  'Wednesday', 'Thursday',
                        'Friday', 'Saturday', 'Sunday']
        hiragana_days = [u'げつようび', u'かようび', u'すいようび', u'もくようび',
                         u'きんようび', u'どようび', u'にちようび']
        kanji_days = u'月火水木金土日'
        for i in xrange(7):
            self.arcLabel(english_days[i], i+0.05, i+1, 0.1, d, g)
            g.lastChild.setAttribute('font-size', '40')

            self.arcLabel(hiragana_days[i], i+0.05, i+1, 0.33, d, g)
            g.lastChild.setAttribute('font-size', '40')

            self.arcLabel(kanji_days[i], i+0.03, i+1, 0.6, d, g)
            g.lastChild.setAttribute('font-size', '80')

        return g


if __name__ == '__main__':

    # Dimensions of the page, in inches
    pageSizeInches = ('18in', '18in')
    pageSize = (18*72, 18*72)
    center = (pageSize[0]/2, pageSize[1]/2)

    # The whole picture.
    picture = SVGPicture(pageSizeInches, pageSize)

    # Background.
    picture.root.appendChild(picture.rect((0, 0), pageSize, fill='white', stroke='none'))

    # The week.
    picture.root.appendChild(Week(picture,
                                  CircularBand(center, radius=350, thickness=200, cycle=7))
                             .element())

    with codecs.open('week.svg', 'w', encoding='utf-8') as f:
        picture.doc.writexml(f, addindent='  ', newl='\n')
        print >> f

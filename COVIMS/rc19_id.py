import numpy as np
import re

# (Time in years, last VIMS file before, first VIMS file after)
GAPS = [
 (2000.3500, 1327302745, 1340483487),
 (2000.6950, 1343357509, 1347928845),
 (2000.8680, 1347964472, 1352959095),
 (2000.8780, 1353103852, 1353246377),
 (2000.8840, 1353265258, 1353318137),
 (2000.8940, 1353534654, 1353677179),
 (2000.9030, 1353893697, 1353964221),
 (2000.9110, 1354126863, 1354179743),
 (2000.9180, 1354324500, 1354395024),
 (2000.9250, 1354557666, 1354610545),
 (2000.9310, 1354755302, 1354825827),
 (2000.9360, 1354827063, 1354969588),
 (2000.9420, 1355042584, 1355171349),
 (2000.9470, 1355297631, 1355306298),
 (2000.9520, 1355385627, 1355517712),
 (2000.9560, 1355539774, 1355687052),
 (2000.9610, 1355727200, 1355863331),
 (2001.1200, 1360722983, 1360937245),
 (2001.5000, 1364481563, 1373331221),
 (2002.0000, 1383906082, 1394091067),
 (2005.5000, 1498752472, 1499045873),
 (2006.0000, 1514578411, 1514910706),
 (2006.5000, 1530543176, 1530544644),
 (2007.0000, 1546295233, 1546355125),
 (2007.5000, 1562101149, 1562101670),
 (2008.0000, 1577857825, 1577906325),
 (2008.5000, 1593658741, 1593658916),
 (2009.0000, 1609396445, 1609440913),
 (2009.5000, 1624835084, 1625234636),
 (2011.5000, 1687660449, 1688392537),
 (2012.0000, 1704110326, 1704110660),
 (2012.5000, 1719866923, 1719893660),
 (2013.0000, 1735601157, 1735908241),
 (2013.5000, 1751446782, 1751448407),
 (2014.0000, 1767194848, 1767238939),
 (2014.3000, 1776350921, 1777319980),
 (2014.5000, 1782987309, 1783069074),
 (2015.5000, 1813427693, 1814628218),
 (2016.0000, 1830232879, 1830405567),
 (2016.5000, 1846118995, 1846120329),
 (2017.0000, 1861894801, 1861899885),
 (2017.5000, 1877635907, 1877745648),
]

IDS = np.array([1999.6] + [t[0] for t in GAPS])

# Constants based on trial and error using the above tabulation
Y = 31557600.0
E = 1593658828.0

def yearfrac_from_sclk(sclk):
    return (sclk-E)/Y + 2008.5

def rc19_id_from_sclk(sclk):
    """The RC19 ID as a fraction of a year, given the SCLK value of a VIMS
    file. Use this to identify the wavelength bin file given the file name."""

    yearfrac = yearfrac_from_sclk(sclk)
    diffs = yearfrac - IDS
    return IDS[yearfrac - IDS > 0][-1] if diffs[0] > 0 else IDS[0]

# This pattern matches any filepath in which the basename contains a ten-digit
# number starting with '12'-'18'.
REGEX = re.compile(r'(?:|.*[^0-9])(1[2-8][0-9]{8})[^/]*$')

def rc19_id_from_filename(filename):
    """The RC19 ID as a fraction of a year, given a VIMS filepath. The filepath
    must contain a SCLK value embedded as a ten-digit integer."""

    match = REGEX.match(filename)
    if match is None:
        raise ValueError('not a valid VIMS filename: ' + filename)

    sclk = int(match.group(1))
    return rc19_id_from_sclk(sclk)


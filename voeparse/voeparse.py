#pysovo VOEvent Tools
#Convenience functions allowing easy access to information in VOEvent packets. 
#Tim Staley, <timstaley337@gmail.com>, 2012

from lxml import objectify, etree
from collections import namedtuple

import definitions
voevent_v2_0_schema = etree.XMLSchema(
                        etree.fromstring(definitions.v2_0_schema_str))

#Personally, I like astropysics.coords, but that's a fairly big dependency.
#So here I'll just return a namedtuple 
Coords = namedtuple('Coords', 'ra dec ra_err dec_err units system')

class CoordSystemIDs(object):
    """Handy tags listing common coordinate system identifiers"""
    fk5 = 'UTC-FK5-GEO'

class CoordUnits(object):
    """Handy tags listing the unit names used by voeparse."""
    degrees = 'degrees'

def loads(s, validate=False):
    """
    Wrapper to parse a VOEvent tree, taking care of some subtleties.

    Currently pretty basic, but we can imagine using this function to
    homogenise or at least identify different VOEvent versions, etc.

    NB The namespace is removed from the root element tag to make
    objectify access work as expected,
    (see docstring for ``_remove_root_tag_prefix``)
    so we must re-insert it when we want to conform to schema.
    """
    v = objectify.fromstring(s)
    _remove_root_tag_prefix(v)
    return v


def load(path):
    s = open(path, 'rb').read()
    return loads(s)


def _remove_root_tag_prefix(v):
    """
    Removes 'voe' namespace prefix from root tag.

    When we load in a VOEvent, the root element has a tag prefixed by
     the VOE namespace, e.g. {http://www.ivoa.net/xml/VOEvent/v2.0}VOEvent
    Because objectify expects child elements to have the same namespace as
    their parent, this breaks the python-attribute style access mechanism.
    We can get around it without altering root, via e.g
     who = v['{}Who']

    Alternatively, we can temporarily ditch the namespace altogether.
    This makes access to elements easier, but requires care to reinsert
    the namespace upon output.

    I've gone for the latter option.
    """
    v.tag = v.tag.replace(''.join(('{', v.nsmap['voe'], '}')), '')
    # Now v.tag = '{}VOEvent'
    return


def _reinsert_root_tag_prefix(v):
    """
    Returns 'voe' namespace prefix to root tag.
    """
    v.tag = ''.join(('{', v.nsmap['voe'], '}VOEvent'))
    return

def _return_to_standard_xml(v):
    #Remove lxml.objectify DataType namespace prefixes:
    objectify.deannotate(v)
    #Put the default namespace back:
    _reinsert_root_tag_prefix(v)
#    etree.cleanup_namespaces(v)

def dumps(v, validate=False, pretty_print=True, xml_declaration=True):
    """Converts voevent 'v' to string.

    NB Encoding is UTF-8, in line with V2 schema.
    Declaring the encoding can cause diffs with the original loaded VOEvent,
    but I think it's probably the right thing to do.
    """
    _return_to_standard_xml(v)
    s = etree.tostring(v, pretty_print=pretty_print,
                       xml_declaration=xml_declaration,
                       encoding='UTF-8')
    _remove_root_tag_prefix(v)
    return s

def dump(v, file, validate=False, pretty_print=True, xml_declaration=True):
    """Dumps voevent 'v' to file"""
    file.write(dumps(v, validate, pretty_print, xml_declaration))

def valid_as_v2_0(v):
    _return_to_standard_xml(v)
    valid_bool = voevent_v2_0_schema.validate(v)
    _remove_root_tag_prefix(v)
    return valid_bool

def assert_valid_as_v2_0(v):
    """Raises an lxml.etree.DocumentInvalid if v is bad.

      Especially useful since the stack trace contains a reason for the
      invalidation.
    """
    _return_to_standard_xml(v)
    valid_bool = voevent_v2_0_schema.assertValid(v)
    _remove_root_tag_prefix(v)
    return valid_bool

def make_voevent(ivorn, role,
                 validate=True):
    """Make a VOEvent conforming to schema.

      Note ivorn should be supplied *without* prefix,
      e.g. ``ivorn = "voevent.soton.ac.uk/EXAMPLE#Test_packet_1" ``
   """
    v = objectify.fromstring(definitions.v2_0_skeleton_str)
    _remove_root_tag_prefix(v)
    v.attrib['ivorn'] = ''.join(('ivo://', ivorn))
    v.attrib['role'] = role
    #For a moment I considering implementing various checks
    #But all the hard work is already done for us!
    if validate:
        assert_valid_as_v2_0(v)
    return v
#
#def get_param_names(v):
#    '''
#    Grabs the "what" section of a voevent, and produces a list of tuples of group name and param name.
#    For a bare param, the group name is the empty string.
#    
#    NB. This replicates functionality from VOEventLib - but the inbuilt version is broken as of v0.3.
#    '''
#    list = []
#    w = v.What
#    if not w: return list
#    for p in v.What.Param:
#        list.append(('', p.name))
#    for g in v.What.Group:
#        for p in g.Param:
#            list.append((g.name, p.name))
#    return list
#


#
def pull_astro_coords(v):
    """Returns a Coords namedtuple.

        For now, only tested / compatible with NASA GCN style coords format.
    """
    ac = v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords
    ac_sys = v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoordSystem
    sys = ac_sys.attrib['id']

    try:
        assert ac.Position2D.Name1 == 'RA' and ac.Position2D.Name2 == 'Dec'
        ra_deg = ac.Position2D.Value2.C1
        dec_deg = ac.Position2D.Value2.C2
        err_deg = ac.Position2D.Error2Radius
    except AttributeError:
        raise ValueError("Unrecognised AstroCoords type")
    return Coords(ra=ra_deg, dec=dec_deg,
                  ra_err=err_deg, dec_err=err_deg,
                  units=CoordUnits.degrees,
                  system=sys
                  )


#def get_isotime(v):
#    assert isinstance(v, voe.VOEvent)
#    try:
#        ol = v.WhereWhen.ObsDataLocation.ObservationLocation
#        return ol.AstroCoords.Time.TimeInstant.ISOTime
#    except:
#        return None
#
#def make_Who(names, emails):
#    names = listify(names)
#    emails = listify(emails)
#    w = voe.Who()
#    w.Author = voe.Author()
#    w.Author.contactName = names
#    w.Author.contactEmail = emails
#    return w

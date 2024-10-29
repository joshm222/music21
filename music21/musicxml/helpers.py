# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Name:         musicxml/helpers.py
# Purpose:      Helper routines for musicxml export
#
# Authors:      Michael Scott Asato Cuthbert
#               Jacob Tyler Walls
#
# Copyright:    Copyright © 2013-2020 Michael Scott Asato Cuthbert
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
from __future__ import annotations

import copy
import typing as t
from xml.etree.ElementTree import tostring as et_tostring

from music21 import common
from music21 import meter
from music21.musicxml import xmlObjects
from music21 import prebase

if t.TYPE_CHECKING:
    from collections.abc import Callable
    import xml.etree.ElementTree as ET

    from music21.base import Music21Object


def dumpString(obj, *, noCopy=False) -> str:
    r'''
    wrapper around xml.etree.ElementTree that returns a string
    in every case and indents tags and sorts attributes.

    >>> from music21.musicxml.m21ToXml import Element
    >>> from music21.musicxml.helpers import dumpString
    >>> e = Element('accidental')

    >>> dumpString(e)
    '<accidental />'

    >>> e.text = '∆'
    >>> e.text == '∆'
    True
    >>> dumpString(e)
    '<accidental>∆</accidental>'
    '''
    if noCopy is False:
        xmlEl = copy.deepcopy(obj)  # adds 5% overhead
    else:
        xmlEl = obj
    indent(xmlEl)  # adds 5% overhead

    for el in xmlEl.iter():
        attrib = el.attrib
        if len(attrib) > 1:
            # adjust attribute order, e.g. by sorting
            attribs = sorted(attrib.items())
            attrib.clear()
            attrib.update(attribs)
    xStr = et_tostring(xmlEl, encoding='unicode')
    xStr = xStr.rstrip()
    return xStr


def dump(obj):
    r'''
    wrapper around xml.etree.ElementTree that prints a string
    in every case and indents tags and sorts attributes.  (Prints, does not return)

    >>> from music21.musicxml.helpers import dump
    >>> from xml.etree.ElementTree import Element
    >>> e = Element('accidental')

    >>> dump(e)
    <accidental />

    >>> e.text = '∆'
    >>> e.text == '∆'
    True
    >>> dump(e)
    <accidental>∆</accidental>
    '''
    print(dumpString(obj))


def indent(elem, level=0):
    '''
    helper method, indent an element in place:
    '''
    i = '\n' + level * '  '
    lenL = len(elem)
    if lenL:
        if not elem.text or not elem.text.strip():
            elem.text = i + '  '
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

        subElem = None
        for subElem in elem:
            indent(subElem, level + 1)
        if subElem is not None:  # last el
            subElem.tail = i

        if not elem.tail or not elem.tail.strip():
            elem.tail = '\n' + level * '  '
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def insertBeforeElements(root, insert, tagList=None):
    # noinspection PyShadowingNames
    '''
    Insert element `insert` into element `root` at the earliest position
    of any instance of a child tag given in `tagList`. Append the element
    if `tagList` is `None`.

    >>> from xml.etree.ElementTree import fromstring as El
    >>> from music21.musicxml.helpers import insertBeforeElements, dump
    >>> root = El('<clef><sign>G</sign><line>4</line></clef>')
    >>> insert = El('<foo/>')

    >>> insertBeforeElements(root, insert, tagList=['line'])
    >>> dump(root)
    <clef>
        <sign>G</sign>
        <foo />
        <line>4</line>
    </clef>

    Now insert another element at the end by not specifying a tag list:

    >>> insert2 = El('<bar/>')
    >>> insertBeforeElements(root, insert2)
    >>> dump(root)
    <clef>
        <sign>G</sign>
        <foo />
        <line>4</line>
        <bar />
    </clef>
    '''
    if not tagList:
        root.append(insert)
        return
    insertIndices = {len(root)}
    # Iterate children only, not grandchildren
    for i, child in enumerate(root.findall('*')):
        if child.tag in tagList:
            insertIndices.add(i)
    root.insert(min(insertIndices), insert)


def measureNumberComesBefore(mNum1: str, mNum2: str) -> bool:
    '''
    Determine whether `measureNumber1` strictly precedes
    `measureNumber2` given that they could involve suffixes.
    Equal values return False.

    >>> from music21.musicxml.helpers import measureNumberComesBefore
    >>> measureNumberComesBefore('23', '24')
    True
    >>> measureNumberComesBefore('23', '23')
    False
    >>> measureNumberComesBefore('23', '23a')
    True
    >>> measureNumberComesBefore('23a', '23b')
    True
    >>> measureNumberComesBefore('23b', '23a')
    False
    >>> measureNumberComesBefore('23b', '24a')
    True
    >>> measureNumberComesBefore('23b', '23b')
    False
    '''
    def splitSuffix(measureNumber):
        number = ''
        for char in measureNumber:
            if char.isnumeric():
                number += char
            else:
                break
        suffix = measureNumber[len(number):]
        return number, suffix

    if mNum1 == mNum2:
        return False
    m1Numeric, m1Suffix = splitSuffix(mNum1)
    m2Numeric, m2Suffix = splitSuffix(mNum2)
    if int(m1Numeric) != int(m2Numeric):
        return int(m1Numeric) < int(m2Numeric)
    else:
        sortedSuffixes = sorted([m1Suffix, m2Suffix])
        return m1Suffix is sortedSuffixes[0]


def isFullMeasureRest(r: 'music21.note.Rest') -> bool:
    isFullMeasure = False
    if r.fullMeasure in (True, 'always'):
        isFullMeasure = True
    elif r.fullMeasure == 'auto':
        tsContext = r.getContextByClass(meter.TimeSignature)
        if tsContext and tsContext.barDuration.quarterLength == r.duration.quarterLength:
            isFullMeasure = True
    return isFullMeasure


def synchronizeIdsToM21(element: ET.Element, m21Object: Music21Object):
    '''
    MusicXML 3.1 defines the id attribute
    (%optional-unique-id)
    on many elements which is perfect for setting as .id on
    a music21 element.

    <fermata id="hello"><id>bye</id></fermata>

    >>> from xml.etree.ElementTree import fromstring as El
    >>> e = El('<fermata id="fermata1"/>')
    >>> f = expressions.Fermata()
    >>> musicxml.helpers.synchronizeIdsToM21(e, f)
    >>> f.id
    'fermata1'

    Does not change the id if the id is not specified:

    >>> e = El('<fermata />')
    >>> f = expressions.Fermata()
    >>> f.id = 'doNotOverwrite'
    >>> musicxml.helpers.synchronizeIdsToM21(e, f)
    >>> f.id
    'doNotOverwrite'
    '''
    newId = element.get('id', None)
    if not newId:
        return
    m21Object.id = newId

def synchronizeIdsToXML(
    element: ET.Element,
    m21Object: prebase.ProtoM21Object|None
) -> None:
    # noinspection PyTypeChecker
    '''
    MusicXML 3.1 defines the id attribute (entity: %optional-unique-id)
    on many elements which is perfect for getting from .id on
    a music21 element.

    >>> from xml.etree.ElementTree import fromstring as El
    >>> e = El('<fermata />')
    >>> f = expressions.Fermata()
    >>> f.id = 'fermata1'
    >>> musicxml.helpers.synchronizeIdsToXML(e, f)
    >>> e.get('id')
    'fermata1'

    Does not set attr: id if el.id is not valid or default:

    >>> e = El('<fermata />')
    >>> f = expressions.Fermata()
    >>> musicxml.helpers.synchronizeIdsToXML(e, f)
    >>> e.get('id', None) is None
    True
    >>> f.id = '123456'  # invalid for MusicXML id
    >>> musicxml.helpers.synchronizeIdsToXML(e, f)
    >>> e.get('id', None) is None
    True

    None can be passed in instead of a m21object.

    >>> e = El('<fermata />')
    >>> musicxml.helpers.synchronizeIdsToXML(e, None)
    >>> e.get('id', 'no idea')
    'no idea'
    '''
    # had to suppress type-checking because of spurious error on
    #    e.get('id', 'no idea')
    if not isinstance(m21Object, prebase.ProtoM21Object):
        return
    if not hasattr(m21Object, 'id'):
        return

    m21Id = m21Object.id  # type: ignore

    if m21Id is None:
        return

    if not xmlObjects.isValidXSDID(m21Id):
        return
    element.set('id', m21Id)



def setM21AttributeFromAttribute(
    m21El: t.Any,
    xmlEl: ET.Element,
    xmlAttributeName: str,
    attributeName: str|None = None,
    transform: Callable[[str], t.Any]|None = None,
) -> None:
    '''
    If xmlEl has at least one element of tag==tag with some text. If
    it does, set the attribute either with the same name (with "foo-bar" changed to
    "fooBar") or with attributeName to the text contents.

    Pass a function or lambda function as transform to transform the value before setting it

    >>> from xml.etree.ElementTree import fromstring as El
    >>> e = El('<page-layout new-page="yes" page-number="4" />')

    >>> setb = musicxml.helpers.setM21AttributeFromAttribute
    >>> pl = layout.PageLayout()
    >>> setb(pl, e, 'page-number')
    >>> pl.pageNumber
    '4'

    >>> setb(pl, e, 'new-page', 'isNew')
    >>> pl.isNew
    'yes'


    Transform the pageNumber value to an int.

    >>> setb(pl, e, 'page-number', transform=int)
    >>> pl.pageNumber
    4

    More complex:

    >>> convBool = musicxml.xmlObjects.yesNoToBoolean
    >>> setb(pl, e, 'new-page', 'isNew', transform=convBool)
    >>> pl.isNew
    True
    '''
    value = xmlEl.get(xmlAttributeName)  # find first
    if value is None:
        return

    if transform is not None:
        value = transform(value)

    if attributeName is None:
        attributeName = common.hyphenToCamelCase(xmlAttributeName)
    setattr(m21El, attributeName, value)


def setXMLAttributeFromAttribute(
    m21El: t.Any,
    xmlEl: ET.Element,
    xmlAttributeName: str,
    attributeName: str|None = None,
    transform: Callable[[t.Any], t.Any]|None = None
):
    '''
    If m21El has at least one element of tag==tag with some text. If
    it does, set the attribute either with the same name (with "foo-bar" changed to
    "fooBar") or with attributeName to the text contents.

    Pass a function or lambda function as transform to transform the value before setting it

    >>> from xml.etree.ElementTree import fromstring as El
    >>> e = El('<page-layout/>')

    >>> setb = musicxml.helpers.setXMLAttributeFromAttribute
    >>> pl = layout.PageLayout()
    >>> pl.pageNumber = 4
    >>> pl.isNew = True

    >>> setb(pl, e, 'page-number')
    >>> e.get('page-number')
    '4'

    >>> XB = musicxml.m21ToXml.XMLExporterBase()
    >>> XB.dump(e)
    <page-layout page-number="4" />

    >>> setb(pl, e, 'new-page', 'isNew')
    >>> e.get('new-page')
    'True'


    Transform the isNew value to 'yes'.

    >>> convBool = musicxml.xmlObjects.booleanToYesNo
    >>> setb(pl, e, 'new-page', 'isNew', transform=convBool)
    >>> e.get('new-page')
    'yes'
    '''
    if attributeName is None:
        attributeName = common.hyphenToCamelCase(xmlAttributeName)

    value = getattr(m21El, attributeName, None)
    if value is None:
        return

    if transform is not None:
        value = transform(value)

    xmlEl.set(xmlAttributeName, str(value))



if __name__ == '__main__':
    import music21
    music21.mainTest()  # doc tests only

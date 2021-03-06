
#
# soaplib - Copyright (C) Soaplib contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import soaplib

from lxml import etree

def nillable_value(func):
    def wrapper(cls, value, tns, *args, **kwargs):
        if value is None:
            return Null.to_xml(value, tns, *args, **kwargs)
        return func(cls, value, tns, *args, **kwargs)
    return wrapper

def nillable_element(func):
    def wrapper(cls, element):
        if bool(element.get('{%s}nil' % soaplib.ns_xsi)): # or (element.text is None and len(element.getchildren()) == 0):
            return None
        return func(cls, element)
    return wrapper

def string_to_xml(cls, value, tns, name):
    assert isinstance(value, str) or isinstance(value, unicode), "'value' must " \
                    "be string or unicode. it is instead '%s'" % repr(value)

    retval = etree.Element("{%s}%s" % (tns,name))

    retval.set('{%s}type' % soaplib.ns_xsi, cls.get_type_name_ns())
    retval.text = value

    return retval

class Base(object):
    __namespace__ = None
    __type_name__ = None

    class Attributes(object):
        nillable = True
        min_occurs = 0
        max_occurs = 1

    class Empty(object):
        pass

    @classmethod
    def is_default(cls):
        return (cls.Attributes.nillable == Base.Attributes.nillable
            and cls.Attributes.min_occurs == Base.Attributes.min_occurs
            and cls.Attributes.max_occurs == Base.Attributes.max_occurs)

    @classmethod
    def get_namespace_prefix(cls):
        ns = cls.get_namespace()

        retval = soaplib.get_namespace_prefix(ns)

        return retval

    @classmethod
    def get_namespace(cls):
        return cls.__namespace__

    @classmethod
    def resolve_namespace(cls, default_ns):
        if cls.__namespace__ in soaplib.const_prefmap and not cls.is_default():
            cls.__namespace__ = None

        if cls.__namespace__ is None:
            cls.__namespace__ = cls.__module__

            if (cls.__namespace__.startswith("soaplib")
                                            or cls.__namespace__ == '__main__'):
                cls.__namespace__ = default_ns

    @classmethod
    def get_type_name(cls):
        retval = cls.__type_name__
        if retval is None:
            retval = cls.__name__.lower()

        return retval

    @classmethod
    def get_type_name_ns(cls):
        if cls.get_namespace() != None:
            return "%s:%s" % (cls.get_namespace_prefix(), cls.get_type_name())

    @classmethod
    def to_xml(cls, value, tns, name='retval'):
        return string_to_xml(cls, value, tns, name)

    @classmethod
    def add_to_schema(cls, schema_entries):
        '''
        Nothing needs to happen when the type is a standard schema element
        '''
        pass

    @classmethod
    def customize(cls, **kwargs):
        """
        This function duplicates and customizes the class it belongs to. The
        original class remains unchanged.
        """

        cls_dict = {}

        for k in cls.__dict__:
            if not (k in ("__dict__", "__module__", "__weakref__")):
                cls_dict[k] = cls.__dict__[k]

        class Attributes(cls.Attributes):
            pass

        cls_dict['Attributes'] = Attributes

        for k,v in kwargs.items():
            setattr(Attributes,k,v)

        cls_dup = type(cls.__name__, cls.__bases__, cls_dict)

        return cls_dup

class Null(Base):
    @classmethod
    def to_xml(cls, value, tns, name='retval'):
        element = etree.Element("{%s}%s" % (tns,name))
        element.set('{%s}nil' % soaplib.ns_xsi, 'true')

        return element

    @classmethod
    def from_xml(cls, element):
        return None

class SimpleType(Base):
    __namespace__ = "http://www.w3.org/2001/XMLSchema"
    __base_type__ = None

    class Attributes(Base.Attributes):
        values = set()

    def __new__(cls, **kwargs):
        """
        Overriden so that any attempt to instantiate a primitive will return a
        customized class instead of an instance.

        See serializers.base.Base for more information.
        """

        retval = cls.customize(**kwargs)

        if not retval.is_default():
            if retval.get_namespace() is None:
                retval.__base_type__ = cls.__base_type__
            else:
                retval.__base_type__ = cls.get_type_name_ns()

            if retval.get_namespace() in soaplib.const_prefmap:
                retval.__namespace__ = None

            if retval.__type_name__ is None:
                retval.__type_name__ = kwargs.get("type_name", Base.Empty)

        return retval

    @classmethod
    def is_default(cls):
        return (Base.is_default()
            and cls.Attributes.values == SimpleType.Attributes.values)

    @classmethod
    def get_restriction_tag(cls, schema_entries):
        simple_type = etree.Element('{%s}simpleType' % soaplib.ns_xsd)
        simple_type.set('name', cls.get_type_name())
        schema_entries.add_simple_type(cls, simple_type)

        restriction = etree.SubElement(simple_type,
                                            '{%s}restriction' % soaplib.ns_xsd)
        restriction.set('base', cls.__base_type__)

        for v in cls.Attributes.values:
            enumeration = etree.SubElement(restriction,
                                            '{%s}enumeration' % soaplib.ns_xsd)
            enumeration.set('value', str(v))

        return restriction

    @classmethod
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls) and not cls.is_default():
            cls.get_restriction_tag(schema_entries)

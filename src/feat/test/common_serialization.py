# -*- coding: utf-8 -*-
# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import itertools
import types

from twisted.python.reflect import qual
from twisted.spread import jelly
from twisted.trial.unittest import SkipTest

from feat.common import serialization
from feat.common.serialization import base
from feat.interface.serialization import *

from . import common


@serialization.register
class SerializableDummy(serialization.Serializable, jelly.Jellyable):
    '''Simple dummy class that implements various serialization scheme.'''

    def __init__(self):
        self.str = "dummy"
        self.unicode = u"dummy"
        self.int = 42
        self.long = 2**66
        self.float = 3.1415926
        self.bool = True
        self.none = None
        self.list = [1, 2, 3]
        self.tuple = (1, 2, 3)
        self.set = set([1, 2, 3])
        self.dict = {1: 2, 3: 4}
        self.ref = None
        pass

    def getStateFor(self, jellyer):
        return self.snapshot()

    def unjellyFor(self, unjellyer, data):
        # The way to handle circular references in spread
        unjellyer.unjellyInto(self, "__dict__", data[1])
        return self

    def __setitem__(self, name, value):
        # Needed by twisted spread to handle circular references
        setattr(self, name, value)

    def __repr__(self):
        return "<%s: %s>" % (type(self).__name__, repr(self.__dict__))

    def __eq__(self, value):
        return (value is self
                or (self.str == value.str
                    and self.unicode == value.unicode
                    and self.int == value.int
                    and self.long == value.long
                    and abs(self.float - value.float) < 0.00000001
                    and self.bool == value.bool
                    and self.none == value.none
                    and self.list == value.list
                    and self.tuple == value.tuple
                    and self.set == value.set
                    and self.dict == value.dict
                    and self.ref == value.ref))

jelly.setUnjellyableForClass(qual(SerializableDummy),
                             SerializableDummy)


class TestTypeSerializationDummy(object):
    pass


class MetaTestTypeSerializationDummy(type):
    pass


class TestTypeSerializationDummyWithMeta(object):
    __metaclass__ = MetaTestTypeSerializationDummy


class ConverterTest(common.TestCase):
    '''Base classes for convert test cases.

    Sub-classes should override convertion_table() to return
    an iterator on a list of records containing::

        (INPUT_TYPE, [POSSIBLE_INPUT_VALUES],
         OUTPUT_TYPE, [POSSIBLE_OUTPUT_VALUES],
         SHOULD_BE_COPIED)

    To test a pair of converters, one should inherit from this
    base class and override convertion_table() for the pair of
    converters. Then create a class for each conversion
    way inheriting from it, one with the SerializerMixin
    and one with UnserializerMixin.

    These classes have to override setUp() and initialize some attributes:

      - self.serializer : the L{IConverter} to serialize.
      - self.unserializer : the L{IConverter} to unserialize or None.

    Child class can use checkSymmetry() to check the symmetry to check
    symmetry with other serializer/unserializer..

    See test_common_serialization_pytree.py for examples.
    '''

    def testUnserialization(self):

        def inverter(gen):
            while True:
                record = gen.next()
                if len(record) == 5:
                    t1, v1, t2, v2, c = record
                    yield t2, v2, t1, v1, c
                elif len(record) == 7:
                    t1, v1, a1, t2, v2, a2, c = record
                    yield t2, v2, a2, t1, v1, a1, c
                else:
                    self.fail("Unexpected conversion table record:\nRECORD: %r"
                              % (record, ))

        if self.unserializer is None:
            raise SkipTest("No unserializer, cannot test convertion")

        capabilities = self.unserializer.capabilities
        self.checkConvertion(inverter(self.convertion_table(capabilities)),
                             self.unserializer.convert)

    def testSerialization(self):
        if self.serializer is None:
            raise SkipTest("No serializer, cannot test convertion")

        capabilities = self.serializer.capabilities
        self.checkConvertion(self.convertion_table(capabilities),
                             self.serializer.convert)

    def testSymmetry(self):
        if self.unserializer is None:
            raise SkipTest("No unserializer, cannot test for symmetry")

        if self.serializer is None:
            raise SkipTest("No serializer, cannot test for symmetry")

        cap1 = self.unserializer.capabilities
        cap2 = self.serializer.capabilities
        capabilities = cap1.intersection(cap2)
        self.checkSymmetry(self.serializer.convert,
                           self.unserializer.convert,
                           capabilities=capabilities)

    def serialize(self, data):
        return self.serializer.convert(data)

    def unserialize(self, data):
        return self.unserializer.convert(data)

    def assertEqualButDifferent(self, value, expected):
        '''Asserts that two value are equal but are different instances.
        It will recurse python structure and object instances
        and ensure everything is equal but different.
        If the expected value contains multiple references to the same value,
        it ensures the other value contains a references to its own value.'''
        self._assertEqualButDifferent(value, expected, 0, {}, {})

    def checkConvertion(self, table, converter):
        if table is None:
            raise SkipTest("No convertion table")
        for record in table:
            if len(record) == 5:
                _t1, v1, t2, v2, c = record
                values = v1
                exp_type = t2
                exp_values = v2
                should_be_copied = c
            elif len(record) == 7:
                _t1, v1, _a1, t2, v2, a2, c = record
                values = v1
                exp_type = t2
                exp_values = v2 + a2
                should_be_copied = c
            else:
                self.fail("Unexpected conversion table record:\nRECORD: %r"
                          % (record, ))

            for value in values:
                # For each conversion table entries
                # Only check the value, not the alternatives
                self.log("Checking conversion of %r (%s), expecting: %s",
                         value, exp_type.__name__,
                         ", ".join([repr(v) for v in exp_values]))

                result = converter(value)

                # Check type
                self.assertTrue(isinstance(result, exp_type),
                                 "Converted value with type %s instead "
                                 "of %s:\nVALUE: %r"
                                 % (type(result).__name__,
                                    exp_type.__name__, result))

                # Check it's a copy, if required
                if should_be_copied:
                    self.assertIsNot(value, result,
                                     "Input value and converted value "
                                     "are a same instances:\nVALUE: %r"
                                     % (value, ))

                # Look for an expected value
                for expected in exp_values:
                    # For each possible expected values
                    if self.safe_equal(expected, result):
                        break
                else:
                    self.fail("Value not converted to one of the expected "
                              "values:\nVALUE:    %r\nRESULT:   %r\n%s"
                              % (value, result,
                                 "\n".join(["EXPECTED: " + repr(v)
                                            for v in exp_values])))

    def checkSymmetry(self, serializer, deserializer, capabilities=None):
        if capabilities is None:
            capabilities = base.DEFAULT_CAPABILITIES

        for exp_type, values, must_change in self.symmetry_table(capabilities):
            for value in values:
                self.log("Checking symmetry for %r (%s)",
                         value, exp_type.__name__)
                self.assertTrue(issubclass(type(value), exp_type),
                                "Expecting value %r to have type %s, not %s"
                                % (value, exp_type, type(value)))
                data = serializer(value)
                result = deserializer(data)
                self.assertTrue(issubclass(type(result), exp_type),
                                "Expecting result %r to have type %s, not %s"
                                % (result, exp_type, type(result)))
                for v in values:
                    if self.safe_equal(v, result):
                        expected = v
                        break
                else:
                    print "="*80, "VALUE"
                    import pprint
                    pprint.pprint(value)
                    print "-"*80, "DATA"
                    pprint.pprint(data)
                    print "-"*80, "RESULT"
                    pprint.pprint(result)
                    for v in values:
                        print "-"*80, "EXPECTED"
                        pprint.pprint(result)
                    print "="*80
                    self.fail("Value not one of the expected values:\n"
                              "VALUE:    %r\nRESULT:   %r\n%s"
                              % (value, result,
                                 "\n".join(["EXPECTED: " + repr(v)
                                            for v in values])))
                if must_change:
                    self.assertEqualButDifferent(result, expected)

    def convertion_table(self, capabilities):
        raise NotImplementedError()

    def symmetry_table(self, capabilities):

        from datetime import datetime

        valdesc = [(Capabilities.int_values, Capabilities.int_keys,
                    int, [0, -42, 42]),
                   (Capabilities.long_values, Capabilities.int_values,
                    long, [0L, -2**66, 2**66]),
                   (Capabilities.float_values, Capabilities.float_keys,
                   float, [0.0, 3.14159, -3.14159, 1.23145e23, 1.23145e-23]),
                   (Capabilities.str_values, Capabilities.str_keys,
                    str, ["", "spam", "\x00", "\n"]),
                   (Capabilities.unicode_values, Capabilities.unicode_keys,
                    unicode, [u"", u"hétérogénéité", u"\x00\n"]),
                   (Capabilities.bool_values, Capabilities.bool_keys,
                    bool, [True, False]),
                   (Capabilities.none_values, Capabilities.none_keys,
                    type(None), [None])]

        if Capabilities.meta_types in capabilities:
            valdesc.append((Capabilities.type_values, Capabilities.type_keys,
                            type, [int, dict, datetime,
                                   TestTypeSerializationDummy,
                                   TestTypeSerializationDummyWithMeta,
                                   SerializableDummy]))
        else:
            valdesc.append((Capabilities.type_values, Capabilities.type_keys,
                            type, [int, dict, datetime,
                                   TestTypeSerializationDummy]))

        def iter_values(desc):
            for cap, _, value_type, values in valdesc:
                if cap in capabilities:
                    for value in values:
                        yield value_type, value, False

        def iter_keys(desc):
            for _, cap, value_type, values in valdesc:
                if cap in capabilities:
                    for value in values:
                        yield value_type, value, False

        def iter_instances(desc):
            # Default instance
            yield SerializableDummy, SerializableDummy(), True
            # Modified instance
            o = SerializableDummy()

            del o.int
            del o.none

            o.str = "spam"
            o.unicode = "fúúúú"
            o.long = 2**44
            o.float = 2.7182818284
            o.bool = False
            o.list = ['a', 'b', 'c']
            o.tuple = ('d', 'e', 'f')
            o.set = set(['g', 'h', 'i'])
            o.dict = {'j': 1, 'k': 2, 'l': 3}

            yield SerializableDummy, o, True

        def iter_all_values(desc, stop=False, immutable=False):
            values = [v for _, v, _ in iter_values(desc)]
            if not immutable:
                values += [v for _, v, _ in iter_instances(desc)]
            if not stop:
                values += [v for _, v, _ in iter_tuples(desc, True, immutable)]
                if not immutable:
                    values += [v for _, v, _ in iter_lists(desc, True)]
                    values += [v for _, v, _ in iter_sets(desc, True)]
                    values += [v for _, v, _ in iter_dicts(desc, True)]
            return values

        def iter_all_keys(desc, stop=False):
            values = [v for _, v, _ in iter_values(desc)]
            if not stop:
                values += [v for _, v, _ in iter_tuples(desc, True, True)]
            return values

        def iter_tuples(desc, stop=False, immutable=False):
            yield tuple, (), False # Exception for empty tuple singleton
            # A tuple for each possible values
            for v in iter_all_values(desc, stop, immutable):
                yield tuple, tuple([v]), True
            # One big tuple with everything supported in it
            yield tuple, tuple(iter_all_values(desc, stop, immutable)), True

        def iter_lists(desc, stop=False):
            yield list, [], True
            # A list for each possible values
            for v in iter_all_values(desc, stop):
                yield list, [v], True
            # One big list with everything supported in it
            yield list, iter_all_values(desc, stop), True

        def iter_sets(desc, stop=False):
            yield set, set([]), True
            # A set for each possible values
            for v in iter_all_values(desc, stop, True):
                yield set, set([v]), True
            # One big list with everything supported in it
            yield set, set(iter_all_values(desc, stop, True)), True

        def iter_dicts(desc, stop=False):
            yield dict, {}, True
            # One a big dict for every supported values with all supported keys
            for v in iter_all_values(desc, stop):
                d = {}
                for k in iter_all_keys(desc, stop):
                    d[k] = v
                yield dict, d, True

        def iter_all(desc):
            return itertools.chain(iter_values(desc),
                                   iter_instances(desc),
                                   iter_tuples(desc),
                                   iter_lists(desc),
                                   iter_sets(desc),
                                   iter_dicts(desc))

        for record in iter_all(valdesc):
            value_type, value, should_mutate = record
            yield value_type, [value], should_mutate

        if Capabilities.circular_references in capabilities:
            # get supported values, keys and referencable
            values = iter_values(valdesc)
            _, X, _ = values.next()
            _, Y, _ = values.next()

            keys = iter_keys(valdesc)
            _, K, _ = keys.next()
            _, L, _ = keys.next()

            if Capabilities.list_values in capabilities:
                Z = [X, Y]
            elif Capabilities.tuple_values in capabilities:
                Z = (X, Y)
            elif Capabilities.set_values in capabilities:
                Z = set([X, Y])
            elif Capabilities.dict_values in capabilities:
                Z = dict([X, Y])
            else:
                self.fail("Converter support circular references but do not "
                          "supporte any referencable types")

            if Capabilities.list_values in capabilities:
                # Reference in list
                yield list, [[Z, Z]], True
                yield list, [[Z, [Z, [Z], Z], Z]], True

                # List self-references
                a = []
                a.append(a)
                yield list, [a], True

                a = []
                b = [a]
                a.append(b)
                yield list, [b], True

            if Capabilities.tuple_values in capabilities:
                # Reference in tuple
                yield tuple, [(Z, Z)], True
                yield tuple, [(Z, (Z, (Z, ), Z), Z)], True

            if Capabilities.dict_values in capabilities:
                # Reference in dictionary value
                yield dict, [{K: Z, L: Z}], True
                yield dict, [{K: Z, L: {L: Z, K: {K: Z}}}], True

                # Dictionary self-references
                a = {}
                a[1] = a
                yield dict, [a], True

                a = {}
                b = {K: a}
                a[K] = b
                yield dict, [a], True

                if (Capabilities.tuple_keys in capabilities
                    and Capabilities.list_values in capabilities):
                        a = (K, L)

                        # Dereference in dictionary keys.
                        yield list, [[a, {a: X}]], True

                        # Reference in dictionary keys.
                        yield list, [[{a: Y}, a]], True

                        # Multiple reference in dictionary keys
                        a = (K, L)
                        yield dict, [{(K, a): X, (L, a): Y}], True

            if (Capabilities.set_values in capabilities
                and Capabilities.tuple_keys in capabilities
                and Capabilities.list_values in capabilities):

                a = (K, L)
                # Dereference in set.
                yield list, [[a, set([a])]], True

                # Reference in set.
                yield list, [[set([a]), a]], True

                # Multiple reference in set
                b = set([(K, a), (L, a)])
                yield set, [b], True


            if (Capabilities.tuple_values in capabilities
                and Capabilities.list_values in capabilities
                and Capabilities.dict_values in capabilities
                and Capabilities.tuple_keys in capabilities
                and Capabilities.list_values in capabilities):

                # Complex structure
                a = (K, L)
                b = (a, )
                b2 = set(b)
                c = (a, b)
                c2 = {a: b2, b: c}
                d = (a, b, c)
                d2 = [a, b2, c2]
                e = (b, c, d)
                e2 = [b2, c2, e]
                c2[e] = e2 # Make a cycle
                yield dict, [{b: b2, c: c2, d: d2, e: e2}], True

            if Capabilities.instance_values in capabilities:
                # complex references in instances
                o1 = SerializableDummy()
                o2 = SerializableDummy()
                o3 = SerializableDummy()

                o1.dict = {1: 1}
                o2.tuple = (2, )
                o3.list = [3]

                o1.ref = o2
                o2.ref = o1
                o3.ref = o3
                o1.list = o3.list
                o2.dict = o1.dict
                o3.tuple = o2.tuple

                yield SerializableDummy, [o1], True
                yield SerializableDummy, [o2], True
                yield SerializableDummy, [o3], True

                if Capabilities.list_values in capabilities:
                    yield list, [[o1, o2]], True
                    yield list, [[o2, o1]], True
                    yield list, [[o1, o3]], True
                    yield list, [[o3, o1]], True
                    yield list, [[o2, o3]], True
                    yield list, [[o3, o2]], True
                    yield list, [[o1, o2, o3]], True
                    yield list, [[o3, o1, o2]], True

    def safe_equal(self, a, b):
        '''Circular references safe comparator.
        The two values must have the same internal references,
        meaning if a contains multiple references to the same
        object, b should equivalent values should be references
        too but do not need to be references to the same object,
        the object just have to be equals.'''
        return self._safe_equal(a, b, 0, {}, {})

    ### Private Methods ###

    def _safe_equal(self, a, b, idx, arefs, brefs):
        if a is b:
            return True

        if type(a) != type(b):
            return False

        if isinstance(a, float):
            return abs(a - b) < 0.000001

        if isinstance(a, (int, long, str, unicode, bool, type(None))):
            return a == b

        aid = id(a)
        bid = id(b)

        if aid in arefs:
            # first value is a reference, check the other value is too
            if bid not in brefs:
                return False
            # Check the two reference the same value inside the structure
            return arefs[aid] == brefs[bid]

        if bid in brefs:
            return False

        arefs[aid] = idx
        brefs[bid] = idx

        if isinstance(a, (tuple, list)):
            if len(a) != len(b):
                return False
            for v1, v2 in zip(a, b):
                if not self._safe_equal(v1, v2, idx + 1, arefs, brefs):
                    return False
                idx += 1
            return True

        if isinstance(a, set):
            if len(a) != len(b):
                return False
            for k1 in a:
                for k2 in b:
                    # We keep a copy of the reference dictionaries
                    # because if the comparison fail we don't want to pollute
                    # them with invalid references
                    acopy = dict(arefs)
                    bcopy = dict(brefs)
                    if self._safe_equal(k1, k2, idx + 1, acopy, bcopy):
                        arefs.update(acopy)
                        brefs.update(bcopy)
                        break
                else:
                    # Not equal key found in b
                    return False
                idx += 1
            return True

        if isinstance(a, (dict, types.DictProxyType)):
            if len(a) != len(b):
                return False
            for k1, v1 in a.iteritems():
                for k2, v2 in b.iteritems():
                    # We keep a copy of copy of the reference dictionaries
                    # because if the comparison fail we don't want to pollute
                    # them with invalid references
                    acopy = dict(arefs)
                    bcopy = dict(brefs)
                    if self._safe_equal(k1, k2, idx + 1, acopy, bcopy):
                        if not self._safe_equal(v1, v2, idx + 2, arefs, brefs):
                            return False
                        arefs.update(acopy)
                        brefs.update(bcopy)
                        break
                else:
                    # Not key found
                    return False
                idx += 2
            return True

        if hasattr(a, "__dict__"):
            return self._safe_equal(a.__dict__, b.__dict__,
                                    idx + 1, arefs, brefs)

        if hasattr(a, "__slots__"):
            for attr in a.__slots__:
                v1 = getattr(a, attr)
                v2 = getattr(b, attr)
                if not self._safe_equal(v1, v2, idx + 1, arefs, brefs):
                    return False
            return True

        raise RuntimeError("I don't know how to compare %r and %r" % (a, b))

    def _assertEqualButDifferent(self, value, expected, idx, valids, expids):
        '''idx is used to identify every values uniquely to be able to verify
        references are made to the same value, valids and expids are
        dictionaries with instance id() for key and idx for value.'''

        # Only check references for type that can be referenced.
        # Let the immutable type do what they want, sometime strings
        # are interned sometime no, we don't care.
        if not isinstance(expected, (int, long, float, bool,
                                     str, unicode, type(None))):
            # Get unique instance identifiers
            expid = id(expected)
            valid = id(value)

            if expid in expids:
                # Expected value is a reference, check the other value is too
                self.assertTrue(valid in valids)
                # Check the two reference the same value inside the structure
                self.assertEqual(valids[valid], expids[expid])
                return idx

            # Check the other value is not a reference if it wasn't expected
            self.assertFalse(valid in valids)

            # Store the instance identifiers for later checks
            expids[expid] = idx
            valids[valid] = idx

        if expected is None:
            self.assertEqual(expected, value)
        elif isinstance(expected, (list, tuple)):
            if expected != (): # Special case for tuple singleton
                self.assertIsNot(expected, value)

            self.assertEqual(len(expected), len(value))
            for exp, val in zip(expected, value):
                idx = self._assertEqualButDifferent(val, exp, idx + 1,
                                                    valids, expids)
        elif isinstance(expected, set):
            self.assertEqual(len(expected), len(value))
            for exp in expected:
                self.assertTrue(exp in value)
                val = [v for v in value if v == exp][0]
                idx = self._assertEqualButDifferent(val, exp, idx + 1,
                                                    valids, expids)
        elif isinstance(expected, dict):
            self.assertEqual(len(expected), len(value))
            for exp_key, exp_val in expected.items():
                self.assertTrue(exp_key in value)
                val_key = [k for k in value if k == exp_key][0]
                val_val = value[val_key]
                idx = self._assertEqualButDifferent(val_key, exp_key, idx + 1,
                                                    valids, expids)
                idx = self._assertEqualButDifferent(val_val, exp_val, idx + 1,
                                                    valids, expids)
        elif isinstance(value, float):
            self.assertAlmostEqual(value, expected)
        elif isinstance(value, (int, long, bool, str, unicode, type)):
            self.assertEqual(value, expected)
        else:
            self.assertIsNot(expected, value)
            if ISerializable.providedBy(expected):
                self.assertTrue(ISerializable.providedBy(value))
            idx = self._assertEqualButDifferent(value.__dict__,
                                                expected.__dict__,
                                                idx + 1,
                                                valids, expids)
        return idx

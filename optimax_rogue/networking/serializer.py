"""This module is used for defining a standard set of functions that can be used
for transmitting data across the network.

Typical usage is as follows:
import optimax_rogue.networking.serializer as ser

class MyClass(ser.Serializable):
    def to_prims(self) -> typing.Any:
        return self.__dict__.copy() # may be omitted for this implementation

    @classmethod
    def from_prims(cls, prims) -> 'MyClass':
        return cls(**prims) # may be omitted for this implementation

    @classmethod
    def identifier(self) -> str:
        return 'my_class' # may be omitted for package + snake case of class

ser.register(M)

# to serialize
recov = ser.deserialize(ser.serialize(MyClass()))
"""

import typing
import json
import inflection
import base64


class Serializer:
    """The interface that anything that is capable of serialization must
    implement"""

    def serialize(self, val: typing.Any) -> bytes:
        """Converts the specified value, which may be a dict, list, set, number, string,
        or tuple into bytes format."""
        raise NotImplementedError

    def deserialize(self, serd: bytes) -> typing.Any:
        """Converts back from the specified value. This operation may lose the distinction
        between lists and tuples, but if it does so it must prefer lists"""
        raise NotImplementedError

class JsonSerializer(Serializer):
    """Serializes using the json format. Tuples are converted to lists"""

    def serialize(self, val: typing.Any) -> bytes:
        """Serializes the value to json format"""
        return json.dumps(val).encode(encoding='ASCII', errors='strict')

    def deserialize(self, serd: bytes) -> typing.Any:
        """Deserializes the value from json format"""
        return json.loads(serd.decode(encoding='ASCII', errors='strict'))

class Serializable:
    """This is the base class for anything that can be serialized.
    """

    def to_prims(self) -> typing.Any:
        """Converts this object to a collection of primitives"""
        return self.__dict__.copy()

    def to_prims_embeddable(self) -> str:
        """Converts this object to a collection of primitives *except* bytes"""
        res = self.to_prims()
        if SERIALIZER_SUPPORTS_BYTES or not self.has_custom_serializer():
            return res
        return base64.a85encode(res).decode('ASCII', 'strict')

    @classmethod
    def from_prims_embeddable(cls, prims: str) -> 'Serializable':
        """Converts the result of to_prims_embeddable back to an instance"""
        if SERIALIZER_SUPPORTS_BYTES or not cls.has_custom_serializer():
            return cls.from_prims(prims)
        return cls.from_prims(base64.a85decode(prims))

    @classmethod
    def from_prims(cls, prims) -> 'Serializable':
        """Converts from the primitives back into an instance"""
        return cls(**prims)

    @classmethod
    def identifier(cls) -> str:
        """Gets a unique identifier for this class"""
        cname = inflection.underscore(cls.__name__)
        return cls.__module__ + '.' + cname

    @classmethod
    def has_custom_serializer(cls) -> bool:
        """If this returns true, to_prims must return a bytes array and
        from_prims must accept one"""
        return False

class SerializableDict(Serializable):
    """A light wrapper around a dict that acts much like a dictionary does
    but supports the serializable syntax

    Attributes:
        attrs (dict): the real attributes
    """
    def __init__(self, attrs: dict = None):
        self.attrs = attrs if attrs is not None else dict()

    def __getitem__(self, attr_name):
        return self.attrs[attr_name]

    def __setitem__(self, attr_name, attr_val):
        self.attrs[attr_name] = attr_val

    def to_prims(self):
        return self.attrs.copy()

    @classmethod
    def from_prims(cls, prims):
        return cls(prims)

    def __repr__(self):
        return repr(self.attrs)

IDENS_TO_TYPE = dict()
SERIALIZER_SUPPORTS_BYTES = False
SERIALIZER = JsonSerializer()

def register(ser: type) -> None:
    """Registers the specified serializable such that it can be deserialized"""
    IDENS_TO_TYPE[ser.identifier()] = ser

def serialize_embeddable(obj: Serializable) -> typing.Any:
    """Serializes the given object in an embeddable way"""
    return {'iden': obj.identifier(), 'prims': obj.to_prims_embeddable()}

def _debug_dump(obj: Serializable):
    """Tries to fairly determine why something will fail to serialize"""
    print(f'[serializer] dumping {obj} (type={type(obj)})')
    for key, val in obj.__dict__.items():
        print(f'[serializer]   {key} -> {val} (type={type(val)})')
        if isinstance(val, Serializable):
            _debug_dump(val)

def serialize(obj: Serializable) -> bytes:
    """Serializes the given object"""
    try:
        return SERIALIZER.serialize(serialize_embeddable(obj))
    except:
        _debug_dump(obj)
        raise

def peek_type_embeddable(serd: typing.Any) -> typing.Type:
    """Returns the type of the serialized embeddable"""
    return IDENS_TO_TYPE[serd['iden']]

def deserialize_embeddable(serd: typing.Any) -> Serializable:
    """Deserializes the result from serialize_embeddable() back into the object"""
    typ = peek_type_embeddable(serd)
    return typ.from_prims_embeddable(serd['prims'])

def deserialize(serd: bytes) -> Serializable:
    """Deserializes the result from serialize() back into the object"""
    return deserialize_embeddable(SERIALIZER.deserialize(serd))

register(SerializableDict)

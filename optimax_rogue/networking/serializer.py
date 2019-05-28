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
import io
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
        arr = io.BytesIO()
        json.dump(val, arr)
        return arr.getvalue()

    def deserialize(self, serd: bytes) -> typing.Any:
        """Deserializes the value from json format"""
        arr = io.BytesIO(serd)
        arr.seek(0, 0)
        return json.load(arr)

class Serializable:
    """This is the base class for anything that can be serialized.
    """

    def to_prims(self) -> typing.Any:
        """Converts this object to a collection of primitives"""
        return self.__dict__.copy()

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

IDENS_TO_TYPE = dict()
SERIALIZER = JsonSerializer()
SERIALIZER_SUPPORTS_BYTES = False

def register(ser: type) -> None:
    """Registers the specified serializable such that it can be deserialized"""
    IDENS_TO_TYPE[ser.identifier()] = ser

def serialize(obj: Serializable) -> bytes:
    """Serializes the given object"""
    if SERIALIZER_SUPPORTS_BYTES or not obj.has_custom_serializer():
        return SERIALIZER.serialize({'iden': obj.identifier(), 'prims': obj.to_prims()})

    serd = obj.to_prims()
    serd_b64 = base64.a85encode(serd)
    return SERIALIZER.serialize({'iden': obj.identifier(), 'prims': serd_b64})

def deserialize(serd: bytes) -> Serializable:
    """Deserializes the result from serialize() back into the object"""
    serd = SERIALIZER.deserialize(serd)

    typ = IDENS_TO_TYPE[serd['iden']]
    if SERIALIZER_SUPPORTS_BYTES or not typ.has_custom_serializer():
        return typ.from_prims(serd['prims'])

    serd_b64 = serd['prims']
    serd_v = base64.a85decode(serd_b64)
    return typ.from_prims(serd_v)

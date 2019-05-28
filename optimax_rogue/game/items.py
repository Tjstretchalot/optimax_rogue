"""Describes items that a unit can have."""
import optimax_rogue.networking.serializer as ser

class Item(ser.Serializable):
    """Describes a single item, unattached to anything.
    """

    @property
    def name(self) -> str:
        """Returns a pretty name for this item"""
        raise NotImplementedError

    @property
    def stack_size(self) -> int:
        """Returns the stack size for this item"""
        return 1

    def on_try_pickup(self, entity: 'Entity') -> bool:
        """Invoked when the given entity tries to pick this object up.
        Returns True if the item should be added to the entities inventory
        and removed from the world, False otherwise. Will be invoked even
        if the entity doesn't have any inventory space"""
        return entity.has_room(self)

    def on_pickup(self, entity: 'Entity') -> None:
        """Invoked when the item has been successfully picked up by the specified
        entity"""
        pass

    def on_dropped(self, entity: 'Entity') -> None:
        """Invoked when this object is dropped by the given entity"""
        pass

    def usable(self, entity: 'Entity') -> bool:
        """Returns True if this item is usable, False otherwise"""
        return False

    def on_used(self, entity: 'Entity'):
        """Invoked when this item has been used by the specified entity"""
        pass
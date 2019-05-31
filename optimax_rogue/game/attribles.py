"""Describes an attribute that can go on an entity that is entirely
determined by the modifiers on the entity"""

class Attrible:
    """Describes some attribute on an entity that uses the modifier list

    Attributes:
        parent (Entity): the entity this attribute is on
        value (int): the last calculated value for this attrible (updated on_tick)
    """

    def __init__(self, parent: 'Entity') -> None:
        self.parent = parent
        self.value = None

    def on_tick(self, game_state: 'GameState') -> None:
        """Must be called after every tick and is used to update the current
        value"""
        pass

class MaxHealthAttrible(Attrible):
    """This attrible is for maximum health"""
    def on_tick(self, game_state: 'GameState') -> None:
        result = self.parent.base_max_health
        for mod in self.parent.modifiers:
            result += mod.flat_max_health
        self.value = result

class DamageAttrible(Attrible):
    """This attrible is for damage"""
    def on_tick(self, game_state: 'GameState') -> None:
        result = self.parent.base_damage
        for mod in self.parent.modifiers:
            result += mod.flat_damage
        self.value = result

class ArmorAttrible(Attrible):
    """This attrible is for armor"""
    def on_tick(self, game_state: 'GameState') -> None:
        result = self.parent.base_armor
        for mod in self.parent.modifiers:
            result += mod.flat_armor
        self.value = result

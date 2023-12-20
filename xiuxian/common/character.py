
class Character:
    def __init__(self, name, level=1):
        self.name = name
        self.level = level
        self.experience = 0
        self.inventory = []
        self.equipment = {}
        self.skills = []

    def set_property(self, name, value):
        self.properties[name] = value

    def get_property(self, name):
        return self.properties.get(name)

    def add_experience(self, experience):
        self.experience += experience
        if self.experience >= 100:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.experience = 0

    def add_item(self, item):
        self.inventory.append(item)

    def equip_item(self, item):
        self.equipment[item.name] = item


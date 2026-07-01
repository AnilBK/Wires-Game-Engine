import pygame


class AssetManager:
    _textures = {}

    @classmethod
    def LoadTexture(cls, path):
        if path not in cls._textures:
            cls._textures[path] = pygame.image.load(path).convert_alpha()
        return cls._textures[path]


class GameObject:
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        self.position = pygame.Vector2(0, 0)

    def SetPosition(self, new_position: pygame.Vector2) -> None:
        self.position.update(new_position)

    def GetPosition(self) -> pygame.Vector2:
        return self.position

    def Clone(self):
        raise NotImplementedError

    def RenderAt(self, surface: pygame.Surface, pos: pygame.Vector2):
        pass

    def Render(self, surface: pygame.Surface):
        pass


class Sprite(GameObject):
    def __init__(self, identifier: str, texture: str) -> None:
        super().__init__(identifier)

        self.texture_path = texture
        self.texture = AssetManager.LoadTexture(texture)

    def Clone(self):
        clone = Sprite(
            identifier=self.identifier,
            texture=self.texture_path,
        )

        clone.position = self.position.copy()

        return clone

    def Render(self, surface: pygame.Surface):
        rect = self.texture.get_rect(
            center=(int(self.position.x), int(self.position.y))
        )
        surface.blit(self.texture, rect.topleft)

    def RenderAt(self, surface: pygame.Surface, pos: pygame.Vector2):
        rect = self.texture.get_rect(center=(int(pos.x), int(pos.y)))
        surface.blit(self.texture, rect.topleft)


class Scene:
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier

        # Objects currently in the scene.
        self.nodes: list[GameObject] = []

        # Prototype objects.
        self.registered_nodes: dict[str, GameObject] = {}

    def RegisterNode(self, gameobject: GameObject) -> None:
        self.registered_nodes[gameobject.identifier] = gameobject

    def Instantiate(self, identifier: str) -> GameObject:
        prototype = self.registered_nodes[identifier]

        instance = prototype.Clone()

        self.nodes.append(instance)

        return instance

    def AddNode(self, gameobject: GameObject):
        self.nodes.append(gameobject)

    def Render(self, surface: pygame.Surface):
        for node in self.nodes:
            node.Render(surface)

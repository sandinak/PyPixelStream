from time import time
from os import mkdir, listdir, remove
from os.path import exists

import sys
import os

from .serialize.serialize import (source_to_dict,
                                  filter_to_dict,
                                  dict_to_filter,
                                  dict_to_source,
                                  load_scene_from_file)
from .scene import Scene

from json import dumps, loads
from numpy import ndarray, zeros, uint8

class Engine:

    def __init__(self,
                 size: tuple[int, int] = (48, 32),
                 path_save: str = "/saved/",
                 save_interval_seconds: int = 2) -> None:
        path_program = sys.argv[0]
        path_program = os.path.dirname(path_program)
        full_path_save = path_program + path_save

        if not exists(full_path_save):
            mkdir(full_path_save)
        
        self.path_scenes: str = full_path_save + "scenes/"
        self.path_engine_save: str = full_path_save + "engine_save.json"

        
        self.path_scenes = os.path.join(path_program, self.path_scenes)
        self.path_engine_save = os.path.join(path_program, self.path_engine_save)

        self.save_interval_seconds: int = save_interval_seconds
        self.last_save: float = time()

        if not exists(self.path_scenes):
            mkdir(self.path_scenes)
        
        self.scenes: list[Scene] = []
        self.atm_scene: Scene | None = None
        self.size: tuple[int, int] = size
        self.background: ndarray = None
        self.background_template: ndarray = None
        
        self.load_engine_save()
        self.set_background(self.size)

    def load_engine_save(self) -> None:
        
        if not exists(self.path_engine_save):
            return

        with open(self.path_engine_save, "r") as file:
            json_dict = file.read()
        
        json_dict = loads(json_dict)
        self.size = json_dict["resolution"]

        for scenes_id in listdir(self.path_scenes):
            # for removing scenes that are not in the engine save
            path = f"{self.path_scenes}/{scenes_id}"
            only_id = scenes_id.split(".")[0]
            if only_id not in json_dict["scenes_ids"]:
                remove(path)

        for scene_id in json_dict["scenes_ids"]:
            scene_dict = load_scene_from_file(scene_id, self.path_scenes)
            scene = Scene(scene_dict["name"], scene_dict["order"], scene_dict["internal_id"])

            for source in scene_dict["sources"]:
                scene.add_source(source)
            
            for filter in scene_dict["filters"]:
                scene.filters.add(filter)
            
            self.add_scene(scene)
        
        atm_scene_id = json_dict["atm_scene"]
        if atm_scene_id:
            atm_scene = None
            for scene in self.scenes:
                if scene.internal_id == atm_scene_id:
                    atm_scene = scene
                    break

            self.set_scene(atm_scene)
        
        self.order()

    def check_auto_save(self) -> None:
        if time() - self.last_save > self.save_interval_seconds:
            json_dict = {"resolution": self.size, "scenes_ids": [], "atm_scene": None}
            if self.atm_scene:
                json_dict["atm_scene"] = self.atm_scene.internal_id
            for scene in self.scenes:
                scene_id = scene.internal_id
                json_dict["scenes_ids"].append(scene_id)
            
            with open(self.path_engine_save, "w") as file:
                file.write(dumps(json_dict, indent=4))
            
            atm_scene = self.atm_scene
            if atm_scene:
                atm_scene.save(self.path_scenes)

            self.last_save = time()

    def set_background(self, size: tuple[int, int]) -> None:
        self.size = size
        self.background = zeros((size[1], size[0], 3), dtype=uint8)
        self.background_template = self.background.copy()

    def check_scene_name(self, name: str) -> None:
        for scene in self.scenes:
            if scene.name == name:
                raise ValueError(f"Scene with name '{name}' already exists")

    def order(self) -> None:
        self.scenes.sort(key=lambda scene: scene.order)
        
        for i in range(len(self.scenes)):
            self.scenes[i].order = i

    def get_scene(self, name: str) -> Scene:
        for scene in self.scenes:
            if scene.name == name:
                return scene
        raise ValueError(f"Scene with name '{name}' does not exist")

    def add_scene(self, scene: Scene) -> None:
        self.check_scene_name(scene.name)
        self.scenes.append(scene)
        scene.save(self.path_scenes)
        self.order()
        if self.atm_scene == None:
            self.set_scene(scene)

    def remove_scene(self, scene: Scene) -> None:
        scene.disconnect()
        scene = self.get_scene(scene.name)
        if scene == self.atm_scene:
            self.set_scene(None)
        self.scenes.remove(scene)
        self.order()

    def set_scene(self, scene: Scene) -> None:
        if self.atm_scene == scene:
            return
        
        if self.atm_scene:
            self.atm_scene.disconnect()
        self.atm_scene = scene
        if self.atm_scene: 
            self.atm_scene.connect()
    
    def update(self) -> bool:
        self.check_auto_save()
        if self.atm_scene:
            self.background[...] = self.background_template
            self.atm_scene.update(self.background)
            return True
        return False
    
    def duplicate_scene(self, scene: Scene) -> None:
        new_name = f"{scene.name} copy"
        while True:
            try:
                self.check_scene_name(new_name)
                break
            except ValueError:
                new_name += " copy"

        new_scene = Scene(name=new_name, order=scene.order + 0.5)

        for filter in scene.filters.filters:
            copy_filter = dict_to_filter(filter_to_dict(filter))
            new_scene.filters.add(copy_filter)
        
        for source in scene.sources:
            copy_source = dict_to_source(source_to_dict(source))
            new_scene.add_source(copy_source)

        self.add_scene(new_scene)
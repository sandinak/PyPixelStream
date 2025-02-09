from kivy.config import Config
from kivy.utils import platform

if not platform in ('android', 'ios'):
    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.core.window import Window
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock

from uix.main.main import MainContainer
from config.load_kv import load_kv_files

class Main(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_container = MainContainer()
        self.add_widget(self.main_container)

        Clock.schedule_once(self.update)
        Window.bind(on_request_close=self.on_request_close)

    def update(self, dt):
        check = self.main_container.engine.update()
        if check:
            self.main_container.interactive_resize_video.set_frame(self.main_container.engine.background)
        Clock.schedule_once(self.update)

    def on_request_close(self, *args):
        for scene in self.main_container.engine.scenes:
            scene.save(self.main_container.engine.path_scenes)
            for source in scene.sources:
                source.disconnect()

class MyApp(App):
    def build(self):
        return Main()

if __name__ == '__main__':
    load_kv_files()
    MyApp().run()
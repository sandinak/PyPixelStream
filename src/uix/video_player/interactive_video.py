from kivy.graphics import Color, Line, InstructionGroup
from kivy.metrics import dp
from numpy import ndarray

from engine_2d.source import Source
from .render_engine import VideoRender

class InteractiveVideoRender(VideoRender):

    def __init__(self,
                 size: tuple[int, int],
                 source_list: list[Source],
                 selection_color: tuple[int, int, int] = (255, 0, 0),
                 selection_callback: callable = None,
                 deselect_callback: callable = None,
                 **kwargs):
        
        super().__init__(size, **kwargs)
        self.source_list: list[Source] = source_list
        self.selected_source: Source | None = None
        self._selection_box: InstructionGroup | None = None
        self.selection_color: tuple[int, int, int] = selection_color
        self.touch_offset: dict[str, int] = {'x': 0, 'y': 0}
        self.selection_callback = selection_callback
        self.deselect_callback = deselect_callback

    def change_source_list(self, source_list: list[Source], callback=True):
        self.deselect_source(callback=callback)
        self.source_list = source_list
        self._refresh_selection_box()

    def set_frame(self, rgb_data: ndarray):
        super().set_frame(rgb_data)
        if self.selected_source:
            self._refresh_selection_box()

    def select_source(self, source: Source, callback=True):
        
        if source == self.selected_source:
            return

        if self.selected_source:
            self._remove_selection_box()
            self.selected_source.set_selected(False)
        self.selected_source = source
        self.selected_source.set_selected(True)
        self._add_selection_box(source)
        if callback and self.selection_callback:
            self.selection_callback(source)

    def deselect_source(self, callback=True):
        if self.selected_source:
            self.selected_source.set_selected(False)
            self._remove_selection_box()
        self.selected_source = None
        if callback and self.deselect_callback:
            self.deselect_callback()

    def handle_selection(self, source: Source):
        if source != self.selected_source:
            self.deselect_source()
            self.select_source(source)

    def on_touch_down(self, touch):
        if touch.button == 'scrolldown' or touch.button == 'scrollup':
            super().on_touch_down(touch)
            return
        source = self._get_source_from_click(touch)
        if source:
            self.handle_selection(source)
            if self.selected_source is None:
                return
            touch_x, touch_y = self._get_scaled_touch_position(touch)
            self.touch_offset = {'x': touch_x - self.selected_source.x,
                                  'y': touch_y - (self.selected_source.y + self.selected_source.height)}
            return
        self.deselect_source()

    def on_touch_move(self, touch):
        if self.selected_source is not None:
            touch_x, touch_y = self._get_scaled_touch_position(touch)
            new_x = int(touch_x - self.touch_offset['x'])
            new_y = int(touch_y - self.touch_offset['y'])
            new_y = new_y - self.selected_source.height
            self.selected_source.set_position((new_x, new_y))
            self._refresh_selection_box()

    def _get_scaled_touch_position(self, touch):
        rect_pos, rect_size = self.get_image_position_and_size()
        scale_x = rect_size[0] / self._size[0]
        touch_x = (touch.x - rect_pos[0]) / scale_x
        touch_y = (1 - ((touch.y - rect_pos[1]) / rect_size[1])) * self._size[1]
        return touch_x, touch_y

    def _is_touch_within_bounds(self, touch, pos, size):
        return pos[0] <= touch.x <= pos[0] + size[0] and pos[1] <= touch.y <= pos[1] + size[1]

    def _get_source_from_touch(self, touch, source: Source):
        pos, size = self._scale_source_to_widget(source)
        if self._is_touch_within_bounds(touch, pos, size):
            return source
        return None

    def _get_source_from_click(self, touch):
        if self.selected_source and self._get_source_from_touch(touch, self.selected_source):
            if self.selected_source.is_selectable:
                return self.selected_source

        reversed_source_list = sorted(self.source_list, key=lambda x: x.order, reverse=True)
        for source in reversed_source_list:
            if self._get_source_from_touch(touch, source):
                if source.is_selectable:
                    return source
        return None

    def _add_selection_box(self, source: Source):
        pos, size = self._scale_source_to_widget(source)
        if self._selection_box:
            self._remove_selection_box()
        if self.selected_source and self.selected_source.is_selectable:
            self._selection_box = self._create_selection_box(pos, size)
            self.canvas.add(self._selection_box)

    def _refresh_selection_box(self):
        self._remove_selection_box()
        if self.selected_source:
            self._add_selection_box(self.selected_source)

    def _create_selection_box(self, pos, size):
        selection_box = InstructionGroup()
        selection_box.add(Color(*self.selection_color))

        points = [
            [pos[0], pos[1], pos[0] + size[0], pos[1]],
            [pos[0], pos[1], pos[0], pos[1] + size[1]],
            [pos[0] + size[0], pos[1], pos[0] + size[0], pos[1] + size[1]],
            [pos[0], pos[1] + size[1], pos[0] + size[0], pos[1] + size[1]]
        ]
        for point in points:
            selection_box.add(Line(points=point, width=dp(2)))

        return selection_box

    def _remove_selection_box(self):
        if self._selection_box:
            self.canvas.remove(self._selection_box)
            self._selection_box = None

    def _scale_source_to_widget(self, source: Source):
        rect_pos, rect_size = self.get_image_position_and_size()
        scale_x = rect_size[0] / self._size[0]
        scale_y = rect_size[1] / self._size[1]
        
        formated_x = int(source.x)
        formated_y = int(source.y)
        
        pos = [formated_x * scale_x + rect_pos[0], 
               (1 - (formated_y + source.height) / self._size[1]) * rect_size[1] + rect_pos[1]]
        size = [source.width * scale_x, source.height * scale_y]
        return pos, size
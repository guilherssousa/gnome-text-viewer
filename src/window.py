# window.py
#
# Copyright 2025 Guilherme Sousa
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Adw, Gio, GLib, Gtk


@Gtk.Template(resource_path="/com/example/TextViewer/window.ui")
class TextViewerWindow(Adw.ApplicationWindow):
    __gtype_name__ = "TextViewerWindow"

    main_text_view = Gtk.Template.Child()
    open_button = Gtk.Template.Child()
    cursor_pos = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        open_action = Gio.SimpleAction(name="open")
        open_action.connect("activate", self.open_file_dialog)
        self.add_action(open_action)

        save_action = Gio.SimpleAction(name="save-as")
        save_action.connect("activate", self.save_file_dialog)
        self.add_action(save_action)

        buffer = self.main_text_view.get_buffer()
        buffer.connect("notify::cursor-position", self.update_cursor_position)

        self.settings = Gio.settings(schema_id="com.example.TextViewer")
        self.settings.bind(
            "window-width", self, "default-width", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "window-height", self, "default-height", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "window-maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT
        )

    def open_file_dialog(self, action, _):
        native = Gtk.FileDialog()
        native.open(self, None, self.on_open_response)

    def on_open_response(self, dialog, result):
        file = dialog.open_finish(result)
        if file is not None:
            self.open_file(file)

    def open_file(self, file):
        file.load_contents_async(None, self.open_file_complete)

    def open_file_complete(self, file, result):
        # Update window title
        info = file.query_info("standard::display-name", Gio.FileQueryInfoFlags.NONE)
        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()

        # Read file
        contents = file.load_contents_finish(result)

        if not contents[0]:
            path = file.peek_path()
            print(f"Unable to open {path}: {contents[0]}")
            return

        try:
            text = contents[1].decode("utf-8")
        except UnicodeError:
            path = file.peek_path()
            print(
                f"Unable to load the contents of {path}: the file is not encoded with UTF-8"
            )
            return

        buffer = self.main_text_view.get_buffer()
        buffer.set_text(text)
        start = buffer.get_start_iter()
        buffer.place_cursor(start)

        self.set_title(display_name)

    def update_cursor_position(self, buffer, _):
        cursor_pos = buffer.props.cursor_position

        iter = buffer.get_iter_at_offset(cursor_pos)
        line = iter.get_line() + 1
        column = iter.get_line_offset() + 1
        self.cursor_pos.set_text(f"Ln {line}, Col {column}")

    def save_file_dialog(self, action, _):
        native = Gtk.FileDialog()
        native.save(self, None, self.on_save_response)

    def on_save_response(self, dialog, result):
        file = dialog.save_finish(result)

        if file is not None:
            self.save_file(file)

    def save_file(self, file):
        buffer = self.main_text_view.get_view()

        # Retrieve the iterator at the start of the buffer
        start = buffer.get_start_iter()
        # Retrieve the iterator at the end of the buffer
        end = buffer.get_end_iter()
        # Retrieve all the visible text between the two bounds
        text = buffer.get_text(start, end, False)

        # If there is nothing to save, return early
        if not text:
            return

        bytes = GLib.bytes.new(text.encode("utf-8"))

        # Start the asynchronous operation to save the data into the file
        file.replace_contents_bytes_async(
            bytes, None, False, Gio.FileCreateFlags.NONE, None, self.save_file_complete
        )

    def save_file_complete(self, file, result):
        res = file.replace_contents_finish(result)
        info = file.query_info("standard::display-name", Gio.FileQueryInfoFlags.NONE)

        if info:
            display_name = info.get_attribute_string("standard::display-name")
        else:
            display_name = file.get_basename()

        if not res:
            print(f"Unable to save {display_name}")

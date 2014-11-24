#!/usr/bin/python
# Copyright (c) 2014 Cedric Bellegarde <gnumdk@gmail.com>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GObject, Gdk
from gettext import gettext as _
from time import sleep

from lollypop.config import Objects
from lollypop.database import Database
from lollypop.widgets import *
from lollypop.utils import translate_artist_name

"""
	Loading view used on db update
"""
class LoadingView(Gtk.Grid):
	def __init__(self):
		Gtk.Grid.__init__(self)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/Loading.ui')
		self.set_property('halign', Gtk.Align.CENTER)
		self.set_property('valign', Gtk.Align.CENTER)
		self.set_vexpand(True)
		self.set_hexpand(True)
		self._label = self._ui.get_object('label')
		self._label.set_label(_("Loading please wait..."))
		self.add(self._label)
		self.show_all()
		
	def remove_signals(self):
		pass
	def calculate_content_size(self):
		pass

"""
	Generic view
"""
class View(Gtk.Grid):
	def __init__(self):
		Gtk.Grid.__init__(self)
		self.set_property("orientation", Gtk.Orientation.VERTICAL)
		self.set_border_width(0)
		# Current object, used to handle context/content view
		self._object_id = None

		Objects["player"].connect("current-changed", self.current_changed)
		Objects["player"].connect("cover-changed", self.cover_changed)

	"""
		Remove signals on player object
	"""
	def remove_signals(self):
		Objects["player"].disconnect_by_func(self.current_changed)
		Objects["player"].disconnect_by_func(self.cover_changed)


	"""
		Current song changed
		Update context and content
		@param widget as unused, track id as int
	"""
	def current_changed(self, widget, track_id):
		self._update_content()
		self._update_context()

	"""
		Update album cover in view
		Do nothing here
	"""
	def cover_changed(self, widget, album_id):
		pass
	
	"""
		Calculate content size
	"""	
	def calculate_content_size(self):
		pass
		
#######################
# PRIVATE             #
#######################

	"""
		Update content view
		Do nothing here
	"""
	def _update_content(self):
		pass

	"""
		Update context view
		Do nothing here
	"""
	def _update_context(self):
		pass


"""
	Artist view is a vertical grid with album songs widgets
"""
class ArtistView(View):

	"""
		Init ArtistView ui with a scrolled grid of AlbumWidgetSongs
	"""
	def __init__(self, artist_id, genre_id):
		View.__init__(self)
		self.set_property("orientation", Gtk.Orientation.VERTICAL)
		self._ui = Gtk.Builder()
		self._ui.add_from_resource('/org/gnome/Lollypop/ArtistView.ui')
		
		self._genre_id = genre_id
		self._object_id = artist_id

		self._size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

		artist_name = Objects["artists"].get_name(artist_id)
		artist_name = translate_artist_name(artist_name)
		self._ui.get_object('artist').set_label(artist_name)

		self._albumbox = Gtk.Grid()
		if Objects["settings"].get_value('dark-view'):
			self.get_style_context().add_class('black')
		self._albumbox.set_property("orientation", Gtk.Orientation.VERTICAL)
		self._scrolledWindow = Gtk.ScrolledWindow()
		self._scrolledWindow.set_vexpand(True)
		self._scrolledWindow.set_hexpand(True)
		self._scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC,
						Gtk.PolicyType.AUTOMATIC)
		self._scrolledWindow.add(self._albumbox)

		self.add(self._ui.get_object('ArtistView'))
		self.add(self._scrolledWindow)
		self.show_all()

	"""
		Populate the view, can be threaded
	"""
	def populate(self):
		sql = Objects["db"].get_cursor()
		if self._object_id == COMPILATIONS:
			albums = Objects["albums"].get_compilations(self._genre_id, sql)
		elif self._genre_id == ALL:
			albums = Objects["albums"].get_ids(self._object_id, None, sql)
		else:
			albums = Objects["albums"].get_ids(self._object_id, self._genre_id, sql)
		GLib.idle_add(self._add_albums, albums)

	"""
		Update album cover in view
		@param album id as int
	"""
	def cover_changed(self, widget, album_id):
		for widget in self._albumbox.get_children():
			widget.update_cover(album_id)

	"""
		Update view class, dark if dark is True
		@param bool
	"""
	def update_class(self, dark):
		if dark:
			self._albumbox.get_style_context().add_class('black')
		else:
			self._albumbox.get_style_context().remove_class('black')

	"""
		Calculate content size
	"""	
	def calculate_content_size(self):
		for widget in self._albumbox.get_children():
			widget.update_content_width(self.get_allocated_width())

#######################
# PRIVATE             #
#######################

	"""
		Update the content view
	"""
	def _update_content(self):
		track_id = Objects["player"].get_current_track_id()
		artist_id = Objects["tracks"].get_artist_id(track_id)
		if self._albumbox:
			for widget in self._albumbox.get_children():
				widget.update_playing_track(track_id)

	"""
		Pop an album and add it to the view,
		repeat operation until album list is empty
		@param [album ids as int]
	"""
	def _add_albums(self, albums):
		if len(albums) > 0:
			widget = ArtistWidget(albums.pop(0), self._genre_id, True, self._size_group)
			widget.show()
			self._albumbox.add(widget)
			GLib.idle_add(self._add_albums, albums, priority=GLib.PRIORITY_LOW)

"""
	Album view is a flowbox of albums widgets with album name and artist name
"""
class AlbumView(View):

	"""
		Init album view ui with a scrolled flow box and a scrolled context view
	"""
	def __init__(self, genre_id):
		View.__init__(self)
		self._genre_id = genre_id
		self._albumsongs = None

		self._albumbox = Gtk.FlowBox()
		if Objects["settings"].get_value('dark-view'):
			self._albumbox.get_style_context().add_class('black')

		self._albumbox.set_selection_mode(Gtk.SelectionMode.NONE)
		self._albumbox.connect("child-activated", self._on_album_activated)
		self._albumbox.set_max_children_per_line(100)
		self._scrolledWindow = Gtk.ScrolledWindow()
		self._scrolledWindow.set_vexpand(True)
		self._scrolledWindow.set_hexpand(True)
		viewport = Gtk.Viewport()
		viewport.add(self._albumbox)
		viewport.set_property("valign", Gtk.Align.START)
		self._scrolledWindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scrolledWindow.add(viewport)
		self._scrolledWindow.show_all()
		
		self._stack = Gtk.Stack()
		self._stack.set_transition_duration(500)
		self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
		self._stack.show()
		
		self._scrolledContext = Gtk.ScrolledWindow()
		self._scrolledContext.set_min_content_height(250)
		self._scrolledContext.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
		self._scrolledContext.add(self._stack)

		separator = Gtk.Separator()
		separator.show()
		
		self.add(self._scrolledWindow)
		self.add(separator)
		self.add(self._scrolledContext)
		self.show()

	"""
		Populate albums, can be threaded
	"""	
	def populate(self):
		sql = Objects["db"].get_cursor()
		if self._genre_id == ALL:
			albums = Objects["albums"].get_ids(None, None, sql)
		elif self._genre_id == POPULARS:
			albums = Objects["albums"].get_populars(sql)
		else:
			albums = Objects["albums"].get_compilations(self._genre_id, sql)
			albums += Objects["albums"].get_ids(None, self._genre_id, sql)

		GLib.idle_add(self._add_albums, albums)
	
	"""
		Update album cover in view
		@param widget as unused, album id as int
	"""
	def cover_changed(self, widget, album_id):
		self._stack.get_visible_child().update_cover(album_id)
		for child in self._albumbox.get_children():
			for widget in child.get_children():
				widget.update_cover(album_id)

	"""
		Update view class, dark if dark is True
		@param bool
	"""
	def update_class(self, dark):
		if dark:
			self._albumbox.get_style_context().add_class('black')
		else:
			self._albumbox.get_style_context().remove_class('black')

	"""
		Calculate content size
	"""	
	def calculate_content_size(self):
		context_widget = self._stack.get_visible_child()
		if context_widget:
			context_widget.update_content_width(self.get_allocated_width())

#######################
# PRIVATE             #
#######################
	"""
		Return next view
	"""
	def _get_next_view(self):
		for child in self._stack.get_children():
			if child != self._stack.get_visible_child():
				return child
		return None

	"""
		Update the context view
	"""
	def _update_context(self):
		track_id = Objects["player"].get_current_track_id()
		album_id = Objects["tracks"].get_album_id(track_id)
		context_widget = self._stack.get_visible_child()
		if context_widget:
			context_widget.update_playing_track(track_id)

	"""
		populate context view
		@param album id as int
	"""
	def _populate_context(self, album_id):
		old_view = self._get_next_view()
		if old_view:
			self._stack.remove(old_view)
		view = ArtistWidget(album_id, self._genre_id, True, None)
		view.show()
		self._stack.add(view)
		self._stack.set_visible_child(view)
			
	"""
		Show Context view for activated album
		@param flowbox, children
	"""
	def _on_album_activated(self, flowbox, child):
		if self._object_id == child.get_child().get_id():
			self._object_id = None
			self._scrolledContext.hide()
		else:
			self._object_id = child.get_child().get_id()
			self._populate_context(self._object_id)
			self._scrolledContext.show()		
	
	"""
		Pop an album and add it to the view,
		repeat operation until album list is empty
		@param [album ids as int]
	"""
	def _add_albums(self, albums):
		if len(albums) > 0:
			widget = AlbumWidget(albums.pop(0))
			widget.show()
			self._albumbox.insert(widget, -1)
			GLib.idle_add(self._add_albums, albums, priority=GLib.PRIORITY_LOW)


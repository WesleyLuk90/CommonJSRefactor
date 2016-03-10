import sublime_plugin

valid_extensions = [".js", ".jsx"]

import os
import re

def is_js_file(path):
	for extension in valid_extensions:
		if path.endswith(extension):
			return True
	return False

def find_javascript_files(path, ignore_folders=["node_modules", ".git", "public"]):
	for entry in os.listdir(path):
		full_path = os.path.join(path, entry)
		if os.path.isfile(full_path):
			if is_js_file(full_path):
				yield full_path
		elif os.path.isdir(full_path) and not os.path.islink(full_path):
			if entry in ignore_folders:
				continue
			for dir_path in find_javascript_files(full_path):
				yield dir_path

REQUIRE_RE = re.compile("require\(['\"]([^'\"']+)['\"]\)")

class RequireReplacer(object):
	def __init__(self, paths, from_path, to_path):
		self.paths = paths
		self.from_path = from_path
		self.to_path = to_path

	def get_absolute_import_name(self):
		path, _ = os.path.splitext(self.from_path)
		norm_from_path = os.path.normpath(path)
		return norm_from_path

	def do_replace(self):
		norm_from_path = self.get_absolute_import_name()
		for path in self.paths:
			directory = os.path.dirname(path)
			def path_replacer(match):
				relative_path = match.group(1)
				if relative_path[0] != ".":
					return match.group(0)
				import_path = os.path.join(directory, relative_path)
				import_path = os.path.normpath(import_path)
				if import_path == norm_from_path:
					new_path = self.get_new_path(path)
					print ("import path is\n\t%s\n\t%s" % (path, new_path))

			with open(path, 'r') as f:
				contents = f.read()
				REQUIRE_RE.sub(path_replacer, contents)

	def get_new_import_abs(self):
		path, _ = os.path.splitext(self.to_path)
		return path

	def get_new_path(self, file):
		directory = os.path.dirname(file)
		rel_path = os.path.relpath(self.get_new_import_abs(), directory)
		rel_path = rel_path.replace("\\", "/")
		if rel_path[0] != ".":
			rel_path = "./" + rel_path
		return rel_path


class CjsRenameFileCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		file_name = self.view.file_name()
		return is_js_file(file_name)

	def run(self, edit):
		file_name = self.view.file_name()
		window = self.view.window()
		window.show_input_panel("New File Name", file_name, self.run_rename, None, None)

	def run_rename(self, new_path):
		if new_path == self.view.file_name():
			return

		if not new_path:
			return

		self.view.run_command('cjs_do_rename_file', {'new_path': new_path})

class CjsDoRenameFileCommand(sublime_plugin.TextCommand):

	def run(self, edit, new_path):
		project_data = self.view.window().extract_variables()
		javascript_files = list(find_javascript_files(project_data['project_path']))

		current_path = self.view.file_name()
		replacer = RequireReplacer(javascript_files, current_path, new_path)

		replacer.do_replace()
"""Registry manager core."""

from .utils import traverse_registry
from .config import defaults, exceptions

import os
import winreg
from pathlib import Path
from typing import Optional
from collections.abc import Mapping

#-=-=-=-#

class RegEntry(Mapping):
	"""
	Represents a single Windows Registry key and provides
	navigation, subkey, and value (variable) operations on it.
	"""

	_hives = {
		"HKCR": "HKEY_CLASSES_ROOT",
		"HKCU": "HKEY_CURRENT_USER",
		"HKLM": "HKEY_LOCAL_MACHINE",
		"HKU" : "HKEY_USERS",
		"HKCC": "HKEY_CURRENT_CONFIG"
	}

	_types = [
		"REG_SZ",
		"REG_MULTI_SZ",
		"REG_EXPAND_SZ",
		"REG_BINARY",
		"REG_QWORD",
		"REG_DWORD"
	]
	_types = {getattr(winreg, type): type for type in _types}

	#-=-=-=-#

	def __init__(self, path: str):
		"""
		Initialize self. See help(type(self)) for accurate signature.

		Parameters
		----------
			path (str):
				Registry path including the hive, either as a short alias (e.g. "HKLM")
				or a full name (e.g. "HKEY_LOCAL_MACHINE"), followed by the subkey path.

		Raises
		------
			exceptions.setup.ESC_FOUND:
				If `path` contains any of the characters
				listed in `defaults.path.ESC_CHARS`.

			exceptions.hive.NOTEXISTS:
				If the leading path segment does
				not resolve to a known registry hive.
		"""
		if any(character in path for character in defaults.path.ESC_CHARS):
			raise exceptions.setup.ESC_FOUND

		path = path.strip(os.sep)
		main = path.split(os.sep)
		main[0] = main[0].upper()

		for key, value in self._hives.items():
			main[0] = main[0].replace(value, key)

		if main[0] not in self._hives:
			raise exceptions.hive.NOTEXISTS

		main[0] = self._hives[main[0]]

		self.__hive = main[0]
		self.__path = os.sep.join(main)

	#-=-=-=-#
	# Properties, all tested

	@property
	def path(self) -> str:
		"""
		Returns
		-------
			str:
				Current registry key path with full hive name
				(e.g. "HKEY_CURRENT_USER\\Software").
		"""
		return self.__path.rstrip(os.sep)

	@property
	def path_short(self) -> str:
		"""
		Returns
		-------
			str:
				Current registry key path with short hive name
				(e.g. "HKCU\\Software").
		"""
		return os.path.join(self.hive_short, self.subkey).rstrip(os.sep)

	@property
	def hive(self) -> str:
		"""
		Returns
		-------
			str:
				Current registry key's full hive name
				(e.g. "HKEY_CURRENT_USER").
		"""
		return self.__hive

	@property
	def hive_short(self) -> str:
		"""
		Returns
		-------
			str:
				Current registry key's short hive name (e.g. "HKCU").
		"""
		return {v: k for k, v in self._hives.items()}[self.hive]

	@property
	def hive_constant(self) -> int:
		"""
		Returns
		-------
			int:
				Current registry hive's integer constant, as used by `winreg`
				(e.g. `winreg.HKEY_CURRENT_USER`).
		"""
		return getattr(winreg, self.hive)

	@property
	def subkey(self) -> str:
		"""
		Returns
		-------
			str:
				Current registry subkey's path, without the hive (e.g. "Software\\MyApp").
		"""
		return self.hive.join(self.path.split(self.hive)[1:]).strip(os.sep)

	@property
	def dirname(self) -> str:
		"""
		Returns
		-------
			str:
				Full path (with hive) of the current subkey's parent.
		"""
		return os.path.dirname(self.path)

	@property
	def dirname_short(self) -> str:
		"""
		Returns
		-------
			str:
				Short path (with short hive) of the current subkey's parent.
		"""
		return os.path.dirname(self.path_short)

	@property
	def basename(self) -> str:
		"""
		Returns
		-------
			str:
				Current registry subkey's own name (last path component).
		"""
		return self.subkey.split(os.sep)[-1]

	#-=-=-=-=-=-#
	# Checks, all tested

	def is_hive(self) -> bool:
		"""
		Determines whether the current path points at a hive root
		(i.e. has no subkey path beneath it).

		Returns
		-------
			bool:
				True if the current path is a bare hive, False otherwise.
		"""
		return self.path == self.hive

	def subkey_exists(self, key_name: Optional[str] = None) -> bool:
		"""
		Checks whether a subkey exists in the registry.

		Parameters
		----------
			key_name (optional, str):
				Name of the subkey, relative to the current subkey.
				If None, checks the current subkey itself.

		Returns
		-------
			bool:
				True if the subkey exists, False otherwise.
		"""
		try:
			with winreg.OpenKey(
				self.hive_constant,
				self._key_resolver(key_name),

				access = winreg.KEY_READ
			) as entry:
				retval = True
		except (OSError, AttributeError):
			retval = False

		return retval

	def variable_exists(self, variable_name: str) -> bool:
		"""
		Checks whether a variable (value) exists in the current subkey.

		Parameters
		----------
			variable_name (str):
				Name of the variable to check.

		Returns
		-------
			bool:
				True if the variable exists, False otherwise.

		Raises:
			OSError:
				If the current subkey itself cannot be opened for reading
				(e.g. it does not exist, or access is denied).
		"""
		# Read-only access is sufficient for an existence check, and avoids
		# raising PermissionError on keys the caller can't fully modify.
		with winreg.OpenKey(
			self.hive_constant,
			self.subkey,

			access = winreg.KEY_READ
		) as entry:
			try:
				winreg.QueryValueEx(entry, variable_name)
				retval = True
			except OSError:
				retval = False

		return retval

	def relcd(self, target: str) -> None:
		"""
		Navigates in the current registry by changing the path
		this `RegEntry` points at, in place.

		Notes
		-----
			This function treats slashes (`/`) as a
			path separator, not as a part of a name.

			It means that e.g. creating a subkey with a
			name containing a slash will not be possible.

		Parameters
		----------
			target (str):
				Relative path to navigate to, from the current subkey.
				Supports ".." segments. An empty/falsy value is a no-op.

		Raises
		------
			exceptions.hive.NOTEXISTS:
				If navigating with `target` would resolve to a path outside
				of the current hive (e.g. too many ".." segments).
		"""
		if target:
			target_path = os.path.join(self.path, target)
			target_path = os.path.normpath(target_path)

			target_path = target_path.rstrip(os.sep)

			if target_path.split(os.sep)[0] != self.hive:
				# raise so callers notice when a relative path walks outside the hive
				raise exceptions.hive.NOTEXISTS
		else:
			target_path = self.path

		self.__path = target_path

	#-=-=-=-#
	# Subkeys

	def subkeys(
		self,
		recursive: bool = False,
		absolute_paths: bool = False
	) -> tuple:
		"""
		Lists the subkeys in the current subkey.

		Parameters
		----------
			recursive (bool):
				If True, recursively lists all descendant subkeys, not just direct children.

			absolute_paths (bool):
				If True, returned paths include the hive (and are rooted at the hive),
				rather than being relative to the current subkey.

		Returns
		-------
			tuple:
				Subkey names or paths, per `absolute_paths`.

		Raises
		------
			exceptions.key.NOTEXISTS:
				If the current subkey does not exist.
		"""

		if not self.subkey_exists():
			raise exceptions.key.NOTEXISTS

		array = []

		if recursive:
			stack = [self.subkey]

			while stack:
				current = stack.pop()

				with winreg.OpenKey(
					self.hive_constant,
					current,

					access = winreg.KEY_READ
				) as entry:

					for name in self._list_subkeys(entry):
						child = os.path.join(current, name)

						if absolute_paths:
							array.append(
								os.path.join(self.hive, child).rstrip(os.sep)
							)
						else:
							if self.subkey:
								relative = child[len(self.subkey):]
								relative = relative.lstrip(os.sep)
							else:
								relative = child

							array.append(relative)

						stack.append(child)
		else:
			with winreg.OpenKey(
				self.hive_constant,
				self.subkey,

				access = winreg.KEY_READ
			) as entry:

				array = list(self._list_subkeys(entry))

				if absolute_paths:
					array = [
						os.path.join(self.path, key)
						for key in array
					]

		return tuple(array)

	def create_subkey(self, key_name: Optional[str] = None, ignore_errors: Optional[bool] = True) -> None:
		"""
		Creates a subkey in the current subkey.

		Parameters
		----------
			key_name (optional, str):
				Name of the subkey to create, relative to the current subkey.
				If omitted, creates the current subkey itself.

			ignore_errors (optional, bool):
				If True, creation proceeds even if the subkey already exists (no-op in that case).
				If None, falls back to `defaults.path.EXIST_OK`.

		Raises
		------
			exceptions.key.EXISTS:
				If the subkey already exists and `ignore_errors` (or its default) is not True.
		"""
		if ignore_errors is None:
			ignore_errors = defaults.path.exist_ok

		if self.subkey_exists(key_name) and not ignore_errors:
			raise exceptions.key.EXISTS

		winreg.CreateKey(
			self.hive_constant,
			self._key_resolver(key_name)
		)

	def remove_subkeys(self, key_name: Optional[str] = None) -> None:
		"""
		Removes a subkey along with all of its descendant subkeys and
		values, without warning or confirmation.

		Parameters
		----------
			key_name (optional, str):
				Name of the subkey to remove, relative to the current subkey.
				If None, removes the current subkey.

		Raises
		------
			exceptions.hive.REMOVE:
				If the current path is a bare hive 
				(hives themselves cannot be removed).

			exceptions.key.NOTEXISTS:
				If the current subkey does not exist.
		"""
		if self.is_hive():
			raise exceptions.hive.REMOVE

		if not self.subkey_exists():
			raise exceptions.key.NOTEXISTS

		self._iterative_remove_subkeys(
			self.hive_constant,
			self._key_resolver(key_name)
		)

	#-=-=-=-#
	# Variables, all tested

	def variables(self, key_name: Optional[str] = None) -> dict:
		"""
		Lists the variables (values) in a subkey.

		Parameters
		----------
			key_name (optional, str):
				Name of the subkey to list, relative to the current subkey.
				If omitted, lists the current subkey's variables.

		Returns
		-------
			dict:
				Variable names mapped to `[value, type]` pairs,
				as `{"name": [value, "REG_TYPE"], ...}`.

		Raises
		------
			exceptions.key.NOTEXISTS:
				If the target subkey does not exist.
		"""
		if not self.subkey_exists(key_name):
			raise exceptions.key.NOTEXISTS

		key_path = self._key_resolver(key_name)

		retval = {}

		with winreg.OpenKey(
			self.hive_constant,
			key_path,

			access = winreg.KEY_READ
		) as entry:
			counter = 0

			while True:
				try:
					keys = winreg.EnumValue(entry, counter)
					keys = list(keys)

					# Emulate self.get
					keys[1] = list(winreg.QueryValueEx(entry, keys[0]))
					keys[1][1] = self._types[keys[1][1]]

					keys = {keys[0]: keys[1]}

					retval.update(keys)

					counter += 1
				except OSError:
					break

		return retval

	def set(
		self,
		name: Optional[str] = None,
		value: Optional[object] = None,
		var_type: Optional[str] = None,
		exist_ok: Optional[bool] = None
	) -> None:
		"""
		Creates or modifies a variable in the current subkey.

		Parameters
		----------
			name (optional, str):
				Name of the variable.
				If None, falls back to `defaults.variable.VALUE`.

			value (optional, str):
				Value to store.
				If None, falls back to `defaults.variable.VALUE`.
				For "REG_MULTI_SZ", a single string is automatically wrapped into a one-item list.

			var_type (optional, str):
				Registry value type, e.g. "REG_SZ" or "SZ"
				(the "REG_" prefix is optional).

				If None, falls back to `defaults.variable.TYPE`.

			exist_ok (optional, bool):
				If True, allows overwriting an existing variable.
				If None, falls back to `defaults.variable.EXIST_OK`.

		Raises
		------
			exceptions.variable.EXISTS:
				If the variable already exists and `exist_ok` (or its default) is not True.

			AttributeError:
				If `var_type` does not resolve to a known `winreg` REG_* constant.
		"""
		if value is None:
			value = defaults.variable.value

		if var_type is None:
			var_type = defaults.variable.type

		if exist_ok is None:
			exist_ok = defaults.variable.exist_ok

		var_type_obj = var_type.lower().split("reg_")[-1]
		var_type_str = "REG_" + var_type_obj.upper()
		var_type_obj = getattr(winreg, var_type_str)

		#-=-=-=-#

		if var_type_str.endswith("MULTI_SZ"):
			if isinstance(value, str):
				value = [value]

			value = list(value)

		#-=-=-=-#

		with winreg.OpenKey(
			self.hive_constant,
			self.subkey,

			access = winreg.KEY_SET_VALUE
		) as entry:
			if self.variable_exists(name) and not exist_ok:
				raise exceptions.variable.EXISTS

			winreg.SetValueEx(entry, name, 0, var_type_obj, value)

	def get(self, variable_name: str) -> tuple:
		"""
		Retrieves a variable's value and type from the current subkey.

		Parameters
		----------
			variable_name (str):
				Name of the variable to retrieve.

		Returns
		-------
			tuple:
				(value, REG_TYPE).

		Raises
		------
			exceptions.variable.NOTEXISTS:
				If the variable does not exist.
		"""
		with winreg.OpenKey(
			self.hive_constant,
			self.subkey,

			access = winreg.KEY_READ
		) as entry:
			if not self.variable_exists(variable_name):
				raise exceptions.variable.NOTEXISTS

			retval = list(winreg.QueryValueEx(entry, variable_name))
			retval[1] = self._types[retval[1]]

		return tuple(retval)

	def rename_variable(self, variable_name: str, target_name: str) -> None:
		"""
		Renames a variable in the current subkey, preserving its value and type.

		Parameters
		----------
			variable_name (str):
				Name of the existing variable to rename.

			target_name (str):
				New name for the variable.

		Raises
		------
			exceptions.variable.EXISTS:
				If `target_name` already exists.

			exceptions.variable.NOTEXISTS:
				If `variable_name` does not exist.
		"""
		if self.variable_exists(target_name):
			raise exceptions.variable.EXISTS

		input_content, input_var_type = self.get(variable_name)
		self.remove_variable(variable_name)
		self.set(target_name, input_content, input_var_type)

	def remove_variable(self, variable_name: str) -> None:
		"""
		Removes a variable from the current subkey.

		Parameters
		----------
			variable_name (str):
				Name of the variable to remove.

		Raises
		------
			exceptions.variable.NOTEXISTS:
				If the variable does not exist.
		"""
		with winreg.OpenKey(
			self.hive_constant,
			self.subkey,

			access = winreg.KEY_ALL_ACCESS
		) as entry:
			if not self.variable_exists(variable_name):
				raise exceptions.variable.NOTEXISTS

			winreg.DeleteValue(entry, variable_name)

	#-=-=-=-=-=-#
	# Special functions

	def _list_subkeys(self, key: winreg.OpenKey):
		"""
		Yields the immediate child subkey names of an open `winreg` key handle.

		Parameters
		----------
			key (winreg.OpenKey):
				An open `winreg` key handle.

		Yields
		------
			str:
				Each direct child subkey's name.
		"""
		counter = 0

		while True:
			try:
				subkey = winreg.EnumKey(key, counter)
				yield subkey
			except OSError:
				break

			counter += 1

	def _key_resolver(self, key_name: str) -> str:
		"""
		Resolves a subkey name, relative to the current subkey, into a
		full subkey path suitable for `winreg` calls.

		Parameters
		----------
			key_name (str):
				Name of the subkey, relative to the current subkey.
				If falsy, resolves to the current subkey's own path.

		Returns
		-------
			str:
				Resolved subkey path (without hive).

		Raises
		------
			exceptions.setup.ESC_FOUND:
				If `key_name` contains any of the
				characters listed in `defaults.path.ESC_CHARS`.
		"""
		if key_name:
			key_name = str(key_name)

			if any(character in key_name for character in defaults.path.ESC_CHARS):
				raise exceptions.setup.ESC_FOUND

			key_name = key_name.lstrip(os.sep)
			key_path = os.path.join(self.subkey, key_name)
			key_path = key_path.rstrip(os.sep)
		else:
			key_path = self.subkey

		return key_path

	def _iterative_remove_subkeys(self, key, name) -> None:
		"""
		Recursively deletes a subkey and everything beneath it, using an
		explicit stack in order to not hit Python's recursion limit.

		Parameters
		----------
			key:
				An open `winreg` hive/key handle, or a hive constant.

			name:
				Path of the subkey to delete, relative to `key`.
		"""
		# Each stack entry is (parent_key_or_handle, relative_path).
		# Walk the tree first, then delete in reverse order so children
		# are removed before their parents.
		to_delete = []
		stack = [(key, name)]

		while stack:
			current_key, current_name = stack.pop()
			to_delete.append((current_key, current_name))

			with winreg.OpenKey(current_key, current_name) as entry:
				children = list(self._list_subkeys(entry))

			for child_name in children:
				stack.append(
					(current_key, os.path.join(current_name, child_name))
				)

		for parent_key, path in reversed(to_delete):
			winreg.DeleteKey(parent_key, path)

	def save(
		self,
		output: str = None,
		beautify_depth: int = 0,
		editable: bool = False,
		exist_ok: bool = True
	) -> str:
		"""
		Saves key to a `.reg` file.

		Parameters
		----------
		output (str):
			Output file path. Extension is applied automatically!
			Equals subkey name if empty.

		beautify_depth (int):
			Depth of subkeys written that will be separated by
			additional 3 newlines.
			-1 strips output file from all newlines at all.

		editable (bool):
			If False:
				Only keys containing values are written.

			If True:
				All keys are written, including empty keys.
				Values are still written for keys that contain them.

		exist_ok (bool):
			Determines if file should be forcefully written.

		Returns
		-------
		str:
			Output file path.
		"""

		if output:
			output = os.path.expanduser(output)
			output = os.path.abspath(output)
		else:
			output = self.basename

		if exist_ok is None:
			exist_ok = defaults.path.file.EXIST_OK

		extension = ".reg"

		output = str(Path(output).resolve())

		if os.path.exists(output):
			if not exist_ok:
				raise exceptions.path.file.EXISTS

			if os.path.isdir(output):
				output = os.path.join(
					output,
					self.basename
				)

		output = os.path.splitext(output)[0] + extension

		# Initialize collector array
		array = [
			"Windows Registry Editor Version 5.00",
			""
		]

		# Traverse registry
		traverse_registry(
			hkey = self.hive_constant,
			key_path = self.subkey,
			hive_constant = self.hive_constant,
			hive_name = self.hive,
			list_subkeys_fn = self._list_subkeys,
			types_dict = self._types,
			exceptions_module = exceptions,
			output_array = array,
			beautify_depth = beautify_depth,
			editable = editable,
		)

		# Remove trailing empty lines
		while array and array[-1] == "":
			array.pop()

		content = "\n".join(array)

		# Handle beautify_depth
		if beautify_depth == -1:
			while "\n" * 2 in content:
				content = content.replace(
					"\n" * 2,
					"\n"
				)
		else:
			while "\n" * 3 in content:
				content = content.replace(
					"\n" * 3,
					"\n" * 2
				)

		# Write file
		with open(output, "w", encoding = "UTF-8") as file:
			file.write(content)

		return output

	#-=-=-=-#
	# Standard Python representations

	def __str__(self) -> str:
		return self.path

	def __len__(self) -> int:
		"""Returns the total number of recursive subkeys."""
		return len(self.subkeys(recursive = True))

	def __repr__(self) -> str:
		return f"RegEntry(path='{self.path}')"

	def __int__(self) -> int:
		return self.hive_constant

	def __dir__(self) -> tuple:
		return self.subkeys(False, False)

	# Mapping methods returning native dict views
	def as_dict(self, recursive: bool = False) -> dict:
		"""Helper to build full subkey map."""
		return {
			subkey: self.variables(subkey)
			for subkey in self.subkeys(recursive = recursive)
		}

	def __iter__(self):
		"""Yields (subkey, variables) pairs so dict(self) works."""
		return iter(self.as_dict().items())

	def items(self):
		"""Returns standard dict_items view with .keys() and .values()."""
		return self.as_dict().items()

	def keys(self):
		"""Returns standard dict_keys view."""
		return self.as_dict().keys()

	def values(self):
		"""Returns standard dict_values view."""
		return self.as_dict().values()

	# Variable direct access
	def __setitem__(self, key: str, value) -> None:
		return self.set(key, value)

	def __getitem__(self, key: str):
		variables = {k.lower(): v for k, v in self.variables().items()}

		try:
			return variables[key.lower()][0]
		except KeyError:
			if self.subkey_exists(key):
				raise KeyError(
					f"{key!r} is a subkey, not a value - use reg.relcd({key!r}) "
					f"or navigate into it instead."
				) from None
			raise

	def __delitem__(self, key: str) -> None:
		return self.remove_variable(key)

	# Context manager hooks
	def __enter__(self):
		self._handle = winreg.OpenKey(self.hive_constant, self.subkey, 0, winreg.KEY_ALL_ACCESS)
		return self

	def __exit__(self, exc_type, exc_value, traceback) -> bool:
		self._handle.Close()
		self._handle = None
		return False

	#-=-=-=-=-=-#
	# Aliases

	name = basename

	key_exists = exists = subkey_exists
	var_exists = variable_exists

	navigate = nav = rel_cd = relcd

	dirs = subkeys
	mkdir = makedirs = md = make = create_subkey
	rmdir = rmtree = rd = delete_subkeys = remove_subkeys

	vars = variables
	setvar = set_variable = set
	getvar = get_variable = var = variable = get
	renvar = rename_variable
	remvar = delvar = delete_variable = remove_variable

	listdir = __dir__
	getcwd = __str__

#-=-=-=-#

entry = RegEntry
"""Utility functions."""

import os
import winreg

from .config import exceptions

#-=-=-=-#

class StringConverter:
	def str_to_bytes(value: str, encoding: str = "UTF-8") -> str:
		return bytes(value, encoding)

	def hex_to_str(value: str) -> str:
		return bytes.fromhex(value)

	#-=-=-=-=-=-#
	# Aliases

	s2b = str_to_bytes
	h2s = hex_to_string = hex_to_str

class RegFileValueFormatter:
	@staticmethod
	def hex(data: bytes) -> str:
		"""
		Formats bytes for `.reg` hexadecimal syntax.

		Example
		-------
			b"\\x12\\x54\\x03" -> "12,54,03"
		"""
		return ",".join(f"{byte:02x}" for byte in data)

	@staticmethod
	def hex_wrap(value: str, line_length: int = 78) -> str:
		"""
		Wraps long hex values with backslash continuations (regedit format).
		
		Example:
			"hex(2):01,02,03,04,05,06,..." becomes:
			"hex(2):01,02,03,04,05,06,\\\n  00,..."
		"""
		# Only wrap hex/qword values
		if not value.startswith(("hex", "qword")):
			return value
		
		if len(value) <= line_length:
			return value
		
		# Split into prefix ("hex(2):") and hex data ("31,00,20,...")
		parts = value.split(":", 1)
		prefix = parts[0] + ":"
		hex_data = parts[1]
		
		hex_bytes = hex_data.split(",")
		
		lines = []
		current_line = prefix
		
		for byte in hex_bytes:
			test_line = current_line + ("," if current_line != prefix else "") + byte
			
			if len(test_line) > line_length and current_line != prefix:
				lines.append(current_line + ",\\")
				current_line = "  " + byte # Indent continuation
			else:
				current_line = test_line
		
		if current_line:
			lines.append(current_line)
		
		return "\n".join(lines)

	@staticmethod
	def utf16(
		value,
		multi_sz: bool = False
	) -> str:
		"""
		Formats a string as UTF-16LE for `.reg` hex syntax.

		REG_MULTI_SZ requirements
		-------------------------
			- UTF-16LE strings
			- NUL between strings
			- an additional NUL terminator
		"""

		if multi_sz:
			# winreg returns REG_MULTI_SZ as list[str].
			#
			# Example:
			# ["foo", "bar"]
			#
			# becomes:
			# "foo\\0bar\\0\\0"
			value = "\0".join(value) + "\0\0"

		data = value.encode("utf-16le")

		return RegFileValueFormatter.hex(data)

	@staticmethod
	def main(
		name,

		value,
		value_type,

		types_dict,

		exceptions_module,

		optimize: bool
	):
		"""
		Converts a winreg value into a `.reg` value string.
		"""
		try:
			if value is None:
				return "hex(0):"

			if value_type not in types_dict:
				return None

			type_name = types_dict[value_type]

			# REG_SZ
			if type_name == "REG_SZ":
				value = (value
					.replace("\\", r"\\")
					.replace('"', r'\"')
				)

				return '"{}"'.format(value)

			# REG_EXPAND_SZ
			if type_name == "REG_EXPAND_SZ":
				return "hex(2):{}".format(
					RegFileValueFormatter.utf16(value)
				)

			# REG_MULTI_SZ
			if type_name == "REG_MULTI_SZ":

				# An empty REG_MULTI_SZ is still a value.
				if not value:
					return "hex(7):"

				return "hex(7):{}".format(
					RegFileValueFormatter.utf16(value, multi_sz = True)
				)

			# REG_DWORD
			if type_name == "REG_DWORD":
				value = int(value)

				return "dword:{:08x}".format(value)

			# REG_QWORD
			if type_name == "REG_QWORD":
				data = int(value).to_bytes(8, byteorder = "little", signed = False)

				return "hex(b):{}".format(
					RegFileValueFormatter.hex(data)
				)

			# REG_BINARY
			if type_name == "REG_BINARY":
				data = bytes(value)

				# IMPORTANT:
				# b"" means an existing empty REG_BINARY value.
				if not data:
					return "hex(0):"

				return "hex:{}".format(
					RegFileValueFormatter.hex(data)
				)

			# REG_NONE
			if type_name == "REG_NONE":
				if isinstance(value, (bytes, bytearray)):
					data = bytes(value)
				else:
					data = b""

				if not data:
					return "hex(0):"

				return "hex:{}".format(RegFileValueFormatter.hex(data))

			# Unsupported
			return None
		except (OSError, KeyError, TypeError, ValueError, OverflowError):
			raise exceptions_module.variable.INCORRECT

#-=-=-=-#

def clean(key_path: str) -> None:
	"""
	Removes all variables from the `key_path`. Includes `(Default)`.

	Parameters
	----------
		key_path: Existing registry path including the hive.
	"""
	# Deferred import prevents circular loading between core.py and utils.py
	from .core import RegEntry

	subkey = RegEntry(key_path)

	if not subkey.exists():
		raise OSError(exceptions.path.NOTEXISTS)

	for variable in subkey.variables():
		subkey.delete_variable(variable)

# cant be in path.py sadly
def canonicalize(hive: str, parts: str) -> list:
	"""
	Resolve registry key names to the casing actually stored
	in the Windows Registry.

	Notes
	-----
		Existing components are canonicalized.

		Once a component does not exist, that component
		and all following components are left unchanged.
	"""
	if not parts:
		return []

	result = []
	current = hive
	opened = False

	try:
		for index, part in enumerate(parts):
			actual_name = None

			try:
				subkey_count = winreg.QueryInfoKey(current)[0]

				for i in range(subkey_count):
					name = winreg.EnumKey(current, i)

					if name.casefold() == part.casefold():
						actual_name = name
						break
			except OSError:
				actual_name = None

			if actual_name is None:
				# This component doesn't exist.
				# Keep it and everything after it exactly as supplied.
				result.extend(parts[index:])
				break

			result.append(actual_name)

			next_key = winreg.OpenKey(
				current,
				actual_name
			)

			if opened:
				winreg.CloseKey(current)

			current = next_key
			opened = True
	finally:
		if opened:
			try:
				winreg.CloseKey(current)
			except TypeError:
				# handle mocked objects in tests that aren't real PyHKEY objects
				pass


	return result

#-=-=-=-#
# Save

def traverse_registry(
	hkey,
	key_path,
	hive_constant,
	hive_name,
	list_subkeys_fn,
	types_dict,
	exceptions_module,
	output_array,
	beautify_depth: int = 0,
	editable: bool = False,
	current_depth: int = 0,
):
	"""
	Recursively walks registry keys and appends .reg lines.

	The current key is processed first, including all of its values.
	Then all child keys are recursively processed.
	"""
	try:
		with winreg.OpenKey(hkey, key_path, access = winreg.KEY_READ) as entry:
			# Enumerate ALL values belonging to THIS key
			values = []
			counter = 0

			while True:
				try:
					value_name, value, value_type = winreg.EnumValue(entry, counter)
					values.append((value_name, value, value_type))

					counter += 1
				except OSError:
					break

			# Determine whether this key should be exported
			should_write = editable or values # bool

			if should_write:
				output_array.append("[{0}]".format(os.path.join(hive_name, key_path)))

				# Write every value, including empty values
				for value_name, value, value_type in values:
					formatted_value = RegFileValueFormatter.main(
						name = value_name,

						value = value,
						value_type = value_type,

						types_dict = types_dict,

						exceptions_module = exceptions_module,

						optimize = editable
					)

					# Unsupported types are skipped
					if formatted_value is None or not isinstance(formatted_value, str):
						continue

					#if editable:
					formatted_value = RegFileValueFormatter.hex_wrap(formatted_value)

					final_value = value_name.replace("\\", r"\\")
					final_value = final_value.replace('"', r'\"')

					output_array.append(f'"{final_value}"={formatted_value}')

				# End of key
				output_array.append("")

				# Beautification
				if beautify_depth > 0 and current_depth == beautify_depth:
					output_array.append("")
					output_array.append("")

			# Enumerate child keys
			try:
				subkeys = list(list_subkeys_fn(entry))
			except (OSError, StopIteration):
				subkeys = []

			# Recurse into every child
			for subkey_name in subkeys:
				subkey_path = os.path.join(
					key_path,
					subkey_name
				)

				try:
					traverse_registry(
						hkey = hive_constant,
						key_path = subkey_path,
						hive_constant = hive_constant,
						hive_name = hive_name,
						list_subkeys_fn = list_subkeys_fn,
						types_dict = types_dict,
						exceptions_module = exceptions_module,
						output_array = output_array,
						beautify_depth = beautify_depth,
						editable = editable,
						current_depth = current_depth + 1,
					)

				except OSError:
					continue
	except OSError:
		return

#-=-=-=-#

clear = clean
resolve = normpath = canonicalize
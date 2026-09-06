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
	Recursively walks registry keys and appends `.reg` lines.
	"""
	with winreg.OpenKey(hkey, key_path, access = winreg.KEY_READ) as entry:
		# Enumerate subkeys

		try:
			subkeys = list(
				list_subkeys_fn(entry)
			)
		except (OSError, StopIteration):
			subkeys = []

		# Process each subkey
		for subkey_name in subkeys:
			subkey_path = os.path.join(
				key_path,
				subkey_name
			)

			try:

				with winreg.OpenKey(hive_constant, subkey_path, access = winreg.KEY_READ) as sub_entry:
					# Enumerate ALL values
					values = []
					counter = 0

					while True:
						try:
							value = winreg.EnumValue(sub_entry, counter)
							values.append(list(value))
							counter += 1
						except OSError:
							break

					# Enumerate subkeys
					try:
						child_subkeys = list(list_subkeys_fn(sub_entry))
					except (OSError, StopIteration):
						child_subkeys = []

					# Determine whether key contains values
					has_values = bool(values)

					# Determine whether key should be written
					if editable:
						# Editable mode:
						# WRITE EVERY KEY.
						should_write = True
					else:
						# WRITE ONLY KEYS WITH VALUES.
						should_write = has_values

					# Write key header
					if should_write:
						output_array.append("[{0}]".format(os.path.join(hive_name, subkey_path)))

						for keys in values:
							var_type = ""

							try:
								# Registry type is not supported
								if keys[2] not in types_dict:
									continue

								type_name = types_dict[keys[2]]

								# REG_DWORD
								if type_name == "REG_DWORD":
									var_type = "dword:"

									keys[1] = '"{0}"'.format(
										keys[1]
									)

								# REG_QWORD
								elif type_name == "REG_QWORD":
									var_type = "qword:"

								# REG_MULTI_SZ
								elif type_name == "REG_MULTI_SZ":
									var_type = "hex(7):"

									encoded_words = [word.encode("UTF-8").hex(sep = ",") for word in keys[1]]
									keys[1] = ",00,".join(encoded_words)
							except (OSError, KeyError):
								raise (exceptions_module.variable.INCORRECT)

							# Append value
							output_array.append('"{0}"={1}{2}'.format(keys[0], var_type, keys[1]))

						# End of key
						output_array.append("")

						# Beautification
						if (beautify_depth > 0 and current_depth == beautify_depth):
							for x in range(2):
								output_array.append("")

					# ALWAYS recurse
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

#-=-=-=-#

conv = StringConverter
clear = clean
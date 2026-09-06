"""os.path-alike wrapper."""

from .core import RegEntry

from typing import Optional

#-=-=-=-#

def listdir(path: str) -> list:
	"""
	Parameters
	----------
		path (str):
			Existing registry path including the hive.

	Returns
	-------
		list (str):
			The names of the subkeys in the subkey.
	"""
	return dir(RegEntry(path))

class path:
	@staticmethod
	def abspath(path: str, short: bool = False) -> str:
		"""
		Retrieves registry full key.

		Parameters
		----------
			path (str):
				Registry path including the hive.

			short (bool):
				Replaces full hive name with its shortcut.

		Returns
		-------
			str:
				Full path of registry entry.
		"""
		retval = RegEntry(path)

		if short:
			return retval.path_short
	
		return retval.path

	@staticmethod
	def basename(path) -> str:
		"""
		Returns registry key's name.
		
		Parameters
		----------
			path (str):
				Registry path including the hive.
		"""
		return RegEntry(path).basename

	@staticmethod
	def dirname(path: str, short: Optional[bool] = False) -> str:
		"""
		Retrieves name of current subkey's parent path.
		
		Parameters
		----------
			path (str):
				Registry path including the hive.

		Returns
		-------
			str:
				Dirname of registry path.
		"""
		retval = RegEntry(path)

		if short:
			retval = retval.dirname_short
		else:
			retval = retval.dirname

		return retval

	@staticmethod
	def exists(path: str) -> bool:
		"""
		Checks for registry subkey existence.
		
		Parameters
		----------
			path (str):
				Registry path including the hive.

		Returns
		-------
			bool:
				True if subkey exists, False otherwise.
		"""
		return RegEntry(path).subkey_exists()

	@staticmethod
	def is_hive(path: str) -> bool:
		"""
		Determines whether path is a hive.

		Parameters
		----------
			path (str):
				Existing registry path including the hive.

		Returns
		-------
			bool:
				True if currend subkey path is a hive.
		"""
		return RegEntry(path).is_hive()
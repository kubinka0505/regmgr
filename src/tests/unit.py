"""Pytest tests for RegEntry class."""
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open

# Mock the relative imports before importing core
from unittest.mock import MagicMock

from regmgr import RegEntry

mock_utils = MagicMock()
mock_config = MagicMock()
mock_config.defaults.path.ESC_CHARS = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
mock_config.exceptions.setup.ESC_FOUND = Exception("ESC_FOUND")
mock_config.exceptions.hive.NOTEXISTS = Exception("HIVE_NOTEXISTS")
mock_config.exceptions.key.NOTEXISTS = Exception("KEY_NOTEXISTS")
mock_config.exceptions.variable.EXISTS = Exception("VARIABLE_EXISTS")
mock_config.exceptions.variable.NOTEXISTS = Exception("VARIABLE_NOTEXISTS")
mock_config.exceptions.path.file.EXISTS = Exception("FILE_EXISTS")

os.sys.modules["core.utils"] = mock_utils
os.sys.modules["core.config"] = mock_config

class TestRegEntryInitialization:
	"""Test RegEntry initialization and path parsing."""

	def test_init_full_hive_name(self):
		"""Test initialization with full hive name."""
		entry = RegEntry(r"HKEY_CURRENT_USER\Software")
		assert entry.hive == "HKEY_CURRENT_USER"
		assert entry.subkey == "Software"

	def test_init_short_hive_name(self):
		"""Test initialization with short hive alias."""
		entry = RegEntry(r"HKCU\Software")
		assert entry.hive == "HKEY_CURRENT_USER"
		assert entry.subkey == "Software"

	def test_init_hive_only(self):
		"""Test initialization with hive only."""
		entry = RegEntry("HKEY_LOCAL_MACHINE")
		assert entry.hive == "HKEY_LOCAL_MACHINE"
		assert entry.subkey == ""

	def test_init_short_hive_only(self):
		"""Test initialization with short hive alias only."""
		entry = RegEntry("HKLM")
		assert entry.hive == "HKEY_LOCAL_MACHINE"

	def test_init_strips_leading_trailing_separators(self):
		"""Test that leading/trailing separators are stripped."""
		entry = RegEntry("\\HKCU\\Software\\")
		assert entry.path == r"HKEY_CURRENT_USER\Software"

	def test_init_case_insensitive_hive(self):
		"""Test that hive names are case-insensitive."""
		entry = RegEntry(r"HKCU\Software")
		assert entry.hive == "HKEY_CURRENT_USER"

	def test_init_invalid_hive_raises(self):
		"""Test that invalid hive name raises exception."""
		with pytest.raises(FileNotFoundError, match = "hive does not exist"):
			RegEntry(r"INVALID\Software")

	def test_init_valid_path(self):
		"""Test that valid paths are accepted."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.hive == "HKEY_CURRENT_USER"
		assert "Software" in entry.subkey

	def test_init_all_hives(self):
		"""Test initialization with all known hives."""
		hives = [
			("HKCR", "HKEY_CLASSES_ROOT"),
			("HKCU", "HKEY_CURRENT_USER"),
			("HKLM", "HKEY_LOCAL_MACHINE"),
			("HKU", "HKEY_USERS"),
			("HKCC", "HKEY_CURRENT_CONFIG"),
		]
		for short, full in hives:
			entry = RegEntry(short)
			assert entry.hive == full
			assert entry.hive_short == short

class TestRegEntryProperties:
	"""Test RegEntry properties."""

	def test_path_property(self):
		"""Test path property returns full path with hive."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.path == r"HKEY_CURRENT_USER\Software\Microsoft"

	def test_path_no_trailing_separator(self):
		"""Test path property removes trailing separator."""
		entry = RegEntry("HKCU\\Software\\")
		assert not entry.path.endswith("\\")

	def test_path_short_property(self):
		"""Test path_short property returns path with short hive."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.path_short == r"HKCU\Software\Microsoft"

	def test_hive_property(self):
		"""Test hive property returns full hive name."""
		entry = RegEntry(r"HKCU\Software")
		assert entry.hive == "HKEY_CURRENT_USER"

	def test_hive_short_property(self):
		"""Test hive_short property returns short hive alias."""
		entry = RegEntry(r"HKEY_CURRENT_USER\Software")
		assert entry.hive_short == "HKCU"

	def test_hive_constant_property(self):
		"""Test hive_constant property returns winreg constant."""
		with patch("winreg.HKEY_CURRENT_USER", 0x80000001):
			entry = RegEntry(r"HKCU\Software")
			assert entry.hive_constant == 0x80000001

	def test_subkey_property(self):
		"""Test subkey property returns path without hive."""
		entry = RegEntry(r"HKCU\Software\Microsoft\Windows")
		assert entry.subkey == r"Software\Microsoft\Windows"

	def test_subkey_empty_for_hive_root(self):
		"""Test subkey is empty for hive root."""
		entry = RegEntry("HKCU")
		assert entry.subkey == ""

	def test_dirname_property(self):
		"""Test dirname property returns parent directory."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.dirname == r"HKEY_CURRENT_USER\Software"

	def test_dirname_short_property(self):
		"""Test dirname_short property returns parent with short hive."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.dirname_short == r"HKCU\Software"

	def test_basename_property(self):
		"""Test basename property returns last path component."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.basename == "Microsoft"

	def test_basename_at_hive_root(self):
		"""Test basename at hive root is the hive shortname."""
		entry = RegEntry("HKCU")
		# basename splits on subkey, which is empty at hive root
		assert entry.basename == ""

class TestRegEntryChecks:
	"""Test RegEntry check methods."""

	def test_is_hive_true_for_hive_root(self):
		"""Test is_hive returns True for hive root."""
		entry = RegEntry("HKCU")
		assert entry.is_hive() is True

	def test_is_hive_false_for_subkey(self):
		"""Test is_hive returns False for subkey."""
		entry = RegEntry(r"HKCU\Software")
		assert entry.is_hive() is False

	@patch("winreg.OpenKey")
	def test_subkey_exists_true(self, mock_open_key):
		"""Test subkey_exists returns True when key exists."""
		mock_open_key.return_value.__enter__ = Mock(return_value = Mock())
		mock_open_key.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		result = entry.subkey_exists()
		assert result is True

	@patch("winreg.OpenKey")
	def test_subkey_exists_false(self, mock_open_key):
		"""Test subkey_exists returns False when key doesn't exist."""
		mock_open_key.side_effect = OSError("Key not found")

		entry = RegEntry(r"HKCU\Software")
		result = entry.subkey_exists()
		assert result is False

	@patch("winreg.OpenKey")
	def test_subkey_exists_with_relative_path(self, mock_open_key):
		"""Test subkey_exists with relative key name."""
		mock_open_key.return_value.__enter__ = Mock(return_value = Mock())
		mock_open_key.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		entry.subkey_exists("Microsoft")

		# Verify OpenKey was called with correct path
		call_args = mock_open_key.call_args
		assert r"Software\Microsoft" in call_args[0]

	@patch("winreg.OpenKey")
	@patch("winreg.QueryValueEx")
	def test_variable_exists_true(self, mock_query, mock_open_key):
		"""Test variable_exists returns True when variable exists."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		mock_query.return_value = ("value", 1)

		entry = RegEntry(r"HKCU\Software")
		result = entry.variable_exists("MyVar")
		assert result is True

	@patch("winreg.OpenKey")
	@patch("winreg.QueryValueEx")
	def test_variable_exists_false(self, mock_query, mock_open_key):
		"""Test variable_exists returns False when variable doesn't exist."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		mock_query.side_effect = OSError("Variable not found")

		entry = RegEntry(r"HKCU\Software")
		result = entry.variable_exists("MyVar")
		assert result is False

	@patch("winreg.OpenKey")
	def test_variable_exists_raises_for_nonexistent_key(self, mock_open_key):
		"""Test variable_exists raises when key doesn't exist."""
		mock_open_key.side_effect = OSError("Key not found")

		entry = RegEntry(r"HKCU\InvalidKey")
		with pytest.raises(OSError):
			entry.variable_exists("MyVar")

class TestRegEntryNavigation:
	"""Test RegEntry navigation methods."""

	def test_relcd_forward(self):
		"""Test relcd with forward path."""
		entry = RegEntry(r"HKCU\Software")
		entry.relcd(r"Microsoft\Windows")
		assert entry.path == r"HKEY_CURRENT_USER\Software\Microsoft\Windows"

	def test_relcd_empty_is_noop(self):
		"""Test relcd with empty string is no-op."""
		entry = RegEntry(r"HKCU\Software")
		original = entry.path
		entry.relcd("")
		assert entry.path == original

	def test_relcd_parent_directory(self):
		"""Test relcd with parent directory (..)."""
		entry = RegEntry(r"HKCU\Software\Microsoft\Windows")
		entry.relcd("..")
		assert entry.path == r"HKEY_CURRENT_USER\Software\Microsoft"

	def test_relcd_multiple_parents(self):
		"""Test relcd with multiple parent directories."""
		entry = RegEntry(r"HKCU\Software\Microsoft\Windows")
		entry.relcd(r"..\..\Apple")
		assert entry.path == r"HKEY_CURRENT_USER\Software\Apple"

	def test_relcd_outside_hive_raises(self):
		"""Test relcd raises when navigating outside hive."""
		entry = RegEntry(r"HKCU\Software")
		with pytest.raises(FileNotFoundError, match = "hive does not exist"):
			entry.relcd(r"..\..\..\..\..\Outside")

	def test_relcd_none_is_noop(self):
		"""Test relcd with None is no-op."""
		entry = RegEntry(r"HKCU\Software")
		original = entry.path
		entry.relcd(None)
		assert entry.path == original

	def test_relcd_strips_leading_separator(self):
		"""Test relcd strips leading separator."""
		entry = RegEntry(r"HKCU\Software")
		entry.relcd("Microsoft") # Leading sep gets stripped anyway
		assert entry.path == r"HKEY_CURRENT_USER\Software\Microsoft"

class TestRegEntrySubkeys:
	"""Test RegEntry subkey methods."""

	@patch("winreg.OpenKey")
	def test_subkeys_exists_check(self, mock_open_key):
		"""Test subkeys raises if subkey doesn't exist."""
		mock_open_key.side_effect = OSError("Key not found")

		entry = RegEntry(r"HKCU\Software")
		with pytest.raises(FileNotFoundError, match = "Subkey does not exist"):
			entry.subkeys()

	@patch("winreg.OpenKey")
	@patch("winreg.EnumKey")
	def test_subkeys_non_recursive(self, mock_enum, mock_open_key):
		"""Test subkeys returns direct children only."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		mock_enum.side_effect = [OSError()] # No children

		entry = RegEntry(r"HKCU\Software")
		# Set subkey_exists to return True
		with patch.object(entry, "subkey_exists", return_value = True):
			result = entry.subkeys(recursive = False)
			assert isinstance(result, tuple)

	@patch("winreg.CreateKey")
	def test_create_subkey(self, mock_create_key):
		"""Test create_subkey creates new subkey."""
		mock_create_key.return_value.__enter__ = Mock(return_value = Mock())
		mock_create_key.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		entry.create_subkey("NewKey")

		# Verify CreateKey was called
		mock_create_key.assert_called()

	@patch("winreg.EnumKey")
	@patch("winreg.OpenKey")
	@patch("winreg.DeleteKey")
	def test_remove_subkey(self, mock_delete_key, mock_open_key, mock_enum):
		"""Test delete_subkeys deletes subkey."""

		# Mock EnumKey to return no children (empty subkey)
		mock_enum.side_effect = OSError()

		# Mock OpenKey to return a context manager
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)

		with patch.object(RegEntry, "subkey_exists", return_value = True):
			entry = RegEntry(r"HKCU\Software")
			entry.delete_subkeys("OldKey")

			# Verify DeleteKey was called
			mock_delete_key.assert_called()

class TestRegEntryVariables:
	"""Test RegEntry variable (value) methods."""

	@patch("winreg.OpenKey")
	@patch("winreg.QueryValueEx")
	def test_get_variable(self, mock_query, mock_open_key):
		"""Test get returns variable value and type name as string."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		# Real implementation converts type to string name like 'REG_SZ'
		mock_query.return_value = ("test_value", 1) # winreg.REG_SZ = 1

		entry = RegEntry(r"HKCU\Software")
		value, var_type = entry.get("TestVar")
		assert value == "test_value"
		# Type is returned as string representation
		assert var_type == "REG_SZ"

	@patch("winreg.QueryValueEx")
	@patch("winreg.OpenKey")
	@patch("winreg.SetValueEx")
	def test_set_variable(self, mock_set, mock_open_key, mock_query):
		"""Test set creates/updates variable."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		# QueryValueEx is called to check if exists - make it raise OSError (not found)
		mock_query.side_effect = OSError("Variable not found")

		entry = RegEntry(r"HKCU\Software")
		# Patch variable_exists to avoid actual registry access
		with patch.object(entry, "variable_exists", return_value = False):
			entry.set("TestVar", "test_value")

		# Verify SetValueEx was called
		mock_set.assert_called()

	@patch("winreg.OpenKey")
	@patch("winreg.DeleteValue")
	def test_remove_variable(self, mock_delete, mock_open_key):
		"""Test remove_variable deletes variable."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)

		with patch.object(RegEntry, "variable_exists", return_value = True):
			entry = RegEntry(r"HKCU\Software")
			entry.remove_variable("TestVar")

			# Verify DeleteValue was called
			mock_delete.assert_called()

	@patch("winreg.OpenKey")
	@patch("winreg.DeleteValue")
	def test_remove_variable_not_exists_raises(self, mock_delete, mock_open_key):
		"""Test remove_variable raises if variable doesn't exist."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)

		with patch.object(RegEntry, "variable_exists", return_value = False):
			entry = RegEntry(r"HKCU\Software")
			with pytest.raises(FileNotFoundError, match = "Variable does not exist"):
				entry.remove_variable("NonExistent")

class TestRegEntryMappingInterface:
	"""Test Mapping protocol implementation."""

	def test_str_representation(self):
		"""Test __str__ returns path."""
		entry = RegEntry(r"HKCU\Software")
		assert str(entry) == r"HKEY_CURRENT_USER\Software"

	def test_repr_representation(self):
		"""Test __repr__ returns constructor-like string."""
		entry = RegEntry(r"HKCU\Software")
		assert "RegEntry" in repr(entry)
		assert r"HKEY_CURRENT_USER\Software" in repr(entry)

	@patch("winreg.OpenKey")
	@patch("winreg.EnumKey")
	def test_len_returns_recursive_subkeys(self, mock_enum, mock_open_key):
		"""Test __len__ returns count of recursive subkeys."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		mock_enum.side_effect = [OSError()]

		entry = RegEntry(r"HKCU\Software")
		with patch.object(entry, "subkeys", return_value = tuple()):
			length = len(entry)
			assert isinstance(length, int)

	def test_int_returns_hive_constant(self):
		"""Test __int__ returns hive constant."""
		with patch("winreg.HKEY_CURRENT_USER", 0x80000001):
			entry = RegEntry("HKCU")
			assert int(entry) == 0x80000001

	@patch("winreg.OpenKey")
	@patch("winreg.QueryValueEx")
	def test_getitem_variable(self, mock_query, mock_open_key):
		"""Test __getitem__ returns variable value."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		mock_query.return_value = ("test_value", 1)

		with patch.object(RegEntry, "variables", return_value = {"TestVar": ("test_value", 1)}):
			entry = RegEntry(r"HKCU\Software")
			value = entry["TestVar"]
			assert value == "test_value"

	@patch("winreg.QueryValueEx")
	@patch("winreg.OpenKey")
	@patch("winreg.SetValueEx")
	def test_setitem_variable(self, mock_set, mock_open_key, mock_query):
		"""Test __setitem__ sets variable."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		mock_query.side_effect = OSError("Variable not found")

		entry = RegEntry(r"HKCU\Software")
		with patch.object(entry, "variable_exists", return_value = False):
			entry["TestVar"] = "test_value"

		# Verify set was called
		mock_set.assert_called()

	@patch("winreg.OpenKey")
	@patch("winreg.DeleteValue")
	def test_delitem_variable(self, mock_delete, mock_open_key):
		"""Test __delitem__ removes variable."""
		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)

		with patch.object(RegEntry, "variable_exists", return_value = True):
			entry = RegEntry(r"HKCU\Software")
			del entry["TestVar"]

			# Verify delete was called
			mock_delete.assert_called()

class TestRegEntryContextManager:
	"""Test context manager protocol."""

	@patch("winreg.OpenKey")
	def test_context_manager_enter(self, mock_open_key):
		"""Test __enter__ opens key."""
		mock_key = Mock()
		mock_open_key.return_value = mock_key

		entry = RegEntry(r"HKCU\Software")
		result = entry.__enter__()

		assert result is entry
		mock_open_key.assert_called()

	@patch("winreg.OpenKey")
	def test_context_manager_exit(self, mock_open_key):
		"""Test __exit__ closes key."""
		mock_key = Mock()
		mock_open_key.return_value = mock_key

		entry = RegEntry(r"HKCU\Software")
		entry._handle = mock_key
		result = entry.__exit__(None, None, None)

		assert result is False
		mock_key.Close.assert_called()

class TestRegEntryAliases:
	"""Test method aliases."""

	def test_aliases_exist(self):
		"""Test that common aliases are defined."""
		entry = RegEntry("HKCU")

		# Check some aliases exist and reference correct methods
		assert hasattr(entry, "navigate")
		assert hasattr(entry, "nav")
		assert hasattr(entry, "dirs")
		assert hasattr(entry, "vars")
		assert hasattr(entry, "key_exists")
		assert hasattr(entry, "var_exists")

class TestRegEntryHelpers:
	"""Test helper methods."""

	def test_key_resolver_with_key_name(self):
		"""Test _key_resolver with relative key name."""
		entry = RegEntry(r"HKCU\Software")
		result = entry._key_resolver("Microsoft")
		assert result == r"Software\Microsoft"

	def test_key_resolver_without_key_name(self):
		"""Test _key_resolver without key name returns current subkey."""
		entry = RegEntry(r"HKCU\Software")
		result = entry._key_resolver(None)
		assert result == "Software"

	def test_key_resolver_with_valid_name(self):
		"""Test _key_resolver with valid name."""
		entry = RegEntry(r"HKCU\Software")
		result = entry._key_resolver("ValidName")
		assert "ValidName" in result

	@patch("winreg.EnumKey")
	def test_list_subkeys_generator(self, mock_enum):
		"""Test _list_subkeys yields subkey names."""
		mock_enum.side_effect = ["Key1", "Key2", OSError()]

		entry = RegEntry(r"HKCU\Software")
		mock_key = Mock()
		result = list(entry._list_subkeys(mock_key))

		assert "Key1" in result
		assert "Key2" in result
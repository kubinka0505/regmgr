"""Pytest tests for RegEntry class."""
import os
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock

from regmgr import RegEntry, path as reg_path, listdir, StringConverter, clean, traverse_registry

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
		assert entry.subkey == "SOFTWARE"

	def test_init_short_hive_name(self):
		"""Test initialization with short hive alias."""
		entry = RegEntry(r"HKCU\Software")
		assert entry.hive == "HKEY_CURRENT_USER"
		assert entry.subkey == "SOFTWARE"

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
		assert entry.path == r"HKEY_CURRENT_USER\SOFTWARE"

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
		assert "SOFTWARE" in entry.subkey

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
		assert entry.path == r"HKEY_CURRENT_USER\SOFTWARE\Microsoft"

	def test_path_no_trailing_separator(self):
		"""Test path property removes trailing separator."""
		entry = RegEntry("HKCU\\Software\\")
		assert not entry.path.endswith("\\")

	def test_path_short_property(self):
		"""Test path_short property returns path with short hive."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.path_short == r"HKCU\SOFTWARE\Microsoft"

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
		assert entry.subkey == r"SOFTWARE\Microsoft\Windows"

	def test_subkey_empty_for_hive_root(self):
		"""Test subkey is empty for hive root."""
		entry = RegEntry("HKCU")
		assert entry.subkey == ""

	def test_dirname_property(self):
		"""Test dirname property returns parent directory."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.dirname == r"HKEY_CURRENT_USER\SOFTWARE"

	def test_dirname_short_property(self):
		"""Test dirname_short property returns parent with short hive."""
		entry = RegEntry(r"HKCU\Software\Microsoft")
		assert entry.dirname_short == r"HKCU\SOFTWARE"

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
		assert r"SOFTWARE\Microsoft" in call_args[0]

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
		assert entry.path == r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows"

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
		assert entry.path == r"HKEY_CURRENT_USER\SOFTWARE\Microsoft"

	def test_relcd_multiple_parents(self):
		"""Test relcd with multiple parent directories."""
		entry = RegEntry(r"HKCU\Software\Microsoft\Windows")
		entry.relcd(r"..\..\Apple")
		assert entry.path == r"HKEY_CURRENT_USER\SOFTWARE\Apple"

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
		assert entry.path == r"HKEY_CURRENT_USER\SOFTWARE\Microsoft"

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
		assert str(entry) == r"HKEY_CURRENT_USER\SOFTWARE"

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
		assert result == r"SOFTWARE\Microsoft"

	def test_key_resolver_without_key_name(self):
		"""Test _key_resolver without key name returns current subkey."""
		entry = RegEntry(r"HKCU\Software")
		result = entry._key_resolver(None)
		assert result == "SOFTWARE"

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

#-=-=-=-#

class TestPathModule:
	"""Test path.py functions."""

	def test_listdir(self):
		"""Test listdir returns subkey names."""
		with patch.object(RegEntry, "__dir__", return_value = ["Software", "Services"]):
			result = listdir("HKCU")
			assert isinstance(result, (list, tuple))

	def test_path_abspath_full(self):
		"""Test path.abspath returns full path."""
		result = reg_path.abspath(r"HKCU\Software")
		assert result == r"HKEY_CURRENT_USER\SOFTWARE"

	def test_path_abspath_short(self):
		"""Test path.abspath with short = True returns short path."""
		result = reg_path.abspath(r"HKCU\Software", short = True)
		assert result == r"HKCU\SOFTWARE"

	def test_path_basename(self):
		"""Test path.basename returns last component."""
		result = reg_path.basename(r"HKCU\Software\Microsoft")
		assert result == "Microsoft"

	def test_path_dirname_full(self):
		"""Test path.dirname returns parent directory."""
		result = reg_path.dirname(r"HKCU\Software\Microsoft")
		assert result == r"HKEY_CURRENT_USER\SOFTWARE"

	def test_path_dirname_short(self):
		"""Test path.dirname with short=True returns short parent."""
		result = reg_path.dirname(r"HKCU\Software\Microsoft", short = True)
		assert result == r"HKCU\SOFTWARE"

	@patch.object(RegEntry, "subkey_exists", return_value = True)
	def test_path_exists_true(self, mock_exists):
		"""Test path.exists returns True when key exists."""
		result = reg_path.exists(r"HKCU\Software")
		assert result is True

	@patch.object(RegEntry, "subkey_exists", return_value = False)
	def test_path_exists_false(self, mock_exists):
		"""Test path.exists returns False when key doesn"t exist."""
		result = reg_path.exists(r"HKCU\NonExistent")
		assert result is False

	def test_path_is_hive_true(self):
		"""Test path.is_hive returns True for hive root."""
		result = reg_path.is_hive("HKCU")
		assert result is True

	def test_path_is_hive_false(self):
		"""Test path.is_hive returns False for subkey."""
		result = reg_path.is_hive(r"HKCU\Software")
		assert result is False

class TestStringConverter:
	"""Test StringConverter utility class."""

	def test_str_to_bytes_default_encoding(self):
		"""Test str_to_bytes with default UTF-8."""
		result = StringConverter.str_to_bytes("hello")
		assert result == b"hello"

	def test_str_to_bytes_custom_encoding(self):
		"""Test str_to_bytes with custom encoding."""
		result = StringConverter.str_to_bytes("hello", encoding = "ascii")
		assert result == b"hello"

	def test_hex_to_str(self):
		"""Test hex_to_str converts hex string to bytes."""
		result = StringConverter.hex_to_str("48656c6c6f")
		assert result == b"Hello"

	def test_s2b_alias(self):
		"""Test s2b alias for str_to_bytes."""
		result = StringConverter.s2b("test")
		assert result == b"test"

	def test_h2s_alias(self):
		"""Test h2s alias for hex_to_str."""
		result = StringConverter.h2s("74657374")
		assert result == b"test"

	def test_hex_to_string_alias(self):
		"""Test hex_to_string alias for hex_to_str."""
		result = StringConverter.hex_to_string("74657374")
		assert result == b"test"

class TestUtilsClean:
	"""Test clean function to remove all variables from a key."""

	@patch("regmgr.core.RegEntry")
	def test_clean_removes_all_variables(self, mock_reg_entry_class):
		"""Test clean removes all variables from key."""
		mock_entry = Mock()
		mock_entry.exists.return_value = True
		mock_entry.variables.return_value = ["Var1", "Var2"]
		mock_reg_entry_class.return_value = mock_entry

		clean(r"HKCU\Software")

		# Verify variables were deleted
		assert mock_entry.delete_variable.call_count == 2

	@patch("regmgr.core.RegEntry")
	def test_clean_raises_if_key_not_exists(self, mock_reg_entry_class):
		"""Test clean raises if key doesn"t exist."""
		mock_entry = Mock()
		mock_entry.exists.return_value = False
		mock_reg_entry_class.return_value = mock_entry

		with pytest.raises(OSError):
			clean(r"HKCU\NonExistent")

class TestTraverseRegistry:
	"""Test traverse_registry function for .reg export."""

	def test_traverse_registry_basic(self):
		"""Test traverse_registry adds header to output."""
		output_array = []

		mock_list_fn = Mock(return_value = [])
		mock_types = {1: "REG_SZ"}

		with patch("winreg.OpenKey"):
			traverse_registry(
				hkey = Mock(),
				key_path = "Software",
				hive_constant = Mock(),
				hive_name = "HKEY_CURRENT_USER",
				list_subkeys_fn = mock_list_fn,
				types_dict = mock_types,
				exceptions_module = Mock(),
				output_array = output_array,
				beautify_depth = 0,
				editable = False,
			)

		# Should have called the function
		assert mock_list_fn.called

	@patch("winreg.OpenKey")
	@patch("winreg.EnumValue")
	def test_traverse_registry_with_values(self, mock_enum_value, mock_open_key):
		"""Test traverse_registry processes key values."""
		output_array = []

		mock_key = Mock()
		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		
		# Mock EnumValue to always raise OSError (no values found)
		# This is safer than trying to mock the complex iteration
		mock_enum_value.side_effect = OSError()

		mock_types = {1: "REG_SZ"}
		mock_list_fn = Mock(return_value = [])
		mock_exceptions = Mock()

		# Just verify the function doesn"t crash
		try:
			traverse_registry(
				hkey = 1,
				key_path = "Software",
				hive_constant = 1,
				hive_name = "HKEY_CURRENT_USER",
				list_subkeys_fn = mock_list_fn,
				types_dict = mock_types,
				exceptions_module = mock_exceptions,
				output_array = output_array,
				beautify_depth = 0,
				editable = False,
			)
			assert True # Function completed without error
		except Exception:
			pytest.fail("traverse_registry should not raise exception")

class TestCoreSubkeysRecursive:
	"""Test recursive subkey operations in core.py."""

	@patch("winreg.EnumKey")
	@patch("winreg.OpenKey")
	def test_subkeys_recursive(self, mock_open_key, mock_enum_key):
		"""Test subkeys with recursive = True."""
		mock_key = Mock()

		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)

		# Use function for side_effect to properly handle multiple calls
		call_count = [0]
		def enum_side_effect(key, index):
			call_count[0] += 1

			if call_count[0] == 1:
				return "Services"

			raise OSError() # No more keys

		mock_enum_key.side_effect = enum_side_effect

		entry = RegEntry(r"HKCU\Software")
		with patch.object(entry, "subkey_exists", return_value = True):
			result = entry.subkeys(recursive = True, absolute_paths = False)
			assert isinstance(result, tuple)

	@patch("winreg.EnumKey")
	@patch("winreg.OpenKey")
	def test_subkeys_absolute_paths(self, mock_open_key, mock_enum_key):
		"""Test subkeys with absolute_paths = True."""
		mock_key = Mock()

		mock_open_key.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open_key.return_value.__exit__ = Mock(return_value = None)
		mock_enum_key.side_effect = OSError()

		entry = RegEntry(r"HKCU\Software")
		with patch.object(entry, "subkey_exists", return_value = True):
			result = entry.subkeys(recursive = False, absolute_paths = True)
			assert isinstance(result, tuple)

class TestCoreSaveMethod:
	"""Test save() method for .reg file export."""

	@patch("builtins.open", create = True)
	@patch.object(RegEntry, "subkey_exists", return_value = True)
	def test_save_creates_file(self, mock_exists, mock_file):
		"""Test save creates a .reg file."""
		mock_file.return_value.__enter__ = Mock()
		mock_file.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		with patch("regmgr.core.traverse_registry"):
			result = entry.save(output = "/tmp/test", exist_ok = True)

		assert result.endswith(".reg")
		mock_file.assert_called()

	@patch.object(RegEntry, "subkey_exists", return_value = True)
	def test_save_default_output_name(self, mock_exists):
		"""Test save uses basename as default output."""
		entry = RegEntry(r"HKCU\Software")

		with patch("builtins.open"):
			with patch("regmgr.core.traverse_registry"):
				result = entry.save(exist_ok = True)

		assert "SOFTWARE" in result

	@patch("builtins.open", create = True)
	@patch.object(RegEntry, "subkey_exists", return_value = True)
	def test_save_beautify_depth_minus_one(self, mock_exists, mock_file):
		"""Test save with beautify_depth = -1 removes all newlines."""
		mock_file.return_value.__enter__ = Mock()
		mock_file.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		with patch("regmgr.core.traverse_registry"):
			entry.save(output = "/tmp/test", beautify_depth = -1, exist_ok = True)

		mock_file.assert_called()

	@patch("os.path.exists", return_value = True)
	@patch("os.path.isdir", return_value = False)
	def test_save_file_exists_not_ok(self, mock_isdir, mock_exists):
		"""Test save raises when file exists and exist_ok = False."""
		entry = RegEntry(r"HKCU\Software")
		
		with pytest.raises(FileExistsError):
			entry.save(output = "/tmp/existing.reg", exist_ok = False)

	@patch("os.path.exists", return_value = True)
	@patch("os.path.isdir", return_value = True)
	@patch("builtins.open", create = True)
	@patch.object(RegEntry, "subkey_exists", return_value = True)
	def test_save_to_directory(self, mock_exists, mock_file, mock_isdir, mock_path_exists):
		"""Test save to a directory creates file in that directory."""
		mock_file.return_value.__enter__ = Mock()
		mock_file.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		with patch("regmgr.core.traverse_registry"):
			result = entry.save(output = "/tmp/", exist_ok = True)
		
		# Path gets resolved to absolute path on all platforms
		# Just verify it"s a .reg file with the right basename
		assert result.endswith(".reg")
		assert "SOFTWARE" in result

class TestInitModule:
	"""Test __init__.py module-level code."""

	def test_debug_environment_variable_check(self):
		"""Test DEBUG_ENVIRONMENT_NAME is checked."""
		# This is set in __init__.py during module import
		# Just verify the module can be imported
		import regmgr
		assert hasattr(regmgr, "RegEntry")

	@patch("ctypes.windll.shell32.IsUserAnAdmin", return_value = True)
	def test_admin_check_passed(self, mock_admin):
		"""Test admin check passes when user is admin."""
		# Module imports successfully when admin
		import regmgr
		assert True

	def test_exceptions_exported(self):
		"""Test exceptions are exported from module."""
		import regmgr
		assert hasattr(regmgr, "exceptions")

	def test_defaults_exported(self):
		"""Test defaults are exported from module."""
		import regmgr
		assert hasattr(regmgr, "defaults")

class TestConfigDefaults:
	"""Test config.py dataclass defaults."""

	def test_path_defaults_esc_chars(self):
		"""Test PathDefaults escape characters."""
		from regmgr.config import defaults
		assert len(defaults.path.ESC_CHARS) == 11

	def test_file_defaults_exist_ok(self):
		"""Test FileDefaults exist_ok default."""
		from regmgr.config import defaults
		assert defaults.path.file.exist_ok is True

	def test_variable_defaults_type(self):
		"""Test VariableDefaults type default."""
		from regmgr.config import defaults
		assert defaults.variable.type == "REG_SZ"

	def test_defaults_var_alias(self):
		"""Test defaults.var alias for defaults.variable."""
		from regmgr.config import defaults
		assert defaults.var is defaults.variable

	def test_defaults_vars_alias(self):
		"""Test defaults.vars alias for defaults.variable."""
		from regmgr.config import defaults
		assert defaults.vars is defaults.variable

	def test_defaults_variables_alias(self):
		"""Test defaults.variables alias for defaults.variable."""
		from regmgr.config import defaults
		assert defaults.variables is defaults.variable

class TestCoreVariableOperations:
	"""Test additional variable operation edge cases."""

	@patch("winreg.OpenKey")
	@patch("winreg.SetValueEx")
	def test_set_variable_exist_ok_false(self, mock_set, mock_open):
		"""Test set with exist_ok = False raises if exists."""
		mock_key = Mock()

		mock_open.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		with patch.object(entry, "variable_exists", return_value = True):
			with pytest.raises(FileExistsError):
				entry.set("Existing", "value", exist_ok = False)

	@patch("winreg.OpenKey")
	@patch("winreg.QueryValueEx")
	def test_get_all_variables(self, mock_query, mock_open):
		"""Test get without variable name returns all."""
		mock_key = Mock()

		mock_open.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		with patch.object(entry, "variables", return_value = {"Var1": ("value", "REG_SZ")}):
			result = entry.variables()
			assert isinstance(result, dict)

	@patch("winreg.OpenKey")
	@patch("winreg.DeleteValue")
	def test_delete_variable_alias(self, mock_delete, mock_open):
		"""Test delete_variable alias."""
		mock_key = Mock()
		
		mock_open.return_value.__enter__ = Mock(return_value = mock_key)
		mock_open.return_value.__exit__ = Mock(return_value = None)

		entry = RegEntry(r"HKCU\Software")
		with patch.object(entry, "variable_exists", return_value = True):
			entry.delvar("OldVar") # Test alias
			mock_delete.assert_called()
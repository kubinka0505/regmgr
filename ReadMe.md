<img src="https://raw.githubusercontent.com/kubinka0505/regmgr/refs/heads/main/docs/img/Logo.svg" width=150>

<a href="https://github.com/kubinka0505/regmgr/commit"><img src="https://custom-icon-badges.demolab.com/github/last-commit/kubinka0505/regmgr?logo=commit&style=for-the-badge&cacheSeconds=60" alt="Last commit date"></a>　<a href="https://github.com/kubinka0505/regmgr/blob/main/License.txt"><img src="https://custom-icon-badges.demolab.com/github/license/kubinka0505/regmgr?logo=law&color=red&style=for-the-badge&cacheSeconds=60" alt="View license"></a>
<br>
<a href="https://app.codacy.com/gh/kubinka0505/regmgr"><img src="https://img.shields.io/codacy/grade/5d90e0ba6272486d96afc814e081374f?logo=codacy&style=for-the-badge&cacheSeconds=60" alt="View grade"></a>　<a href="https://app.codacy.com/gh/kubinka0505/regmgr/coverage"><img src="https://img.shields.io/codacy/coverage/5d90e0ba6272486d96afc814e081374f?logo=codacy&style=for-the-badge&cacheSeconds=60"></a>

## Description 📝
Simplified wrapper for the Python [`winreg`](https://docs.python.org/library/winreg.html) module. 🗃️

## Installation 🖥️
1. [`git`](https://git-scm.com) (recommended)
```bash
git clone https://github.com/kubinka0505/regmgr
cd regmgr/Files
python setup.py install
```

2. [`pip`](https://pypi.org/project/regmgr)
```bash
python -m pip install regmgr -U
```

> [!WARNING]
> Installing this module on non-NT operating systems will raise error.

---

## Features 📋

- ✔️ User-friendly `pathlib.Path`-alike syntax
- ✔️ Popular `os`-alike function aliases, such as `.mkdir()`, `.getcwd()`, etc.
- ✔️ **Registry keys navigation**<sup>*</sup>
- ✔️ Variables setting
- ✔️ Variables retrieval
- ✔️ Variables removal
- ✔️ Variables renaming
- ✔️ Exporting to `.reg` files
- ✔️ Subkeys creation
- ✔️ **Recursive** subkeys removal<sup>*</sup>
- ✔️ Valid subkey name casing
- ❌ Safety 🥶

<sup>*</sup> - unstable

---

## Usage 📝

> [!TIP]
> `HKEY_CURRENT_USER` **is the only hive that does not require admin privileges to manage.**

> [!TIP]
> To disable the UAC warning, **add the variable named as following** to the environment variables listbefore importing module.
> 
> Letter case is not important. 🙂
>
> https://github.com/kubinka0505/regmgr/blob/90406c159e186c5299744d322f501165a61cc46e/src/regmgr/__init__.py#L22

> [!IMPORTANT]
> Due to the architecture of the registry editor, the relative paths in it's subkey names do not behave as standard directories.
> For example in the `os` module, particulary [os.pardir](https://docs.python.org/3/library/os.html#os.pardir) and [os.curdir](https://docs.python.org/3/library/os.html#os.curdir))
> 
> In order to get a value from a subkey located in a parent one, either a new `RegEntry` object must be created or the `.relcd()` function has to be used.
> 
> ```python
> >>> import regmgr
> >>> reg = regmgr.RegEntry(r"HKEY_CURRENT_USER\Facts")
> >>> 
> >>> # Create it
> >>> reg.mkdir(exist_ok = True)
> >>> 
> >>> # Create another one
> >>> reg.mkdir("I got unusual/unexpected behavior.\..Indeed.")
> >>> reg.subkeys(recursive = True)
> ('I got unusual/unexpected behavior.', 'I got unusual/unexpected behavior.\\..Indeed.')
> ```

> [!CAUTION]
> The `.relcd()` function **does not work with mixed slashes**, as it uses [`os.path.normpath`]().
> 
> If new subkey contains slashes or `/../` sequence, creating new `RegEntry` object is mandatory.
> **Using them is not reccomended.**
>
> ```python
> >>> import regmgr
> >>> reg = regmgr.RegEntry(r"HKCC\Software")
> >>> 
> >>> # Does not work due to `os.path.normpath`
> >>> reg.relcd("Do this/that")
> >>> reg.path
> 'HKEY_CURRENT_CONFIG\\Software\\Do this\\that'
> >>> # ...instead of "HKCC\Software\Do this/that\"
> >>> 
> >>> # back to "HKCC\Software" then
> >>> reg.relcd("../..")
> >>> 
> >>> # Use like this
> >>> new_key = r"My key with slashes/../or dots")
> >>> reg.mkdir(new_key)
> >>> reg = regmgr.RegEntry("\\".join((reg.path, new_key)))
> >>> reg.path
> 'HKEY_CURRENT_CONFIG\\Software\\My key with slashes/../or dots'
> ```

<details>
	<summary><b>Get variables from the registry subkey</b> ⚙️</summary>

```python
>>> import regmgr
>>> 
>>> # Create registry object
>>> reg = regmgr.RegEntry(r"HKLM\Software\Microsoft\Windows NT\CurrentVersion")
>>> 
>>> print("My system is:", reg["ProductName"])
My system is: Windows 10 Home
```
</details>

<details>
	<summary><b>Create new subkey and set new variables</b> ➕</summary>

```python
>>> import regmgr
>>> reg = regmgr.RegEntry(r"HKCU\Software")
>>> reg.relcd("A custom subkey")
>>> 
>>> # Create new subkey
>>> reg.make()
>>> 
>>> # Set new values
>>> reg["1st variable"] = "This is a REG_SZ handler"
>>> 
>>> reg.set("1st variable", "I can be updated", "sz", exist_ok = True)
>>> reg.set("2nd variable", regmgr.converter.str_to_bytes("some string"), "binary")
>>> reg.set("3rd variable", regmgr.converter.hex_to_str("73 74 72 69 6e 67"), "binary")
>>> reg.set("4th variable", 0x0505, "dword") # Hexadecimal
>>> reg.set("5th variable", 1285, "qword")   # Decimal
>>> reg.set("6th variable", ("Each", "word", "is", "a", "line"), "multi_sz")
>>> reg.set("7th variable", "Expandable", "expand_sz")
>>> 
>>> # Navigate to parent subkey
>>> reg.relcd("..")
```
</details>

<details>
	<summary><b>Remove a subkey with all of its contents</b> 🚮</summary>

```python
>>> import regmgr
>>> reg = regmgr.RegEntry(r"HKEY_CURRENT_USER\Software\A custom subkey")
>>> 
>>> # More safe, however `reg.delete_subkeys()` can be executed
>>> current_key = reg.basename
>>> reg.relcd("..")
>>> 
>>> reg.delete_subkeys(current_key)
```
</details>

<details>
	<summary><b>Check if subkey exists</b> 🔎</summary>

```python
>>> import regmgr
>>> 
>>> key = r"HKEY_CLASSES_ROOT\.py"
>>> 
>>> # Default
>>> regmgr.RegEntry(key).exists()
True
>>> 
>>> # Alternative, os-like
>>> regmgr.path.exists(key)
True
```
</details>

<details>
	<summary><b>List subkey's... subkeys</b> 📋</summary>

```python
>>> import regmgr
>>> reg = regmgr.RegEntry(r"HKEY_USERS\.DEFAULT\Control Panel\International")
>>> 
>>> # Basic, iterative
>>> dir(reg)
['Geo', 'User Profile', 'User Profile System Backup']
>>> 
>>> # Advanced, iterative
>>> print("\n".join( reg.subkeys(recursive = False, absolute_paths = True) ))
HKEY_USERS\.DEFAULT\Control Panel\International\Geo
HKEY_USERS\.DEFAULT\Control Panel\International\User Profile
HKEY_USERS\.DEFAULT\Control Panel\International\User Profile System Backup
>>>
>>> # Advanced, recursive
>>> reg.subkeys(recursive = True, absolute_paths = False)
('Geo', 'User Profile', 'User Profile\\en-US', 'User Profile System Backup', 'User Profile System Backup\\en-US')
```
</details>

<details>
	<summary><b>List subkey's variables</b> 🔢</summary>

```python
>>> import regmgr
>>> reg = regmgr.RegEntry(r"HKCU\Software\Microsoft\Accessibility")
>>> 
>>> # Current
>>> reg.as_dict(recursive = False)
{'CursorColor': [65471, 'REG_DWORD'], 'CursorType': [3, 'REG_DWORD'], 'CursorSize': [3, 'REG_DWORD']}
>>> 
>>> # Recursive
>>> reg.as_dict(recursive = True)
{'CursorColor': [65471, 'REG_DWORD'], 'CursorType': [3, 'REG_DWORD'], 'CursorSize': [3, 'REG_DWORD'], 'CursorIndicator': {'IndicatorColor': [16711871, 'REG_DWORD'], 'IndicatorType': [3, 'REG_DWORD']}}
```
</details>

<details>
	<summary><b>Save to `.reg` file</b> 💾</summary>

```python
>>> import regmgr
>>> reg = regmgr.RegEntry(r"HKEY_CURRENT_USER\Control Panel\Quick Actions\Control Center")
>>> 
>>> # Simple
>>> # Inherits the current key name to current location
>>> # Does not write subkeys without subkeys or/and variables
>>> reg.export()
'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\PythonXXX\\Control Center.reg'
>>> 
>>> # Advanced
>>> # Custom location with specified filename, though accepts directories only as well
>>> # Editable argument allows writing keys without any subkeys or/and variables
>>> reg.export("~/custom.reg", editable = True)
'C:\\Users\\Admin\\custom.reg'
>>> 
```
</details>

...and more 🙃

---

## Disclaimer ⚠️

> [!IMPORTANT]
> The coincidence of all sorts of names and audio/visual media is coincidental - the author of this particular software is not affiliated nor with Microsoft or its affiliates, and is not responsible for guaranteeing its correct behavior nor the consequences resulting from its improper use.
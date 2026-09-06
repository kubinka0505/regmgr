<p align=center>
	<img src="https://raw.githubusercontent.com/kubinka0505/regmgr/master/Documents/Pictures/Logo.svg" width=150px>
</p>

<br>

<p align=center>
	<img src="https://img.shields.io/badge/Platform-Windows%207-0078D6?logo=Windows&LogoColor=white&style=for-the-badge">　<a href="http://github.com/kubinka0505/regmgr/commit"><img src="https://custom-icon-badges.demolab.com/github/last-commit/kubinka0505/regmgr?logo=commit&style=for-the-badge"></a>　<a href="http://github.com/kubinka0505/regmgr/blob/master/License.txt"><img src="https://custom-icon-badges.demolab.com/github/license/kubinka0505/regmgr?logo=law&color=red&style=for-the-badge"></a>
</p>

<p align=center>
	<img src="https://custom-icon-badges.demolab.com/github/languages/code-size/kubinka0505/regmgr?logo=database&style=for-the-badge">　<a href="https://github.com/kubinka0505/regmgr/actions/workflows/coverage_test_unit.yml"><img src="https://img.shields.io/codacy/coverage/5d90e0ba6272486d96afc814e081374f?logo=code-climate&style=for-the-badge"></a>

<p align=center>
	<a href="https://codeclimate.com/github/kubinka0505/regmgr"><img src="https://custom-icon-badges.demolab.com/codeclimate/maintainability/kubinka0505/regmgr?logo=code-climate&style=for-the-badge"></a>　<a href="https://app.codacy.com/gh/kubinka0505/regmgr"><img src="https://custom-icon-badges.demolab.com/codacy/grade/5d90e0ba6272486d96afc814e081374f?logo=codacy&style=for-the-badge"></a>
</p>

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
- ❌ Valid subkey name casing
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
> https://github.com/kubinka0505/regmgr/blob/85c3d28eea2c3e352f5c10cd59f841d7342adc97/Files/src/__init__.py#L22

> [!IMPORTANT]
> Due to `winreg` module architecture, **no** way to fix casing in the registry entries paths has been implemented. ~~...yet~~
> ```python
> >>> import regmgr
> >>> reg = regmgr.RegEntry("hkcu\software")
> >>> 
> >>> # Casing is not fixed
> >>> reg.path
> 'HKEY_CURRENT_USER\\software'
> >>> 
> >>> # But key exists
> >>> reg.exists()
> True
> ```

> [!IMPORTANT]
> Due to the architecture of the registry editor, the relative paths in it's subkey names do not behave as directories.
> For example in the `os` module, particulary [os.pardir](https://docs.python.org/3/library/os.html#os.pardir) and [os.curdir](https://docs.python.org/3/library/os.html#os.curdir))
> 
> In order to get a value from a subkey located in a parent one, either a new `RegEntry` object must be created or the `.relcd()` function has to be used.
> 
> ```python
> >>> import regmgr
> >>> reg = regmgr.RegEntry(r"HKEY_CURRENT_USER\Facts")
> >>> 
> >>> # Create it
> >>> reg.create_subkey()
> >>> 
> >>> # Create another one
> >>> reg.create_subkey("I got unusual/unexpected behavior.\..Indeed.")
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
> >>> # back to "HKCC\Software"
> >>> reg.relcd("../..")
> >>> 
> >>> # Use like this
> >>> new_key = r"My key with slashes/../or dots")
> >>> reg.create_subkey(new_key)
> >>> reg = regmgr.RegEntry("\\".join((reg.path, new_key)))
> >>> reg.path
'HKEY_CURRENT_CONFIG\\Software\\My key with slashes/../or dots'
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
>>> reg["1st variable"] = "I am REG_SZ by default"
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
>>> # Default
>>> regmgr.RegEntry(r"HKEY_CLASSES_ROOT\.py").exists()
True
>>> 
>>> # Alternative, os-like
>>> regmgr.path.exists(r"HKCR\.waaah")
False
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
('Geo', 'User Profile', 'User Profile\\pl', 'User Profile System Backup', 'User Profile System Backup\\pl')
```
</details>

<details>
	<summary><b>List subkey's variables</b> 🔢</summary>

```python
>>> import regmgr
>>> reg = regmgr.RegEntry(r"HKEY_CLASSES_ROOT\.exe")
>>> 
>>> print(reg.variables())
{'': ('exefile', 'REG_SZ'), 'Content Type': ('application/x-msdownload', 'REG_SZ')}
```
</details>

...and more 🙃

---

## Disclaimer ⚠️

> [!IMPORTANT]
> The coincidence of all sorts of names and audio/visual media is coincidental - the author of this particular software is not affiliated nor with Microsoft or its affiliates, and is not responsible for guaranteeing its correct behavior nor the consequences resulting from its improper use.
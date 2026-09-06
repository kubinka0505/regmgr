from dataclasses import dataclass, field

# Defaults
@dataclass(frozen = True)
class FileDefaults:
	exist_ok: bool = True
	ESC_CHARS: tuple[str, ...] = ("$", "%")

@dataclass(frozen = True)
class PathDefaults:
	exist_ok: bool = False
	ESC_CHARS: tuple[str, ...] = (
		"\a", "\b", "\f",
		"\1", "\2", "\3",
		"\4", "\5", "\6",
		"\7", "\0",
	)

	file: FileDefaults = field(default_factory = FileDefaults)

@dataclass(frozen = True)
class VariableDefaults:
	value: str = ""
	type: str = "REG_SZ"
	exist_ok: bool = True

@dataclass(frozen = True)
class Defaults:
	path: PathDefaults = field(default_factory = PathDefaults)
	variable: VariableDefaults = field(default_factory = VariableDefaults)

	@property
	def var(self) -> VariableDefaults:
		return self.variable

	@property
	def vars(self) -> VariableDefaults:
		return self.variable

	@property
	def variables(self) -> VariableDefaults:
		return self.variable

defaults = defs = Defaults()

# Exceptions
class exceptions:
	class setup:
		NOT_ADMIN = RuntimeWarning("Not as admin - management of most hives will fail")
		WRONG_OS =  RuntimeWarning("Not on NT operating system")
		ESC_FOUND = SyntaxError("Unterminated escape characters found; use raw string literals")

	class hive:
		REMOVE =    OSError("Attempt of hive removal")
		NOTEXISTS = FileNotFoundError("Path's hive does not exist")

	class path:
		class file:
			EXISTS = FileExistsError("File already exists")

		EXISTS =    FileExistsError("Path already exists")
		NOTEXISTS = FileNotFoundError("Path does not exist")

	class key:
		EXISTS =    FileExistsError("Subkey already exists")
		NOTEXISTS = FileNotFoundError("Subkey does not exist")
		TOO_LARGE = RuntimeError("Subkey is too deep to recursively iterate keys from")

	class variable:
		EXISTS =    FileExistsError("Variable already exists")
		NOTEXISTS = FileNotFoundError("Variable does not exist")
		INCORRECT = ValueError("Unsupported value type met during iteration")

	var = vars = variables = variable
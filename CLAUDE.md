# CLAUDE.md — Project Guidelines

## Python Coding Standards

These rules apply to all code written or modified in `src/`.

### OOP — always use classes

- **Never drop bare functions into a module.** All logic belongs inside a class.
- Each module should have a clear primary class (e.g. `GreenhouseProvider`, `ScoutOrchestrator`).
- Utility helpers that don't carry state go in a dedicated class (e.g. `TitleFilter`, `JobIdGenerator`), not as module-level functions.

### PEP 8

- 4-space indentation, max line length 100 characters.
- `snake_case` for variables, functions, and methods; `PascalCase` for classes; `UPPER_SNAKE` for module-level constants.
- Two blank lines between top-level class definitions; one blank line between methods.
- Imports ordered: stdlib → third-party → local, each group separated by a blank line.

### Idiomatic Python

- Use `@dataclass` for plain data containers instead of bare dicts or ad-hoc classes with only `__init__`.
- Use `@property` to expose computed or validated attributes rather than `get_*` methods.
- Prefer `pathlib.Path` over `os.path` string manipulation.
- Use type annotations on all method signatures (parameters and return types).
- Raise specific exceptions; never `except Exception: pass`.

### Example — preferred style

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CompanyConfig:
    name: str
    careers_url: str
    scan_method: str
    enabled: bool
    scan_method_config: dict = field(default_factory=dict)
    category: str | None = None
    employees: str | None = None

    @property
    def slug(self) -> str | None:
        return self.scan_method_config.get("slug")

    @property
    def api_base(self) -> str | None:
        return self.scan_method_config.get("api_base")
```

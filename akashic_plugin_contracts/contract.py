from __future__ import annotations

import ast
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContractViolation:
    code: str
    line: int
    message: str


@dataclass(frozen=True)
class ContractReport:
    path: str
    sha256: str
    plugin_classes: tuple[str, ...]
    violations: tuple[ContractViolation, ...]

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "plugin_classes": list(self.plugin_classes),
            "passed": self.passed,
            "violations": [asdict(item) for item in self.violations],
        }


def check_plugin(path: Path) -> ContractReport:
    """Parse one plugin entrypoint and report every API v2 contract violation."""

    # 1. 固定被验收源码身份
    source = path.read_bytes()
    tree = ast.parse(source, filename=str(path))

    # 2. 逐个检查 Plugin 子类的版本与生命周期
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and _inherits_plugin(node)
    ]
    violations: list[ContractViolation] = []
    if not classes:
        violations.append(
            ContractViolation("PLG200", 1, "plugin.py 缺少 Plugin 子类")
        )
    for plugin_class in classes:
        violations.extend(_check_class(plugin_class))

    # 3. 输出可供跨仓库 CI 绑定的稳定报告
    return ContractReport(
        path=str(path.resolve()),
        sha256=hashlib.sha256(source).hexdigest(),
        plugin_classes=tuple(item.name for item in classes),
        violations=tuple(violations),
    )


def _check_class(plugin_class: ast.ClassDef) -> list[ContractViolation]:
    violations: list[ContractViolation] = []
    api_version = _class_constant(plugin_class, "api_version")
    if api_version != 2:
        violations.append(
            ContractViolation(
                "PLG201",
                plugin_class.lineno,
                f"{plugin_class.name} 必须显式声明 api_version = 2",
            )
        )
    methods = {
        node.name: node
        for node in plugin_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    legacy = methods.get("initialize")
    if legacy is not None:
        violations.append(
            ContractViolation(
                "PLG202",
                legacy.lineno,
                "API v2 禁止 initialize()，按副作用归入 prepare() 或 activate()",
            )
        )
    violations.extend(
        _require_method_kind(methods, "prepare", asynchronous=True)
    )
    violations.extend(
        _require_method_kind(methods, "activate", asynchronous=False)
    )
    violations.extend(
        _require_method_kind(methods, "retire", asynchronous=False)
    )
    violations.extend(
        _require_method_kind(methods, "terminate", asynchronous=True)
    )
    prepare = methods.get("prepare")
    if prepare is not None:
        violations.extend(_check_prepare_boundary(prepare))
    for name in ("prepare", "activate", "retire", "terminate"):
        method = methods.get(name)
        if method is not None:
            violations.extend(_check_task_ownership(method))
    return violations


def _require_method_kind(
    methods: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    name: str,
    *,
    asynchronous: bool,
) -> list[ContractViolation]:
    method = methods.get(name)
    if method is None:
        return []
    valid = isinstance(method, ast.AsyncFunctionDef) == asynchronous
    if valid:
        return []
    expected = "async" if asynchronous else "同步"
    return [
        ContractViolation(
            "PLG203",
            method.lineno,
            f"{name}() 必须是{expected}方法",
        )
    ]


def _check_prepare_boundary(
    method: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ContractViolation]:
    violations: list[ContractViolation] = []
    for node in ast.walk(method):
        if _attribute_path(node) == ("self", "context", "data_dir"):
            violations.append(
                ContractViolation(
                    "PLG204",
                    node.lineno,
                    "prepare() 不得取得正式 plugin-data 路径",
                )
            )
        if (
            isinstance(node, ast.Call)
            and _attribute_path(node.func) == ("self", "context", "create_task")
        ):
            violations.append(
                ContractViolation(
                    "PLG206",
                    node.lineno,
                    "prepare() 不得启动后台任务，任务只能在 activate() 中启动",
                )
            )
    return violations


def _check_task_ownership(
    method: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ContractViolation]:
    violations: list[ContractViolation] = []
    for node in ast.walk(method):
        if not isinstance(node, ast.Call):
            continue
        if _attribute_path(node.func) == ("asyncio", "create_task"):
            violations.append(
                ContractViolation(
                    "PLG205",
                    node.lineno,
                    "插件生命周期必须用 context.create_task() 绑定 generation scope",
                )
            )
    return violations


def _inherits_plugin(node: ast.ClassDef) -> bool:
    return any(_attribute_path(base)[-1:] == ("Plugin",) for base in node.bases)


def _class_constant(node: ast.ClassDef, name: str) -> object:
    for item in node.body:
        if not isinstance(item, ast.Assign) or len(item.targets) != 1:
            continue
        target = item.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(item.value)
    return None


def _attribute_path(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return tuple(reversed(parts))

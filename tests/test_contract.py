from pathlib import Path

from akashic_plugin_contracts.contract import check_plugin


def test_accepts_explicit_v2_lifecycle(tmp_path: Path) -> None:
    path = tmp_path / "plugin.py"
    path.write_text(
        "from agent.plugins import Plugin\n"
        "class WeatherPlugin(Plugin):\n"
        "    api_version = 2\n"
        "    async def prepare(self):\n"
        "        return None\n"
        "    def activate(self):\n"
        "        self.context.create_task(self.worker())\n"
        "    async def worker(self):\n"
        "        return None\n",
        encoding="utf-8",
    )

    report = check_plugin(path)

    assert report.passed
    assert report.api_version == 2
    assert report.entrypoint == "class"
    assert report.plugin_classes == ("WeatherPlugin",)


def test_rejects_v1_and_candidate_state_write(tmp_path: Path) -> None:
    path = tmp_path / "plugin.py"
    path.write_text(
        "import asyncio\n"
        "from agent.plugins import Plugin\n"
        "class WeatherPlugin(Plugin):\n"
        "    api_version = 1\n"
        "    async def initialize(self):\n"
        "        self.context.data_dir.mkdir()\n"
        "        asyncio.create_task(self.worker())\n",
        encoding="utf-8",
    )

    report = check_plugin(path)

    assert not report.passed
    assert {item.code for item in report.violations} == {
        "PLG201",
        "PLG202",
    }


def test_rejects_prepare_data_dir_and_unscoped_task(tmp_path: Path) -> None:
    path = tmp_path / "plugin.py"
    path.write_text(
        "import asyncio\n"
        "from agent.plugins import Plugin\n"
        "class WeatherPlugin(Plugin):\n"
        "    api_version = 2\n"
        "    async def prepare(self):\n"
        "        self.context.data_dir.mkdir()\n"
        "        self.context.create_task(self.worker())\n"
        "        asyncio.create_task(self.worker())\n",
        encoding="utf-8",
    )

    report = check_plugin(path)

    assert {item.code for item in report.violations} == {
        "PLG204",
        "PLG205",
        "PLG206",
    }


def test_accepts_v3_named_exports_without_plugin_class(tmp_path: Path) -> None:
    path = tmp_path / "plugin.py"
    path.write_text(
        "from agent.plugin_composition import ServiceKey\n"
        "api_version = 3\n"
        "name = 'weather'\n"
        "version = '1.0.0'\n"
        "inject = (ServiceKey('clock'),)\n"
        "async def apply(ctx, config):\n"
        "    await ctx.spawn(worker(), name='weather')\n",
        encoding="utf-8",
    )

    report = check_plugin(path)

    assert report.passed
    assert report.api_version == 3
    assert report.entrypoint == "module"
    assert report.plugin_classes == ()


def test_accepts_v3_with_transition_v2_class(tmp_path: Path) -> None:
    path = tmp_path / "plugin.py"
    path.write_text(
        "from agent.plugins import Plugin\n"
        "api_version = 3\n"
        "name = 'weather'\n"
        "version = '1.0.0'\n"
        "def apply(ctx, config):\n"
        "    return None\n"
        "class WeatherPlugin(Plugin):\n"
        "    api_version = 2\n",
        encoding="utf-8",
    )

    report = check_plugin(path)

    assert report.passed
    assert report.api_version == 3
    assert report.plugin_classes == ("WeatherPlugin",)


def test_rejects_invalid_v3_identity_signature_and_task(tmp_path: Path) -> None:
    path = tmp_path / "plugin.py"
    path.write_text(
        "import asyncio\n"
        "api_version = 3\n"
        "name = ' '\n"
        "version = ''\n"
        "async def apply(context, config, extra):\n"
        "    asyncio.create_task(worker())\n",
        encoding="utf-8",
    )

    report = check_plugin(path)

    assert {item.code for item in report.violations} == {
        "PLG301",
        "PLG303",
        "PLG304",
    }


def test_rejects_v3_without_apply(tmp_path: Path) -> None:
    path = tmp_path / "plugin.py"
    path.write_text(
        "api_version = 3\n" "name = 'weather'\n" "version = '1.0.0'\n",
        encoding="utf-8",
    )

    report = check_plugin(path)

    assert {item.code for item in report.violations} == {"PLG302"}

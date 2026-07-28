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

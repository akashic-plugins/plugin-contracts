# Akashic Plugin Contracts

这个仓库拥有 Akashic Plugin API v2 的跨仓库静态门控。它不加载插件，也不读取正式
workspace；只解析候选仓库的 `plugin.py`。

```bash
python -m akashic_plugin_contracts check /path/to/plugin.py
```

当前硬规则：

- `Plugin` 子类必须显式声明 `api_version = 2`；
- 禁止旧 `initialize()` 生命周期；
- `prepare()` 与 `terminate()` 必须是 async，`activate()` 与 `retire()` 必须同步；
- `prepare()` 不能取得正式 `context.data_dir`；
- 生命周期不得绕过 `context.create_task()` 直接调用 `asyncio.create_task()`。

命令成功时返回 0，并输出绑定文件 SHA-256 的 JSON；违反契约时返回 1。

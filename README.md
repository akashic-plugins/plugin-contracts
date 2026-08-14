# Akashic Plugin Contracts

这个仓库拥有 Akashic Plugin API v2/v3 的跨仓库静态门控。它不加载插件，也不读取正式
workspace；只解析候选仓库的 `plugin.py`。

```bash
python -m akashic_plugin_contracts check /path/to/plugin.py
```

当前硬规则：

- 模块声明 `api_version = 3` 时，必须提供非空 `name`、`version` 与精确的 `apply(ctx, config)`；
- API v3 不要求继承 `Plugin`，直接后台任务必须用 `ctx.spawn()` 绑定 Fiber scope；
- `Plugin` 子类必须显式声明 `api_version = 2`；
- 禁止旧 `initialize()` 生命周期；
- `prepare()` 与 `terminate()` 必须是 async，`activate()` 与 `retire()` 必须同步；
- `prepare()` 不能取得正式 `context.data_dir`；
- `prepare()` 不能启动后台任务；
- 生命周期不得绕过 `context.create_task()` 直接调用 `asyncio.create_task()`。

迁移期允许同一文件同时提供 v3 模块入口与 v2 `Plugin` 类；两套声明都会校验。命令成功时返回 0，并输出 API version、entrypoint 与文件 SHA-256 的 JSON；违反契约时返回 1。

#!/usr/bin/env -S uv run 

import deny_rust
import time
from plugins.deny_filter.deny import DenyListConfig
from plugins.deny_filter.deny_rust import DenyListPluginRust
from mcpgateway.plugins.framework import PluginContext,PluginConfig
from mcpgateway.plugins.framework.hooks.prompts import PromptHookType
from mcpgateway.plugins.framework.models import GlobalContext
from mcpgateway.plugins.framework.hooks.prompts import PromptPrehookPayload

import asyncio



async def main():
    words=["malware", "danger", "secret"]
    deny_list = deny_rust.DenyList(words)
    
    start = time.perf_counter()
    result3 = deny_list.scan_str("ok danger")
    elapsed3 = time.perf_counter() - start
    print(f"test scan str: {result3} (took {elapsed3:.6f}s)")

    start = time.perf_counter()
    result4 = deny_list.scan_str("        ok")
    elapsed4 = time.perf_counter() - start
    print(f"test scan str: {result4} (took {elapsed4:.6f}s)")


    start = time.perf_counter()
    result1 = deny_list.scan({"path": "ok danger"})
    elapsed1 = time.perf_counter() - start
    print(f"test deny_list : {result1} (took {elapsed1:.6f}s)")

    start = time.perf_counter()
    result2 = deny_list.scan({"asdf": "        ok"})
    elapsed2 = time.perf_counter() - start
    print(f"test deny_list : {result2} (took {elapsed2:.6f}s)")

    start = time.perf_counter()
    result1 = deny_list.scan({"path": "ok danger"})
    elapsed1 = time.perf_counter() - start
    print(f"test deny_list : {result1} (took {elapsed1:.6f}s)")


    gctx = GlobalContext(request_id="deny-test-batch")
    ctx = PluginContext(global_context=gctx)
    plugin_cfg = PluginConfig (
        name="deny_test",
        kind=f"{DenyListPluginRust.__module__}.{DenyListPluginRust.__name__}",
        hooks=[PromptHookType.PROMPT_PRE_FETCH],
        priority=100,
        config={"words":words}
    )
    p = DenyListPluginRust(config=plugin_cfg)
    start = time.perf_counter()
    payload = PromptPrehookPayload(
        prompt_id="test", args={"text": "         ok"}
    )


    result2 = await p.prompt_pre_fetch(payload,ctx)
    elapsed2 = time.perf_counter() - start
    print(f"test deny_list : {result2.violation} (took {elapsed2:.6f}s)")




if __name__ == "__main__":
    asyncio.run(main())
"""Run the actual fetch wrapper in Node; no browser or network required."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_frontend_rejects_provider_failure_even_with_http_200():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for this frontend regression (available in CI)")
    source = Path("learnctl/web/static/app.js").read_text(encoding="utf-8")
    api = source[source.index("async function api("):source.index("\nfunction escapeHtml")]
    script = r'''
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const apiSource = fs.readFileSync(0, "utf8");
(async () => {
  // The provider failure envelope uses HTTP 200 in learnctl; it must reject.
  for (const path of ["test", "chat", "generate", "review"]) {
    const ctx = {fetch: async () => ({ok:true, status:200,
      json:async () => ({ok:false, error:"HTTP 401，鉴权失败"})})};
    vm.createContext(ctx);
    vm.runInContext(apiSource, ctx);
    await assert.rejects(ctx.api("POST", `/api/ai/${path}`, {}), /HTTP 401/);
    // A corrected key/healthy provider must succeed using the same wrapper.
    ctx.fetch = async () => ({ok:true, status:200, json:async () => ({ok:true, content:"恢复成功"})});
    assert.equal((await ctx.api("POST", `/api/ai/${path}`, {})).content, "恢复成功");
    ctx.fetch = async () => ({ok:false, status:503, json:async () => ({ok:true})});
    await assert.rejects(ctx.api("POST", `/api/ai/${path}`, {}), /HTTP 503/);
    ctx.fetch = async () => ({ok:true, status:200, json:async () => {throw Error("invalid JSON");}});
    await assert.rejects(ctx.api("POST", `/api/ai/${path}`, {}), /不是合法 JSON/);
  }
})().catch(error => {process.stderr.write(String(error)); process.exitCode = 1;});
'''
    result = subprocess.run([node, "-e", script], input=api, text=True, encoding="utf-8",
                            capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr

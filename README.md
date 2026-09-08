# Clash MRS 自动更新

每天北京时间／新加坡时间 09:00 检查 Loyalsoldier/clash-rules 的 release 分支。
仅同步 direct.txt、reject.txt、cncidr.txt，有内容变化时使用 mihomo 转换为 MRS，并提交到本仓库 release 分支。转换失败时不发布。支持 Actions → Update MRS rules → Run workflow 手动运行。

工作流必须位于默认分支 master。使用内置 GITHUB_TOKEN，无需额外 Secret；仓库策略须允许 Actions 写入内容，release 分支须允许机器人推送。
GitHub 定时任务可能延迟；公开仓库连续 60 天无活动时，定时任务可能被停用，需在 Actions 页面重新启用。

## MRS 文件 Raw 链接

- **直连域名列表（direct.mrs）**：[https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/direct.mrs](https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/direct.mrs)
- **广告域名列表（reject.mrs）**：[https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/reject.mrs](https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/reject.mrs)
- **中国大陆 IP 地址列表（cncidr.mrs）**：[https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/cncidr.mrs](https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/cncidr.mrs)

## Mihomo 配置

```yaml
rule-providers:
  direct:
    type: http
    behavior: domain
    format: mrs
    url: https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/direct.mrs
    path: ./ruleset/direct.mrs
    interval: 86400
  reject:
    type: http
    behavior: domain
    format: mrs
    url: https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/reject.mrs
    path: ./ruleset/reject.mrs
    interval: 86400
  cncidr:
    type: http
    behavior: ipcidr
    format: mrs
    url: https://raw.githubusercontent.com/Dowsion-dev/clash-rules/release/cncidr.mrs
    path: ./ruleset/cncidr.mrs
    interval: 86400
rules:
  - RULE-SET,reject,REJECT
  - RULE-SET,direct,DIRECT
  - RULE-SET,cncidr,DIRECT,no-resolve
```

将上述规则合并到现有配置，放在最终 MATCH 规则之前。需要支持 MRS 的 mihomo 内核。

## 构建与来源

固定 mihomo v1.19.30，并验证 GitHub 发布附件提供的 SHA256。修改 scripts/build.py 中的 VERSION 可升级转换器，下一次运行会重新生成。
每次读取上游一个固定提交，避免混用不同版本；release/sources 保留原始 YAML，manifest.json 记录来源提交和输入、输出 SHA256。无变化时跳过转换和提交。

- 上游：https://github.com/Loyalsoldier/clash-rules
- 转换器：https://github.com/MetaCubeX/mihomo
- 格式说明：https://wiki.metacubex.one/config/rule-providers/
- 上游规则许可证：GPL-3.0，见 LICENSE。保留原始规则供追溯。

本工作流替代 Fork 继承的旧 run.yml，避免旧流程强制覆盖 release 分支。产物发布在 release 分支，不创建每日 GitHub Release。

# Free Proxy Airport v7

机场级体验的 Clash Verge / Mihomo 免费节点订阅系统。GitHub Actions 每 30 分钟自动聚合公开免费节点源，执行真实延迟测试，剔除超时和无效节点，并按健康评分生成自动分组。

## Clash Verge 使用方式

Profiles -> Add URL:

```text
https://sunmiao4458.github.io/free-proxy-airport/clash.yaml
```

## 自动更新

工作流名称：`AI Self-Healing Proxy v7`

节点源：

- openRunner clash-freenode
- snakem982 proxypool
- Flikify Free Node
- free-clash-v2ray GitHub Pages

核心能力：

- 真实测速和 timeout 自动剔除
- 节点健康评分排序
- HK / JP / US / AI 自动分组
- FALLBACK 自动降级
- OpenAI / ChatGPT / Claude / Anthropic 智能分流

输出文件：

```text
output/clash.yaml
docs/clash.yaml
```

请仅在遵守当地法律法规和相关服务条款的前提下使用。

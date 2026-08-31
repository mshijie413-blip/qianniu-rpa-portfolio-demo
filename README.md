# Reliable Desktop RPA Portfolio Demo

一个与具体平台解耦的可靠桌面自动化演示，重点展示“宁可停止，也不写入猜测数据”的安全门禁。

> 这是脱敏作品集重构版，不包含平台控件定位、真实订单、买家信息、账号、验证码处理或公司部署脚本。所有数据均为合成样例。

## 安全链路

```text
订单号文本校验
→ 搜索框回读一致
→ 唯一候选确认
→ 候选昵称与资料卡一致
→ 客户字段连续读取两次一致
→ 同主订单多行统一回填
→ 原子保存
→ 历史检查点
```

任何校验失败都会抛出 `SafetyStop`，不会写入不确定结果。

## 运行

```bash
python3 rpa_reliability_demo.py sample_orders.json
python3 -m unittest -v test_rpa_reliability_demo.py
```

真实项目还包含 Windows/macOS 客户端适配、暂停恢复、日志审计和异常保存。本仓库只保留可公开、可迁移的可靠性模式。

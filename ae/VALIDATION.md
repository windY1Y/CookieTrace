# 验证记录

制作日期：2026-09-21。

已验证：

- 在本机 WSL Ubuntu 24.04 / x86-64 下执行 16 项 Python unittest，全部通过。
- 包括真实 Linux 子进程的超时、异常退出、进程组清理、不影响无关进程，及本地 HTTP 示例服务。
- 包括半写入 JSON、缺少阶段时间戳、旧 run ID、错误 cookie 名、错误示例来源的拒绝逻辑。
- 包括模拟浏览器下的完整 runtime 流程（启动、生成文件、校验、整理输出、清理）。
- 包括参数约束、路径含空格、bind mount 目标和默认无代理设置。
- 包括模拟 Docker 下的宿主机创建/启动/退出码确认/清理，以及实际 image ID 记录。
- Bash 语法检查通过；从其他工作目录调用 run.sh --demo --dry-run 验证默认路径不依赖当前目录。

尚未验证：

- 本机没有可用 Docker Engine，尚未实际构建本包镜像或测试 Docker 容器启动。
- 本机没有服务器的完整 Chromium out/sys，尚未用真实 CookieTrace 跑 --check / --demo。
- 尚未测试实际二进制在该容器中的 ABI/共享库组合、Xvfb 启动及具体网页兼容性。
- 尚未测量运行时资源峰值或最低内存。

请不要把模拟浏览器测试等同于真实 CookieTrace 成功运行。完成真实验证的最短命令见 README 第 3 节。如果失败，请保留最新结果目录的 status.json、browser.log、xvfb.log、preflight.json（如已生成）及 launcher.json；它们足以区分路径、依赖、启动和系统内部分析问题。

本次没有在服务器创建、修改或删除文件，没有运行远程浏览器、容器或编译命令。

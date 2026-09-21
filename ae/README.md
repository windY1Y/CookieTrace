# CookieTrace AE 启动包

用途：让现有 Linux x86-64 CookieTrace 浏览器在独立环境中启动，生成可检查的 cookie 来源 JSON。无需修改或重新编译当前浏览器，也无需 Selenium、ChromeDriver、作者 profile 或 Consent-O-Matic。

本包只有启动脚本、Dockerfile、示例与测试，**不包含 Chromium 二进制，也不包含已经构建好的 Docker 镜像**。

## 1. `out/sys` 放在哪里

推荐把本包作为独立目录，位置关系如下：

```text
CookieTrace-AE/
├── run.sh
├── launcher.py
├── README.md
├── docker/
│   ├── Dockerfile
│   └── runtime.py
├── tests/
├── browser/
│   └── sys/                     ← 你的 out/sys，保留其内部相对位置
│       ├── chrome
│       ├── icudtl.dat
│       ├── resources.pak
│       ├── chrome_100_percent.pak
│       ├── chrome_200_percent.pak
│       ├── snapshot_blob.bin
│       ├── v8_context_snapshot.bin
│       ├── locales/
│       └── ...其他运行时文件/动态库
└── results/                     ← 启动器自动创建
    └── <UTC时间>-<唯一ID>/
        ├── status.json
        ├── sources.json         ← 成功时生成
        ├── paths.json           ← 成功时生成
        ├── browser.log
        ├── xvfb.log
        ├── command.json
        ├── launcher.json
        ├── preflight.json
        └── raw/                 ← 浏览器原始输出
```

**也可以完全不移动、不复制现有 out/sys**：每次使用 `--browser-dir /原来的/out/sys`。该目录以只读方式挂载，脚本不会在其中写入 profile、日志或结果。默认的 `browser/sys` 和 `results` 相对于 `launcher.py`，与当前 shell 所在目录无关；你显式传入的相对路径则相对于当前 shell 目录。

不要只放一个 `chrome`。最初验证时直接指向完整 `out/sys` 最稳妥；对外发布时可以另行裁剪 `obj/`、编译工具和测试二进制，但需要保留实际运行依赖并重新执行 `--check`、`--demo`。源码 `.cc/.h`、完整 Chromium 源树和 ChromeDriver 不参与本启动器运行。若目录里存在指向外部文件的符号链接，需在分发运行包中包含真实目标文件。

## 2. 宿主机要求

- Linux x86-64；宿主机 Python 3.9+、Bash。
- 可使用的本地 Docker Engine，当前用户具有运行 Docker 的权限。
- 浏览器必须是你的 instrumented Chromium 108 Linux x86-64 构建，不能替换成普通 Chrome。
- 构建运行环境需要下载 Debian 镜像和软件包；已构建镜像下的 `--demo` 默认禁用外部网络。

脚本不自动安装 Docker，不修改用户组，也不执行 sudo。仅提供 Linux 运行路线；ARM 模拟执行、Windows 原生执行和 macOS 原生执行未验证。WSL 中使用时需要可用的本地 Linux Docker daemon。

## 3. 最短使用流程

在解压后的目录执行：

```bash
# 只构建轻量运行环境；不会把庞大的 browser/sys 放入镜像。
bash run.sh --build

# 默认读取本包的 browser/sys；检查资源文件、架构及共享库。
bash run.sh --check

# 本地页面写入 ct_demo_cookie，验证实际生成的来源 JSON。
bash run.sh --demo
```

不要求 `run.sh` 有可执行位，因为上面显式用 Bash。`chrome` 及运行时可执行程序应保留原有可执行权限。

### 直接使用你服务器上的现有目录

```bash
bash run.sh --build

bash run.sh --check \
  --browser-dir /data/backtrack/yangyi-experiments/arcanum/chromium/src/out/sys

bash run.sh --demo \
  --browser-dir /data/backtrack/yangyi-experiments/arcanum/chromium/src/out/sys \
  --timeout 120
```

以上是供你执行的命令；本次制作过程中没有在服务器执行它们。你运行时会创建 Docker 镜像、临时容器和本包下的结果文件，但不会修改原始 `out/sys` 或服务器原有的 `results_new`。

### 分析真实网页

把下面 URL 和 cookie 名换成你已知会写入目标 cookie 的页面：

```bash
bash run.sh \
  --url 'https://your-test-site.example/path' \
  --cookie-name '_ga' \
  --timeout 600 \
  --output-dir ./results
```

不要把这个示例域名当成实际测试站。真实站点可能受地区、访问状态、站点变化影响；未生成 cookie 会超时，不能解释为系统已成功分析。

## 4. 如何绕过内部写死的路径

启动器把本次运行的 `raw/` 挂载为容器内部的：

```text
/data/backtrack/yangyi-experiments/results_new/
```

因此内部两个 `std::ofstream` 入口都直接写到你的结果目录。**宿主机无需创建这条固定路径，不创建 symlink，不挂载服务器原有的同名目录。** 这只是容器内文件系统映射；内部 C++ 常量仍未修改。若换成另一个写死其他路径的构建，需要调整启动器的 `INTERNAL_OUTPUT` 与 runtime 的 `RAW`，并重新构建运行镜像。

每次运行新建 UUID、容器和临时 profile。内部 `accessing_domain` 固定为安全文件名前缀 `job`，真实 URL 通过独立参数传给浏览器并记录在 `command.json`。已检查的当前补丁中，该 flag 用于输出命名；若未来源码给它新增了其他语义，应同时更新启动器。

## 5. 目标 cookie 的匹配限制

当前系统内部不是通用 exact-name 匹配器：它取 cookie 名第一个数字之前的部分，并与 `cookie_prefix` 做相等比较。

- `--cookie-name __cmpconsent123`：传给引擎 `__cmpconsent`，然后验证结果中真实 cookie 名必须是 `__cmpconsent123`。
- 若引擎先分析到 `__cmpconsent456`，启动器不会把它报成成功；日志会指出目标不匹配。这种内部提前停止不能靠脚本修复。
- `--cookie-prefix __cmpconsent`：明确接受该 legacy prefix 对应的 cookie，不要求某一个数字后缀。
- `--cookie-prefix` 不是任意 starts-with 匹配。例如 `_ga` 不会匹配内部算出的 `_ga_`。
- 本启动器为避免 V8 flag 解析歧义，只接受字母/下划线开头、包含字母数字下划线点号连字符的名称；这不是对所有合法 HTTP cookie 名称的完整实现。

## 6. 代理、证书和网络

默认没有固定代理，而且清除浏览器进程继承的代理环境变量。默认 `--demo`/`--check` 使用 `--network none`，真实 URL 使用 Docker bridge 网络。

如果你在 Linux 宿主机 `127.0.0.1:7895` 有代理：

```bash
bash run.sh --url 'https://your-test-site.example/' --cookie-name '_ga' \
  --network host --proxy http://127.0.0.1:7895
```

容器 bridge 模式的 `127.0.0.1` 不代表宿主机，因此启动器会拒绝这种容易误用的组合。容器能直接访问的远程代理可在 bridge 模式使用。代理 URL 不支持内嵌用户名密码。

对于你在宿主机启动的本地测试站，也要用 `--network host`，或给出容器能访问的地址。内置 demo 不需要 host 网络，它的 HTTP 服务和浏览器位于同一容器。

证书检查默认开启。受控 HTTPS 回放环境确实需要忽略证书时，显式添加 `--ignore-certificate-errors`。

## 7. 完成标准、超时和退出码

成功要求：本次唯一 ID 对应的两个 JSON 能解析，sources 非空且具备预期字段，path 包含目标 cookie、source_scripts 和至少三个阶段时间戳，文件内容保持稳定。`--demo` 还检查来源包含 `ct_demo_cookie`、`ct_demo_value`，且写入值正确。

成功后会停止浏览器，因此**这里不是 document.readyState 全页加载性能计时脚本**。这是最小运行/功能入口，不能用它的 elapsed_seconds 替代论文的性能指标。

| 退出码 | 含义 |
|---:|---|
| 0 | 功能结果通过检查，或 --check 预检通过 |
| 2 | 参数、依赖、容器或运行环境错误 |
| 3 | 浏览器正常退出，但没有合格结果 |
| 4 | 浏览器异常退出 |
| 124 | 超时，可能包括目标 cookie 未出现或输出不匹配 |
| 130 | 用户中断 |

详细原因看 `status.json`、`browser.log`。`--check` 通过仅证明静态依赖齐备，不等于浏览器功能通过。退出码 0 的功能结果也只证明这个目标产生了符合检查的输出，不证明所有论文结论或整个算法正确。

脚本只清理自己创建的进程组和带本次唯一标签的容器，绝不按 `chrome` 名称杀进程。输出保留，profile 随临时容器清理。宿主机异常断电或 Docker daemon 中断时可能留下容器；启动器会打印本次唯一容器名供定位。

## 8. 可选资源限制与排查

```bash
# 查看计划，不创建输出、不访问 Docker、不运行浏览器
bash run.sh --demo --dry-run

# 可选限额，仅表示你选择的实验配置；不是已验证最低需求
bash run.sh --demo --cpus 2 --memory 8g --shm-size 1g

# 自定义浏览器和输出目录（含空格时加引号）
bash run.sh --demo --browser-dir '/path with spaces/out/sys' \
  --output-dir '/path with spaces/results'

# 脚本自身的测试，不需要真实 Chromium/Docker
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

如遇 OOM，可查看 `launcher.json` 的 `container_oom_killed`、Docker 状态和 browser.log。容器默认提供 1 GiB `/dev/shm` 和 1 GiB 临时目录；这些是当前默认配置，尚未经过真实浏览器资源标定。当前 image tag 为 `cookietrace-ae:debian12-v1`。修改 `docker/runtime.py` 后要重新 `--build`。构建只上传 `docker/`，不会上传 browser/sys 或原始数据。

正式发布时应固定 `--base-image debian@sha256:...` 的已验证 digest，并保存生成镜像。当前 Dockerfile 使用 Debian 12 tag 和当时软件源；不是位级可重现构建。每次运行会记录实际 image ID。

## 9. 解决范围与待验证事项

已通过启动器解决/规避：固定输出路径、工作目录依赖、固定代理、缺失 profile、无桌面启动、Python 2/Selenium 依赖、URL 当文件名、同名输出覆盖、缺少超时、清理误杀其他 Chrome、结果错误却报成功。

没有修改浏览器 C++，因此没有声称修复以下内部问题：

- 栈地址转换为 int，以及 unsigned long 的跨平台地址表示。
- 全局分析状态在同一个 renderer 多 isolate 等场景的隔离。
- 内部 cookie prefix 选择逻辑及可能的首次匹配提前停止。
- 相同浏览器进程树内多个 renderer 对同名文件的竞争写入。

每次一个目标、新浏览器和独立容器可以隔离不同运行之间的状态与文件，但不能替代这些内部修复。真实 CookieTrace 的最小示例尚需执行；见 `VALIDATION.md`。

目录映射依据：[Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)。

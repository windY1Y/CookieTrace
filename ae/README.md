# CookieTrace artifact evaluation

This artifact accompanies *Chasing Cookies to the Source: In-browser Data Flow Backtracking for Cookie Compliance Triage* (NDSS 2027). CookieTrace traces a target cookie write back to contributing literals and scripts in an instrumented Chromium browser.

Repository: https://github.com/windY1Y/CookieTrace

## Package layout

The repository and extracted browser have the following layout:

```text
CookieTrace/
  README.md
  cookietrace.patch
  measure/
  data_processing/
  statistics/
  ae/
    README.md
    REPRODUCING.md
    run.sh
    launcher.py
    docker/
      Dockerfile
      runtime.py
      examples/          # readable local HTML and JavaScript fixtures
    browser/
      sys/
        chrome
        icudtl.dat
        resources.pak
        locales/
        ... other runtime files from the same build ...
    results/              # generated locally; not committed
```

Download the prebuilt custom browser from the [AE runtime release](https://github.com/windY1Y/CookieTrace/releases/tag/ae-runtime-v1). The release archive contains the matching Linux x86-64 executable, resources, shared libraries, locales, build metadata, and per-file checksums. Git source archives do not include this binary asset.

From the repository root, download and extract it:

```bash
mkdir -p ae/browser
cd ae/browser
curl -fL --retry 3 -O https://github.com/windY1Y/CookieTrace/releases/download/ae-runtime-v1/cookietrace-chromium108-linux-x86_64.tar.gz
curl -fL --retry 3 -O https://github.com/windY1Y/CookieTrace/releases/download/ae-runtime-v1/SHA256SUMS
sha256sum -c SHA256SUMS
tar -xzf cookietrace-chromium108-linux-x86_64.tar.gz
sha256sum -c BROWSER_FILES_SHA256SUMS
cd ../..
```

The executable is then `ae/browser/sys/chrome`. Keep its adjacent resource files and `locales/` directory together. Do not substitute a stock Chrome installation. Downloading and checksum verification require `curl`, `tar` with gzip support, and `sha256sum` in addition to the runtime prerequisites below.

## Prerequisites

Use x86-64 Linux, Bash, Python >=3.9, and a local Linux Docker daemon accessible to your account. We recommend 8 CPU cores and 16 GB RAM with one browser at a time. No GPU or desktop display is needed: the container starts Xvfb. Native Windows/macOS and emulation are not validated. On Windows, transfer the bundle to an x86-64 Linux environment before evaluation.

## Start here

Run these commands from the repository root:

```bash
chmod u+x ae/browser/sys/chrome
bash ae/run.sh --build
bash ae/run.sh --check
bash ae/run.sh --demo
```

`--build` builds the Debian 12 runtime image only. It does not build Chromium, run a demo, or download the custom browser. `--check` checks the bundle, ELF architecture, shared libraries, and runtime prerequisites; it is not a successful browser experiment. `--demo` launches the real browser on a local page and validates the target cookie and source/path JSON. By default it uses no external network. Docker image construction needs Internet access unless dependencies are already available.

A successful demo exits with code 0 and writes `status.json` with `status: success`, plus `sources.json` and `paths.json`. The checker verifies the demo cookie `ct_demo_cookie=ct_demo_value`, the expected name/value literals, and completed trace metadata. Inspect these outputs as well as the exit code. The demo does not establish the paper's accuracy or performance claims.

## Local examples and readable results

The HTML and JavaScript fixtures are in `ae/docker/examples/`:

| Case | Files | What it exercises |
|---|---|---|
| `direct` (default) | `direct.html`, `direct.js` | Cookie assignment from name and value literals |
| `function` | `function.html`, `function.js` | A cookie value returned by a helper function |

After downloading the browser and building the runtime, run:

```bash
bash ae/run.sh
bash ae/run.sh --demo --demo-case function
```

Calling `run.sh` without arguments runs the default demo. The launcher starts an internal local HTTP server automatically, serves the chosen HTML/JS fixture, and stops it when the run ends. No URL, cookie argument, external website, or separate web server is needed. Both fixtures write `ct_demo_cookie=ct_demo_value`; the trace checker looks for the cookie name and value literals in the generated source records.

At the end, the terminal prints the run directory and the path to **report.html**. Open that file in a normal browser to inspect the actual observed cookie, literal sources, script names, and positions. **summary.txt** contains the same concise results for terminal inspection. Raw `sources.json`, `paths.json`, and logs remain alongside the report. A failed run is displayed as a failure; expected demo values are labeled separately from actual observations.

Rebuild the runtime with `bash ae/run.sh --build` after updating from the previous launcher version. This version uses the `cookietrace-ae:debian12-v2` runtime tag and packages the fixture files into the image. The prebuilt Chromium download is unchanged.

## Run a target website

```bash
bash ae/run.sh --url https://YOUR-SITE --cookie-name YOUR_COOKIE --timeout 600
```

Replace the two uppercase values with a real workload URL and target cookie. There is no assumption that an arbitrary example domain sets the requested cookie. This command performs the single-site browser execution role of `measure/single_site.sh`. It uses a fresh profile, a unique run ID, an isolated output directory, and explicit completion checks. It does not copy the old runner's profile template or perform consent-button interactions. If a cookie requires a particular consent action, login, or profile state, that workload needs an explicit interaction procedure before it can be reproduced.

The legacy runner's second argument is documented by the original repository as an optional script placeholder; the new launcher selects the cookie by name/prefix. This package uses `browser/sys/chrome`. Set the legacy script's `CHROME_BIN` to the intended CookieTrace executable if using that entry point directly.

Internally, the current engine compares the cookie-name prefix before its first digit. `--cookie-name` additionally checks the full name in the output, but cannot change this internal selection behavior. If several cookies share a prefix, inspect the exact cookie and report ambiguity; do not count a different cookie as a successful target.

## Paths, proxy, and outputs

```bash
bash ae/run.sh --demo --browser-dir /ABSOLUTE/PATH/sys --output-dir /ABSOLUTE/PATH/results
bash ae/run.sh --url https://YOUR-SITE --cookie-name YOUR_COOKIE --timeout 600 \
  --network host --proxy http://127.0.0.1:7895
```

The proxy is optional and disabled by default. The second command is only for evaluators who actually run that proxy locally. Normal HTTPS certificate verification remains enabled. The paper's German egress can affect live consent behavior.

Defaults are relative to the launcher directory, not the shell's current directory. Each run gets a new directory under `ae/results/`. The container binds its hardcoded internal output path `/data/backtrack/yangyi-experiments/results_new` to that run's `raw/` directory. This redirects filesystem writes without changing or recompiling V8, and does not require creating the authors' `/data/...` directory on the host. An environment variable or changing the current directory alone would not redirect those writes.

Outputs include status/configuration records, browser logs, raw engine JSON and, on success, normalized `sources.json` / `paths.json`. Preserve raw files when diagnosing errors. The new run IDs are not the legacy four-digit IDs; old post-processing scripts that parse filenames may require an adapter. Do not assume renaming files alone preserves website identity or deduplication keys.

Exit codes: 0 success; 2 setup/configuration error; 3 browser exited without a valid result; 4 browser failure; 124 timeout; 130 interruption. A timeout is not evidence that the cookie has no sources. The launcher stops only its own container.

## E2: effectiveness tables

The paper's effectiveness results were calculated from `statistics/effectiveness_original.csv` and `statistics/effectiveness_deduplicated.csv`. These files contain the per-cookie ground-truth and detection counts used for the original and deduplicated evaluations. Review the supplied tables alongside Tables II-III in the paper. E2 requires no browser rerun, data recollection, or analysis command.

## Analysis dependencies

For the Python analysis scripts, use a separate analysis environment:

```bash
python3 -m venv ae/.venv-analysis
source ae/.venv-analysis/bin/activate
python -m pip install numpy scipy pandas matplotlib seaborn tldextract
```

The runtime Docker image is for browser execution; analysis commands below run in this Python environment. The JavaScript scripts in `data_processing/characterization/` use Node.js; install the dependencies declared in their respective package files before running them.

See [REPRODUCING.md](REPRODUCING.md) for the script-to-experiment mapping and analysis commands. The `ae/analysis/` scripts are adapted from the supplied research tree; `analysis/PROVENANCE.md` records their original locations.

## Artifact appendix

The [artifact appendix](docs/CookieTrace_Artifact_Appendix.pdf) provides the evaluation workflow. Its [editable source](docs/CookieTrace_Artifact_Appendix.tex) is included alongside it.

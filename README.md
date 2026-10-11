# CookieTrace

This repository contains the artifacts for our paper **“Chasing Cookies to the Source: In-browser Data Flow Backtracking for Cookie Compliance Triage”**, accepted at **NDSS 2027**.

CookieTrace is a browser-based data flow backtracking framework that traces cookie writes to their underlying data sources and identifies the responsible scripts, supporting fine-grained cookie compliance analysis.

Below, we describe the repository structure and the purpose of its main files and directories.

- `cookietrace.patch`: Patch file for CookieTrace. We built the prototype based on [Arcanum](https://github.com/BEESLab/Arcanum). Arcanum includes two patch files, and CookieTrace is an implementation extending their `v8.patch`.
  - We integrated [nlohmann](https://github.com/nlohmann/json) into `v8/src/third_party` to output tracking results in JSON format. This addition accounts for approximately 20,000 lines in the patch (as shown in the final git diff). Our actual contributions comprise roughly 4,000 lines of code.
- `measure/`: Automation scripts used to run the experiments.
- `data_processing/`: Scripts used for processing the raw experiment output, including overhead computation, classification, characterization.
- `statistics/`: Processed statistical results, effectiveness and characterization outputs, including analyses on both consent cookies and unnecessary cookies.

## Build from source

Note: Steps 1–2 overlap with Arcanum’s own setup; if you prefer, follow Arcanum’s instructions and skip repeating them here.

1. Install depot_tools to a specific directory (e.g., `$HOME`), and add it to your PATH:

```
# Install depot_tools
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH=$PATH:$HOME/depot_tools
```

2. Fetch Chromium source code and choose Chromium version 108.0.5359.71:

```
mkdir ${HOME}/chromium && cd ${HOME}/chromium/
fetch --nohooks chromium
cd src
gclient sync --with_branch_heads --with_tags
git fetch
git checkout tags/108.0.5359.71
gclient sync --with_branch_heads --with_tags
```

3. Build Arcanum based on its instruction.

4. Apply our patch to Arcanum, and recompile chromium.

## Legacy single-site runner

We provide `measure/single_site.sh` to run CookieTrace on a single website, tracking the source of target cookie.

You should modify `CHROME_BIN` at line 16, pointing to your compiled chromium.

Example Usage:

```
./single_site.sh example.com xx _gcl_au
```

The three parameters are:

1. domain to access (e.g., example.com)

2. script that writes the target cookie (not necessary, can be replaced by any placeholder)

3. the target cookie name




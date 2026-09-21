# Validation scope

The launcher test suite covers argument validation, output-path isolation, cookie identity checks, incomplete JSON handling, timeout and process cleanup, a local HTTP fixture, and mocked browser/Docker orchestration. Run it on Linux with:

```bash
python3 -m unittest discover -s ae/tests -v
```

Mocked process tests are not measurements of the instrumented browser. Use the README commands to check the real browser bundle and run the local demo on the evaluation host. Preserve status.json, browser.log, xvfb.log, preflight.json, and launcher.json when inspecting a run.

The distributed browser executable was checked against the author-provided server copy using SHA-256. The release archive includes a checksum for every runtime file. Analysis fixtures exercise code paths and output formats; they are not paper measurement data.

## Checks performed on 2026-09-21

- All 16 launcher tests passed under Linux, along with Bash syntax checks.
- The effectiveness checker completed on both repository CSVs.
- All seven analysis commands completed on synthetic source/path fixtures. Checks covered independent domains sharing an instance number, numeric forward-call loading, observation-count histogram scaling, paired depth comparisons, category aggregation, and plot creation.
- Modified JavaScript files and all AE Python files passed syntax checks.
- All 71 packaged runtime files matched their research-server SHA-256 checksums. Archive layout, executable permissions, and the English locale were checked. Uploaded asset size and SHA-256 matched the local archive.
- Documentation, source comments, and user-facing script messages were scanned for remaining Chinese text.

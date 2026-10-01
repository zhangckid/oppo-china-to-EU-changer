# oppo china to EU changer

English | [简体中文](README.zh-CN.md)

A cautious, device-specific workflow for converting the OPPO Find X9 Ultra (`PMA110`) from the recorded China build to the EU build `CPH2841_16.0.9.403(EX01)`. This project documents one historical conversion and provides an experimental command-line workflow. **The CLI can issue real device commands with `--execute`, but its end-to-end workflow has not been validated on a phone.** It does not make other OPPO phones supported.

The hardware record covers one 512 GB `PMA110` running `PMA110_16.0.9.403(CN01)`, project `25021`, kernel `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`, converted with the community `Recovery Flasher F9U CN2EU 16.0.9.403.zip` package to `CPH2841_16.0.9.403(EX01)`. Its first installer run was stopped at about 50% of the `super` write, after GPT resize and 100 firmware writes. An operator audited the partial state before rerunning the full package; the phone then completed setup. That human recovery is not performed by this CLI and is not validation of it.

## Start here

**This project is purely for technical exploration. Real operation requires flashing knowledge, Linux command-line experience, and AI-assisted review; the operator must understand and verify each step.** Maintained by Zhang Chen, with Codex assistance in implementation, log analysis, testing and documentation. AI cannot replace human judgment or guarantee a successful flash.

**Only one X9U has historical manual hardware validation; the new CLI has no end-to-end hardware validation.** The owner reports normal everyday use after conversion, except built-in OTA upgrades and NFC card addition rejected by OPPO. Domestic NFC apps themselves run normally. Read the [compatibility and real-device observations](docs/COMPATIBILITY.md) for the limits of this report.

| What do you need? | Entry point |
| --- | --- |
| Learn about or prepare a first conversion | [Start here](docs/START_HERE.md) → [Flowcharts](docs/FLOW.md) → [CLI walkthrough](docs/CLI.md) |
| Match a phone screen or current checkpoint | [Screenshots and checkpoints](docs/SCREENSHOTS.md); run `python3 change.py guide runs/convert` with your actual run directory |
| Upgrade an already converted EU phone | [oppo china to EU OTA updater](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater), after checking its baseline and profile requirements |
| Resolve an interruption, error or unexpected state | [Troubleshooting](docs/TROUBLESHOOTING.md); preserve the state for manual review |

## Built on prior work

This project depends on community work: **koaaN**'s [GBL Chainload App](https://github.com/koaaN/x9u-gbl-chainload-app), [OrangeFox lighthouse adaptation](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox), conversion installer and [arbextract](https://github.com/koaaN/arbextract); the **OrangeFox team's** Recovery; the **Daniel Springer ROM Archive** for [conversion downloads and checksums](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers); Google/AOSP tools; and [XDA community discussion](https://xdaforums.com/t/rom-pma110-pma120-convert-cn-to-global.4799566/).

This project adds input checks, journaling, human checkpoints, backup/readback policy and bilingual documentation. The upstream unlock method, Recovery and conversion package are credited to their respective creators. [Sources, prior work and acknowledgments](docs/SOURCES.md) records how each reference is used, the installer attribution evidence, and authorship limits; see also [third-party notices](THIRD_PARTY_NOTICES.md).

## Scope and safety

Initial conversion changes the partition table and erases user data. It includes bootloader unlock confirmation on the phone and a manual Format Data in OrangeFox. Keep a separate backup of personal data. The documented flow deliberately retains GBL, EFISP, and OrangeFox, leaves the bootloader unlocked, and does not promise support from OPPO.

The CLI divides preparation, status inspection, preview, and explicitly acknowledged execution. It starts only from a fresh CN Android install; it has no option to adopt an already converted phone. Execute mode requires an explicit Platform Tools directory and binds acknowledgments to the device serial and current stage:

```sh
python3 change.py prepare --rom PATH --gbl-apk PATH \
  --recovery-img PATH --recovery-zip PATH --out runs/convert
python3 change.py doctor --platform-tools PATH
python3 change.py status runs/convert
python3 change.py guide runs/convert
python3 change.py run runs/convert                 # preview
python3 change.py run runs/convert --platform-tools PATH --execute \
  --serial ANDROID_SERIAL --ack-erase ANDROID_SERIAL
python3 change.py resume runs/convert --platform-tools PATH --execute \
  --serial CURRENT_SERIAL --ack-stage CURRENT_STATE
```

The interface and behavior are experimental and may change. `--execute` can perform real operations; a preview and mock-backed tests are not hardware validation. The program resumes only from expected human-wait stages after checking state; an interruption during an active operation moves the run to `review_required`. There is no reset or force option. The tool does not automatically retry a write, format data, kill services, or apply an `adbd` workaround. Human actions remain part of the conversion.

## Documentation

| Page | Contents |
| --- | --- |
| [Getting started](docs/START_HERE.md) | Route selection, prerequisites, glossary and AI-assisted review |
| [Flowcharts](docs/FLOW.md) | Host/phone handoffs, partition changes and stop handling |
| [Screenshots](docs/SCREENSHOTS.md) | Real capture, terminal guide examples and missing-photo notes |
| [Compatibility](docs/COMPATIBILITY.md) | One X9U’s reported results, OTA and NFC limits |
| [Conversion workflow](docs/CONVERSION.md) | Exact historical case, tools, manual steps, and stop conditions |
| [CLI walkthrough](docs/CLI.md) | Complete command sequence and human gates for every stage |
| [Design and limits](docs/DESIGN.md) | Workflow boundaries, expected stages, and trust limits |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Exit codes, stage handling, and exception response |
| [Sources and provenance](docs/SOURCES.md) | Maintainer, publisher, XDA, and format-reference links |
| [Validation record](docs/VALIDATION.md) | What was observed on hardware and what remains unvalidated |
| [Releasing](docs/RELEASING.md) | Strict source export and share-safe release contents |

Each page links to its Chinese translation. For the audited later `CPH2841_16.0.10.500(EX01)` OTA process, see [oppo china to EU OTA updater](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater).

## External components

This project does not include firmware, GBL APKs, OrangeFox images or ZIPs, Android Platform Tools, or device backups. Obtain each item from its maintainer or publisher and check the published digest where available. Third-party notices and project terms are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [LICENSE](LICENSE).

## Disclaimer

This is an independent community project, not an OPPO, GBL, OrangeFox, or Google product. Device conversion can make a phone unusable and permanently erase data. Follow the exact upstream instructions for the exact device and build; stop when any prompt, image, layout, or verification differs from the record.

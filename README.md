# oppo china to EU changer

English | [简体中文](README.zh-CN.md)

A cautious, device-specific workflow for converting the OPPO Find X9 Ultra (`PMA110`) from the recorded China build to the EU build `CPH2841_16.0.9.403(EX01)`. This project documents one historical conversion and provides an experimental command-line workflow. **The CLI can issue real device commands with `--execute`, but its end-to-end workflow has not been validated on a phone.** It does not make other OPPO phones supported.

The hardware record covers one 512 GB `PMA110` running `PMA110_16.0.9.403(CN01)`, project `25021`, kernel `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`, converted with the community `Recovery Flasher F9U CN2EU 16.0.9.403.zip` package to `CPH2841_16.0.9.403(EX01)`. Its first installer run was stopped at about 50% of the `super` write, after GPT resize and 100 firmware writes. An operator audited the partial state before rerunning the full package; the phone then completed setup. That human recovery is not performed by this CLI and is not validation of it.

## Scope and safety

Initial conversion changes the partition table and erases user data. It includes bootloader unlock confirmation on the phone and a manual Format Data in OrangeFox. Keep a separate backup of personal data. The documented flow deliberately retains GBL, EFISP, and OrangeFox, leaves the bootloader unlocked, and does not promise support from OPPO.

The CLI divides preparation, status inspection, preview, and explicitly acknowledged execution. It starts only from a fresh CN Android install; it has no option to adopt an already converted phone. Execute mode requires an explicit Platform Tools directory and binds acknowledgments to the device serial and current stage:

```sh
python3 change.py prepare --rom PATH --gbl-apk PATH \
  --recovery-img PATH --recovery-zip PATH --out runs/convert
python3 change.py doctor --platform-tools PATH
python3 change.py status runs/convert
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

# Sources, prior work and acknowledgments

English | [简体中文](SOURCES.zh-CN.md) | [Project home](../README.md)

The project combines a private historical device record, exact locally audited artifacts, and public instructions from community maintainers. It is independent work; none of the community pages below is an OPPO conversion service or a guarantee that a file remains suitable for another build.

## Who contributed what

| Author, maintainer or community | Prior work and how this project uses it |
| --- | --- |
| **koaaN** | Author of the [GBL Chainload App](https://github.com/koaaN/x9u-gbl-chainload-app) and maintainer of the [lighthouse OrangeFox device adaptation](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox). The pinned CN2EU installer also credits `by koaaN`; this project invokes that installer rather than inventing its GPT/firmware conversion procedure. |
| **Jonas Salo / koaaN, arbextract** | Source of the Qualcomm OEM metadata locator adapted into `changer/policy.py`. The copyright name comes from the upstream MIT license; see [third-party notices](../THIRD_PARTY_NOTICES.md) for the full license and pinned revision. |
| **OrangeFox Recovery team** | The [OrangeFox Recovery](https://orangefox.download/) project. This workflow uses koaaN's device-specific unofficial build, without claiming official OrangeFox support for X9U. |
| **Daniel Springer ROM Archive** | Source of [conversion-package hosting, distribution and checksums](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers). The distributor and installer author are credited separately; hosting does not establish authorship of all firmware contents. |
| **Google / Android Open Source Project** | ADB/fastboot host tools and sparse-format reference. Their binaries are not bundled here; this project's sparse parser is its own implementation. |
| **XDA thread author and reply contributors** | Conversion discussion, reports and context. The page currently returns 403 to this review, so individual authors and contributions could not be verified and are not guessed. Consult the original thread; this project does not claim to have originated those community findings. |
| **Zhang Chen** | Project maintainer, hardware operator and source of the usage observations; organized local experiments and defined the checks, backup/state workflow and publication scope. |
| **OpenAI Codex (AI assistance)** | Assisted log analysis, implementation, exception checks, mock-backed tests and bilingual documentation. AI assistance is not hardware validation, upstream endorsement or safety certification, and does not change upstream ownership. |

### Evidence for the conversion installer's attribution

The locally audited `Recovery Flasher F9U CN2EU 16.0.9.403.zip` has SHA-256 `74c9754740c2587b20cd1b59a665436a62887ff078f6d7b4e79feb07973bf626`. Its `META-INF/com/google/android/update-binary`, line 506, displays the author marker `by koaaN`. This is attribution evidence for **that exact installer script**, not proof of authorship of all included OPPO firmware, dependencies or GBL components. This repository does not copy that installer or firmware; its distribution source is listed below.

This project's contribution is the surrounding workflow and checks: pinned-input auditing, durable stage records, explicit human handoffs, selected-partition backups, readback verification, read-only bilingual guidance and documentation. Bootloader access, Recovery and the conversion installer depend on the prior work credited above.

## Referenced documents and their uses

| Source | What it supports | Scope and trust limits |
| --- | --- | --- |
| [XDA: PMA110/PMA120 CN-to-global ROM thread](https://xdaforums.com/t/rom-pma110-pma120-convert-cn-to-global.4799566/) | Community discussion of the Find X9 Ultra conversion | XDA is a community forum. Its first post and later replies can change; use the thread for context and current discussion, not as a checksum authority. The direct page returned HTTP 403 during this documentation review, so its current contents could not be independently read here. |
| [GBL Chainload App repository](https://github.com/koaaN/x9u-gbl-chainload-app) and [v0.2.1 release](https://github.com/koaaN/x9u-gbl-chainload-app/releases/tag/v0.2.1) | GBL app, supported project/kernel information, temporary-root flow, GBL installation and unlock instructions | Maintainer project/release source. The app is not the ROM converter and does not itself unlock the bootloader. Review the current release instructions before use. |
| [OrangeFox lighthouse device repository](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox) and [v1.1 release](https://github.com/koaaN/android_device_oppo_lighthouse-orangefox/releases/tag/v1.1) | Device-specific Recovery IMG/ZIP and changes | Device maintainer source. This project pins the exact v1.1 artifacts for its recorded case; a different build needs a new review. |
| [CN2EU Convert Flashers directory](https://roms.danielspringer.at/index.php?dir=Oppo+Find+X9+Ultra%2FConvert+Flashers) and [publisher checksum page](https://roms.danielspringer.at/index.php?view=checksums) | Conversion package download and publisher checksum | Third-party archive and publisher record, not an official OPPO package. The CLI pins the exact `Recovery Flasher F9U CN2EU 16.0.9.403.zip` file; never substitute EU2CN or another build. |
| [Android Platform Tools release page](https://developer.android.com/tools/releases/platform-tools) | Official ADB and fastboot downloads | Google's host tools; the CLI checks for the reviewed 37.0.1 version. |
| [koaaN/arbextract](https://github.com/koaaN/arbextract) | Qualcomm OEM metadata location in `changer/policy.py` | MIT-licensed upstream locator adapted with bounded ELF64 parsing and exact reviewed metadata checks. The full license and revision are recorded in [Third-party notices](../THIRD_PARTY_NOTICES.md). |
| [AOSP libsparse source](https://android.googlesource.com/platform/system/core/+/refs/heads/main/libsparse/) | Android sparse-image format reference | Format reference only; this repository does not redistribute AOSP source. |
| [Mermaid documentation](https://mermaid.js.org/config/usage.html) | Diagram-rendering reference; the workflow content is authored by this project | Mermaid blocks are the diagram source; supplied SVGs were rendered with Mermaid 12. Diagrams are not hardware evidence; the Mermaid runtime is not bundled. |

The recorded hardware case used `PMA110`, project `25021`, kernel `6.12.58-android16-6-g7704a1ae279b-ab15213644-4k`, and the exact artifacts listed in [`changer/pins.json`](../changer/pins.json). The public `hardware.json` contains partition capacities, not a private device identity. Pins document artifact identity; they do not certify safety or compatibility beyond the recorded case.

Links and the XDA search result were reviewed on 2026-10-01. Because the XDA page itself blocked automated retrieval, check its current top post and maintainer release pages directly before acting. The project does not copy XDA instructions wholesale and does not treat forum reports as hardware validation of this CLI.

## Related OTA project

[oppo china to EU OTA updater](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater) ([Chinese documentation](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater/blob/main/README.zh-CN.md)) is the separate upgrade project maintained by Zhang Chen with Codex assistance. It records the same phone's manual EU403-to-EU500 upgrade and has its own current EU500 baseline and local-profile requirements. It is not the initial CN2EU installer and does not establish hardware validation of this converter CLI.

Citation does not relicense a source: external documents, images, firmware and tools retain their creators' terms. Beyond the declared arbextract adaptation, these public documents use links and this project's explanations; an unverified license is not treated as permission to redistribute binaries or copy complete tutorials.

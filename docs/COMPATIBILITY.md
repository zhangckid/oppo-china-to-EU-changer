# X9 Ultra hardware results, OTA and NFC

English | [简体中文](COMPATIBILITY.zh-CN.md) | [Project home](../README.md)

**Only the OPPO Find X9 Ultra (X9U) has been tested on real hardware in this project: one PMA110 with 512 GB storage.** The owner's reported experience after conversion to the international/EU build is that everyday use works normally, with two known exceptions: built-in OTA upgrading and NFC card addition. This is an experience report for that phone, not a test result for every function or every regional build.

## What was actually tested

| Item | Recorded scope |
| --- | --- |
| Physical phone | Find X9 Ultra / X9U, China model `PMA110`, 512 GB, physical project `25021` |
| Initial conversion | `PMA110_16.0.9.403(CN01)` → `CPH2841_16.0.9.403(EX01)` using the reviewed community CN2EU package |
| Meaning of “international” here | The recorded EU/EEA firmware, identified as `CPH2841` / `CPH2841EEA`; other international regions were not tested |
| Later upgrade | A separate manual EU403 → `CPH2841_16.0.10.500(EX01)` upgrade was completed; its details belong to the updater project |
| New converter CLI | Offline package inspection and simulated device tests; no completed real-device run of the new CLI |
| Other phones/configurations | No hardware validation for other OPPO models, capacities, project IDs, kernels or source builds |

The owner's latest OTA/NFC feedback describes the converted phone's use. It does not establish the same behavior separately for every firmware revision, app release or card type. Hardware observations and automated-tool coverage are tracked separately in [Validation](VALIDATION.md).

## Reported behavior after conversion

| Area | Result on the reference X9U | What can be concluded |
| --- | --- | --- |
| Boot, initial setup and normal use | EU Android booted, setup completed; the owner reports normal everyday operation apart from the exceptions below | A successful usable conversion was observed; this is not an exhaustive hardware/app certification |
| OTA notification and download | New updates can be offered and downloaded | Receiving an OTA does not demonstrate that the built-in updater will install it |
| Built-in OTA upgrade | Upgrade fails, including the observed `Download failed, please try again` message after download | This converted configuration needs separate upgrade handling; see the updater repository |
| Domestic Chinese NFC apps | The owner reports that the apps themselves run normally | App launch/use and card provisioning have different observed outcomes |
| NFC card addition | OPPO rejects the request when adding a card | Card provisioning is a known limitation on this phone; no working fix is claimed here |

## OTA: use the separate updater project

Repository: [oppo china to EU OTA updater](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater). Also available: [Chinese README](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater/blob/main/README.zh-CN.md), [device profiles](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater/blob/main/docs/PROFILE.md), and [validation record](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater/blob/main/docs/VALIDATION.md).

This converter handles initial CN403 → EU403 conversion and includes data erasure. The updater documents the later full-OTA workflow for an already converted device. The successful manual 403 → 500 upgrade is its historical hardware evidence; its current automated policy starts from a verified EU500 baseline and requires a reviewed local device profile. The public example profile is not an executable profile.

Therefore, do not rerun this converter for a new OTA, and do not assume a newly converted EU403 phone can immediately run the updater's current automation. Read its baseline, package and profile requirements first. That workflow does not make the stock updater accept the converted phone, and its own automated hardware-validation limits still apply. Neither project uses bootloader relocking as an OTA workaround.

## NFC: apps run, but adding a card is rejected

The reported sequence is:

1. A domestic Chinese NFC app can run on the converted phone.
2. The user attempts to add a card.
3. OPPO rejects card addition.

The report does **not** establish that NFC hardware is defective or that every NFC operation fails. It also does not prove that every reader, tag, payment, transit or access-card scenario works. Individual apps, card types and service combinations have not been comprehensively tested.

The exact reason for OPPO's rejection has not been established in this project's published evidence. In particular, the report does not isolate whether the rejection is associated with firmware region, account/service eligibility, device state, or another provisioning check. Treat those as questions for diagnosis, not confirmed causes. Do not describe installing a domestic NFC app, changing region properties, relocking, or running the OTA updater as a verified fix.

When documenting this issue, record the exact system build, app name/version, card category, step that fails, and full error text/code. Hide account identifiers, card numbers and provisioning tokens before sharing. Ask the relevant OPPO/app support channel about the specific rejection; preserve the working system rather than repeating the conversion as a diagnostic step. XDA and maintainer links are collected in [Sources](SOURCES.md).

## What `complete` means in the tool

The CLI's final stage checks the EU identity, expected project and slot, unlocked state, Android boot completion, and setup completion. Earlier stages check installation evidence, storage geometry and readback. It does not run a full phone acceptance suite, install a future OTA, or attempt to add NFC cards. A run reaching `complete` would therefore not certify either of the known service limitations as resolved.

For another real-device report, distinguish **manual conversion** from **a complete run of a specific CLI commit**. State model, capacity, starting and resulting build, and which functions were actually exercised. Do not infer support for an untested model from this repository's general project name.

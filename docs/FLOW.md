# Conversion flowcharts and checkpoints

English | [简体中文](FLOW.zh-CN.md) | [Project home](../README.md)

For offline reading or a viewer without Mermaid support, open the rendered SVGs: [1. Prepare Recovery](images/flow-1-en.svg) · [2. Convert and boot](images/flow-2-en.svg) · [3. Partition changes](images/flow-3-en.svg) · [4. Wait and stop](images/flow-4-en.svg). These are diagrams, not phone screenshots.

These diagrams describe the implemented workflow for **Find X9 Ultra (X9U), PMA110, 512 GB, CN403 → CPH2841 EU403**. Only one X9U has historical manual conversion evidence. The new CLI's complete sequence has not been run on a phone. Read the [command walkthrough](CLI.md) alongside these diagrams; a diagram is not an instruction to skip a checkpoint.

“Host” means an action performed or checked by the CLI after explicit execution. “Phone” means an action the operator must perform. The CN2EU package's own installer performs the GPT and firmware writes; this project invokes and checks it.

## 1. From stock China Android to a prepared Recovery

```mermaid
flowchart TD
    A["Stock PMA110, 512 GB, CN403<br/>Back up personal data separately"] --> B["Host: doctor and prepare<br/>Verify four pinned files; preview the run"]
    B --> C{"Device, kernel, inputs<br/>and geometry match?"}
    C -->|No| STOP["Stop and preserve the evidence<br/>Review the recorded state before further action"]
    C -->|Yes| D["Host: install the GBL APK"]
    D --> E["Phone: temporary root and FLASH<br/>Require FLASH_VERIFY_OK"]
    E --> F["Phone: stock Recovery Format Data<br/>Personal data is erased"]
    F --> G["Phone: enter GBL<br/>Hold Volume Up after reboot vibration"]
    G --> H["Host: request bootloader unlock<br/>Phone: confirm the unlock prompt"]
    H --> I["Host: verify unlocked state and Recovery capacity<br/>Flash recovery_a; reboot to OrangeFox"]
    I --> J["Host: check CN layout and retained GBL<br/>Back up 107 partitions and six GPTs"]
    J --> K["Phone: enable ADB Sideload<br/>Host: send the OrangeFox ZIP"]
    K --> L["Fresh OrangeFox Recovery<br/>Verify both Recovery slots and the backups"]
    L --> M["Ready for the CN2EU package<br/>Automatic reboot off; pre-install log saved"]
```

The firmware backup in this sequence happens **after** GBL installation, the stock Format Data, and the first Recovery image write. It excludes `userdata` and cannot recover personal data erased earlier. The historical manual case backed up 121 selected partitions; the new CLI implements its own 107-partition scope. Neither should be described as a pristine factory backup.

Android/Recovery ADB uses the original ADB serial. GBL may expose a different fastboot serial, which is explicitly bound at `waiting_gbl`. The CLI checks active slot A and a 104,857,600-byte `recovery_a` before flashing; it checks `recovery_b` capacity before the OrangeFox ZIP stage. Unexpected execution checks lead to a stop, including checks not drawn as separate decision nodes above.

## 2. From CN2EU sideload to EU Android

```mermaid
flowchart TD
    A["Prepared OrangeFox session<br/>GBL preserved; automatic reboot disabled"] --> B["Phone: enable ADB Sideload<br/>Host: send the exact CN2EU ZIP"]
    B --> C["Phone: Volume Up to continue<br/>Then Volume Down for ABL = NO"]
    C --> D["Upstream installer: resize GPT<br/>Write 100 firmware targets and sparse super"]
    D --> E{"Fresh Installation complete<br/>ABL kept and no installer error?"}
    E -->|No or unknown| STOP["STOP: preserve Recovery and all logs<br/>Do not format, boot System or replay a write"]
    E -->|Yes| F["Host: inspect on-disk GPT and protected boot chain<br/>Reboot directly to Recovery"]
    F --> G{"New Recovery boot ID, EU sizes,<br/>firmware and defined super hashes match?"}
    G -->|No| STOP
    G -->|Yes| H["Phone: Data - Format Data - yes<br/>Stay in this Recovery session"]
    H --> I{"Fresh successful format evidence<br/>for userdata and metadata?"}
    I -->|No| STOP
    I -->|Yes| J["Host: reboot Recovery again<br/>Check EU layout and data mounted as F2FS"]
    J --> K["Host: request first EU Android boot<br/>Phone: finish setup and authorize ADB"]
    K --> L{"Expected EU identity,<br/>boot and setup complete?"}
    L -->|No| STOP
    L -->|Yes| M["Record complete<br/>Review the OTA and NFC compatibility notes"]
```

The host's transfer progress, including a percentage that appears to stop before 100%, is not the installation result. The CLI requires new Recovery-log evidence, then verifies 100 firmware target prefixes and 290 defined RAW/FILL regions in `super`. The 19 DONT_CARE regions have no expected byte content and are excluded from device readback comparison.

The first Recovery reboot makes the kernel reread the changed partition table. The reboot after Format Data checks the new `/data` filesystem in a fresh session. These are separate checkpoints. `complete` means the programmed conversion checks passed; it does not test all phone functions or certify OTA/NFC provisioning. See [real-device results](COMPATIBILITY.md).

## 3. What changes on storage

Logical sector size is 4,096 bytes. The following boundaries are inclusive and apply only to the reviewed 512 GB configuration.

```mermaid
flowchart LR
    subgraph CN["Original CN layout on sda"]
        A["Partitions 1-13<br/>Reviewed fixed boundaries"]
        B["super: sda14<br/>385772 - 5188331"]
        C["userdata<br/>sda15<br/>5188332 - 124070906"]
        A --> B --> C
    end
    subgraph EU["Target EU layout on sda"]
        D["Partitions 1-13<br/>Same reviewed boundaries"]
        E["super: sda14<br/>385772 - 5378795"]
        F["userdata<br/>sda15<br/>5378796 - 124070906"]
        D --> E --> F
    end
    B -.->|Expanded by installer| E
    C -.->|Start moves; format required| F
```

| Component | Reviewed behavior | Why it matters |
| --- | --- | --- |
| `super` | Grows from 19,671,285,760 to 20,451,426,304 bytes | The package streams the sparse image to a raw disk offset; the old in-memory partition size may remain until Recovery reboots. |
| `userdata` | Its start moves; its end remains 124,070,906 | Do not place the conversion ZIP in internal storage. The CLI transfers it from the host using sideload. A normal wipe does not replace the required Format Data. |
| GPT entries 1–13 on `sda` | Their boundaries remain fixed | This is a layout statement: some contents, such as metadata during Format Data, still change. |
| 50 selected firmware images | Written to both slots: 100 targets | Initial conversion affects both slots. The later OTA updater has its own different partition policy. |
| `abl_a`, `abl_b`, EFISP | Existing GBL components retained | Select **ABL = NO** in the conversion installer. The CLI checks the pinned GBL content. |
| `recovery_a`, `recovery_b` | Device-specific OrangeFox retained | The OrangeFox IMG/ZIP stages install it; the CN2EU ROM stage skips its own Recovery image. |
| `userdata` and `metadata` | Formatted by the final OrangeFox Format Data operation | The tool requires fresh successful format records for both, then a new Recovery session. |

## 4. A checkpoint is not an automatic retry

```mermaid
flowchart TD
    A["Read the existing journal and status"] --> B{"Expected waiting state?"}
    B -->|No: unfinished action or review_required| STOP["Manual review<br/>No reset, force, automatic retry or rollback"]
    B -->|Yes| C["Operator completes the requested phone action<br/>Resume with the exact stage and serial"]
    C --> D{"Required observations match?"}
    D -->|No| STOP
    D -->|Yes| E["Persist action intent before mutation"]
    E --> F["Execute the bounded command and check its result"]
    F --> G{"Result is verified?"}
    G -->|No, interrupted or uncertain| STOP
    G -->|Yes| H["Persist the next waiting state or complete"]
    H --> A
```

Exit `3` means a normal human checkpoint. Exit `2` means a check or command failed; inspect `status`, because a usage/setup error need not change the journal while an execution failure can make it `review_required`. Exit `130` means interruption. The tool does not infer from a timeout or disconnect that no bytes were written. See the [exception table](TROUBLESHOOTING.md).

## 5. After conversion

Use the [published OTA updater](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater) to study the separate, reviewed upgrade workflow when the built-in updater cannot upgrade this converted configuration. Its current documented baseline is EU `16.0.10.500` and it requires a verified local device profile; a phone just converted to EU403 is not automatically ready to run it. Follow that project's [Chinese documentation](https://github.com/zhangckid/oppo-china-to-EU-OTA-updater/blob/main/README.zh-CN.md) or English README.

The reported NFC problem is **card addition rejected by OPPO**. Domestic NFC apps themselves run normally on the reference phone. This converter and the OTA updater do not implement an NFC card-provisioning fix. Details and reporting boundaries are in [Compatibility](COMPATIBILITY.md).

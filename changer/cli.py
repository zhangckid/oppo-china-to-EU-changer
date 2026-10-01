"""Explicit execution, preview by default, no device calls while preparing."""
import argparse
import json
import subprocess
import sys
import traceback
import zipfile

from .artifacts import verify_artifacts
from .core import ReviewRequired, execution_lock
from .runner import Runner, create_run, status, tools_info


def parser():
    result = argparse.ArgumentParser(description="oppo china to EU changer — reviewed PMA110 512GB CN403 only")
    sub = result.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Offline pinned artifact verification; no phone access")
    for name in ("rom", "gbl-apk", "recovery-img", "recovery-zip", "out"):
        prepare.add_argument("--" + name, required=True)
    doctor = sub.add_parser("doctor", help="Check host Platform Tools only; no phone commands")
    doctor.add_argument("--platform-tools", required=True)
    view = sub.add_parser("status")
    view.add_argument("run_dir")
    for name in ("run", "resume"):
        command = sub.add_parser(name, help="Preview by default; --execute performs the current stage")
        command.add_argument("run_dir")
        command.add_argument("--execute", action="store_true")
        command.add_argument("--platform-tools")
        command.add_argument("--serial")
        command.add_argument("--ack-erase" if name == "run" else "--ack-stage")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "prepare":
            print("Verifying pinned files and streaming sparse super; this can take several minutes.", file=sys.stderr)
            manifest = verify_artifacts(args.rom, args.gbl_apk, args.recovery_img, args.recovery_zip)
            create_run(args.out, manifest)
            result = status(args.out)
        elif args.command == "doctor":
            result = tools_info(args.platform_tools)
        elif args.command == "status" or not args.execute:
            result = status(args.run_dir)
        else:
            if not args.platform_tools or not args.serial:
                parser().error("--execute requires --platform-tools and --serial")
            with execution_lock():
                result = Runner(args.run_dir).execute(command=args.command, serial=args.serial,
                    platform_tools=args.platform_tools, ack_erase=getattr(args, "ack_erase", None),
                    ack_stage=getattr(args, "ack_stage", None))
        print(json.dumps(result, indent=2))
        return 3 if args.command in {"run", "resume"} and args.execute and result["status"] == "waiting" else 0
    except (ReviewRequired, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted. Preserve the journal and device state; do not replay a write.", file=sys.stderr)
        return 130
    except Exception as error:
        # Unknown programming failures also stop. Include the traceback for a
        # local audit, never continue to another stage after an unexpected error.
        print(f"STOP: unexpected {type(error).__name__}: {error}. Preserve all evidence for manual review.", file=sys.stderr)
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

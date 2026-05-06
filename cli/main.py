from __future__ import annotations

import argparse
import json
import sys

from . import commands


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[2] == "run":
        out = commands.run(sys.argv[1])
        print(json.dumps(out, indent=2, sort_keys=True))
        return

    parser = argparse.ArgumentParser(prog="ct")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("task")

    replay_cmd = sub.add_parser("replay")
    replay_cmd.add_argument("trace_id")

    debug_cmd = sub.add_parser("debug")
    debug_cmd.add_argument("task")

    attach_cmd = sub.add_parser("attach-model")
    attach_cmd.add_argument("provider")

    trace_cmd = sub.add_parser("trace")
    trace_sub = trace_cmd.add_subparsers(dest="trace_cmd", required=True)
    trace_sub.add_parser("show")

    args = parser.parse_args()
    if args.cmd == "run":
        out = commands.run(args.task)
    elif args.cmd == "replay":
        out = commands.replay(args.trace_id)
    elif args.cmd == "debug":
        out = commands.run(args.task, debug=True)
    elif args.cmd == "attach-model":
        out = commands.attach_model(args.provider)
    elif args.cmd == "trace" and args.trace_cmd == "show":
        out = commands.trace_show()
    else:
        raise SystemExit(2)

    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

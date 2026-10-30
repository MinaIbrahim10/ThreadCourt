import argparse
import json
from pathlib import Path
from .agents import Ollama, investigate
from .engine import SCENARIOS


def main():
    parser = argparse.ArgumentParser(description='ThreadCourt concurrency model laboratory')
    parser.add_argument('scenario', choices=SCENARIOS, nargs='?', default='lost-update')
    parser.add_argument('--llm', action='store_true', help='Enable specialist agents using local Ollama/Gemma 4')
    parser.add_argument('--model', default=None)
    parser.add_argument('--max-states', type=int, default=10000)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--serve', action='store_true', help='Open the loopback-only evidence dashboard')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    report = investigate(args.scenario, Ollama(args.model) if args.llm else None, args.max_states)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n', encoding='utf-8')
    if args.serve:
        from .dashboard import serve
        serve(report, args.port)
    else:
        print(rendered)


if __name__ == '__main__':
    main()

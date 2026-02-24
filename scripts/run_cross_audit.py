#!/usr/bin/env python3
"""
Runner para Cross-Audit desde GitHub Actions o CLI.
Conecta al servidor ODI vía API HTTP.
"""

import argparse
import json
import sys
import httpx


def main():
    parser = argparse.ArgumentParser(description='ODI Cross-Audit Runner')
    parser.add_argument('--empresa', default='', help='Empresa específica')
    parser.add_argument('--sample-size', type=int, default=10)
    parser.add_argument('--trigger', default='manual')
    parser.add_argument('--git-commit', default=None)
    parser.add_argument('--git-branch', default=None)
    parser.add_argument('--pr-number', type=int, default=None)
    parser.add_argument('--output', default='audit-report.json')
    parser.add_argument('--server', default='http://localhost:8808')
    args = parser.parse_args()

    # Si se especifica empresa, auditar solo esa
    if args.empresa:
        endpoint = f"{args.server}/audit/empresa"
        payload = {
            'empresa': args.empresa,
            'auditor': 'github_action',
            'trigger_type': args.trigger,
            'sample_size': args.sample_size,
            'git_commit': args.git_commit,
            'git_branch': args.git_branch,
            'pr_number': args.pr_number
        }
    else:
        endpoint = f"{args.server}/audit/all"
        payload = {
            'auditor': 'github_action',
            'trigger_type': args.trigger,
            'sample_size': args.sample_size
        }

    try:
        resp = httpx.post(endpoint, json=payload, timeout=120.0)
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        result = {'status': 'failed', 'error': str(e)}

    # Guardar reporte
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Reporte guardado en {args.output}")
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Health Score: {result.get('health_score', 'N/A')}%")

    # Exit code para CI/CD
    if result.get('status') in ('changes_requested', 'failed'):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()

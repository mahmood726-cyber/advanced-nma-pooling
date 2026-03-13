"""Console entrypoint for installable nma-pool workflows."""

from __future__ import annotations

import argparse
from importlib import import_module


COMMANDS: dict[str, tuple[str, str]] = {
    "analysis": ("nma_pool.pipelines.analysis", "Run an AD NMA analysis from config."),
    "benchmark": ("nma_pool.pipelines.benchmark", "Run the benchmark suite across NMA adapters."),
    "bias-adjusted": (
        "nma_pool.pipelines.bias_adjusted",
        "Run the design-stratified bias-adjusted NMA pipeline.",
    ),
    "bias-adjusted-bayesian": (
        "nma_pool.pipelines.bias_adjusted_bayesian",
        "Run the Bayesian bias-adjusted NMA pipeline.",
    ),
    "bias-sensitivity": (
        "nma_pool.pipelines.bias_sensitivity",
        "Run prior sensitivity scenarios for Bayesian bias adjustment.",
    ),
    "mlnmr": ("nma_pool.pipelines.mlnmr", "Run the ML-NMR AD+IPD pipeline."),
    "mlnmr-bayesian": (
        "nma_pool.pipelines.mlnmr_bayesian",
        "Run the Bayesian ML-NMR AD+IPD pipeline.",
    ),
    "publication-suite": (
        "nma_pool.pipelines.publication_suite",
        "Run the publication-grade simulation suite.",
    ),
    "survival-nph": (
        "nma_pool.pipelines.survival_nph",
        "Run the survival non-proportional hazards pipeline.",
    ),
    "paper1-bundle": (
        "nma_pool.pipelines.paper1_bundle",
        "Build the reproducible Paper-1 artifact bundle.",
    ),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nma-pool",
        description="Installable CLI for nma-pool analysis and validation workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command")
    for command_name, (_, help_text) in COMMANDS.items():
        subparsers.add_parser(command_name, help=help_text, add_help=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    namespace, remainder = parser.parse_known_args(argv)
    command_name = namespace.command
    if command_name is None:
        parser.print_help()
        return 0

    module_name, _ = COMMANDS[command_name]
    module = import_module(module_name)
    result = module.main(remainder)
    if isinstance(result, int):
        return result
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Research experimentation framework — experiment tracking + shadow execution."""

from aquila.experiments.shadow import ShadowExecutor
from aquila.experiments.tracker import Experiment, ExperimentTracker

__all__ = ["ShadowExecutor", "Experiment", "ExperimentTracker"]

"""ADK AgentEvaluator wrapper over the BACEN golden dataset."""

from pathlib import Path

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


@pytest.mark.eval
@pytest.mark.asyncio
async def test_bacen_golden_evalset():
    data_dir = Path(__file__).resolve().parent / "data"
    await AgentEvaluator.evaluate(
        agent_module="bacen_advisor",
        eval_dataset_file_path_or_dir=str(data_dir / "bacen_golden.evalset.json"),
        config_file_path=str(data_dir / "test_config.json"),
        num_runs=1,
    )

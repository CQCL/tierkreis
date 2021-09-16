from collections import Counter
from typing import Dict, Tuple
from pytket.backends.backendresult import BackendResult
from pytket.utils.outcomearray import OutcomeArray

Distribution = Dict[str, float]
SampledDistribution = Tuple[Distribution, int]  # distribution, n_samples


def backres_to_sampleddist(backres: BackendResult) -> SampledDistribution:
    # counts = backres.get_counts()
    assert backres.contains_measured_results
    if backres._counts is not None:
        total_shots = int(sum(backres._counts.values()))
    else:
        total_shots = len(backres._shots)
    return (
        {
            "".join(map(str, key)): val
            for key, val in backres.get_distribution().items()
        },
        total_shots,
    )


def bitstring_to_tuple(bitstr: str) -> Tuple[int, ...]:
    return tuple(map(int, bitstr))


def sampleddist_to_backres(dist: SampledDistribution) -> BackendResult:
    prob_dist, samples = dist
    counts = {
        OutcomeArray.from_readouts([bitstring_to_tuple(key)]): int(val * samples)
        for key, val in prob_dist.items()
    }

    return BackendResult(counts=Counter(counts))

import logging
import numpy as np

from ..problem import Problem
from ..result import Result
from .sampler import Sampler
from .pymc3 import Pymc3Sampler

logger = logging.getLogger(__name__)


def sample(
        problem: Problem,
        n_samples: int,
        sampler: Sampler = None,
        x0: np.ndarray = None,
        result: Result = None
) -> Result:
    """
    This is the main function to call to do parameter sampling.

    Parameters
    ----------
    problem:
        The problem to be solved. If None is provided, a
        :class:`pypesto.Pymc3Sampler` is used.
    n_samples:
        Number of samples to generate.
    sampler:
        The sampler to perform the actual sampling.
    x0:
        Initial parameter for the Markov chain. If None, the best parameter
        found in optimization is used. Note that some samplers require an
        initial parameter, some may ignore it.
    result:
        A result to write to. If None provided, one is created from the
        problem.

    Returns
    -------
    result:
        A result with filled in sample_options part.
    """
    # prepare result object
    if result is None:
        result = Result(problem)

    # try to find initial parameters
    if x0 is None:
        result.optimize_result.sort()
        xs = result.optimize_result.get_for_key('x')
        if len(xs) > 0:
            x0 = xs[0]

    # set sampler
    if sampler is None:
        sampler = Pymc3Sampler()

    # initialize sampler to problem
    sampler.initialize(problem=problem, x0=x0)

    # perform the sampling
    sampler.sample(n_samples=n_samples)

    # extract results
    sampler_result = sampler.get_samples()

    # record results
    result.sample_result = sampler_result

    return result

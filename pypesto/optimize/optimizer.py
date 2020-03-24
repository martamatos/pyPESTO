import numpy as np
import scipy.optimize
import re
import abc
import time
import logging
from typing import Dict

from ..objective import res_to_chi2
from ..C import MAXIMIZATION_OBJECTIVE_TYPES
from ..problem import Problem
from .result import OptimizerResult

try:
    import pyswarm
except ImportError:
    pyswarm = None

try:
    import dlib
except ImportError:
    dlib = None


logger = logging.getLogger(__name__)


def objective_decorator(optimize):
    """
    Default decorator for the optimize() method to initialize and extract
    information stored in the objective.
    """

    def wrapped_optimize(self, problem, x0, index):
        problem.objective.reset_history(index=index)
        if hasattr(problem.objective, 'reset_steadystate_guesses'):
            problem.objective.reset_steadystate_guesses()
        result = optimize(self, problem, x0, index)
        problem.objective.finalize_history()
        result = fill_result_from_objective_history(
            result, problem.objective.history)
        return result
    return wrapped_optimize


def time_decorator(optimize):
    """
    Default decorator for the optimize() method to take time.
    Currently, the method time.time() is used, which measures
    the wall-clock time.
    """

    def wrapped_optimize(self, problem, x0, index):
        start_time = time.time()
        result = optimize(self, problem, x0, index)
        used_time = time.time() - start_time
        result.time = used_time
        return result
    return wrapped_optimize


def fix_decorator(optimize):
    """
    Default decorator for the optimize() method to include also fixed
    parameters in the result arrays (nans will be inserted in the
    derivatives).
    """

    def wrapped_optimize(self, problem, x0, index):
        result = optimize(self, problem, x0, index)
        result.x = problem.get_full_vector(result.x, problem.x_fixed_vals)
        result.grad = problem.get_full_vector(result.grad)
        result.hess = problem.get_full_matrix(result.hess)
        result.x0 = problem.get_full_vector(result.x0, problem.x_fixed_vals)

        logger.info(f"Final fval={result.fval:.4f}, "
                    f"time={result.time:.4f}s, "
                    f"n_fval={result.n_fval}.")

        return result
    return wrapped_optimize


def fill_result_from_objective_history(result, history):
    """
    Overwrite function values in the result object with the values recorded in
    the history.
    """

    # counters
    result.n_fval = history.n_fval
    result.n_grad = history.n_grad
    result.n_hess = history.n_hess
    result.n_res = history.n_res
    result.n_sres = history.n_sres

    # initial values
    result.x0 = history.x0
    result.fval0 = history.fval0

    # best found values
    result.x = history.x_min
    result.fval = history.fval_min

    # trace
    result.trace = history.trace

    return result


def recover_result(objective, startpoint, err):
    """
    Upon an error, recover from the objective history whatever available,
    and indicate in exitflag and message that an error occurred.
    """
    result = OptimizerResult(
        x0=startpoint,
        exitflag=-1,
        message=str(err),
    )
    fill_result_from_objective_history(result, objective.history)

    return result


class Optimizer(abc.ABC):
    """
    This is the optimizer base class, not functional on its own.

    An optimizer takes a problem, and possibly a start point, and then
    performs an optimization. It returns an OptimizerResult.
    """

    def __init__(self):
        """
        Default constructor.
        """

    @abc.abstractmethod
    @fix_decorator
    @time_decorator
    @objective_decorator
    def optimize(
            self,
            problem: Problem,
            x0: np.ndarray,
            index: int
    ) -> OptimizerResult:
        """"
        Perform optimization.

        Parameters
        ----------
        problem:
            The problem to find optimal parameters for.
        x0:
            The starting parameters.
        index:
            Multistart index.
        """

    @abc.abstractmethod
    def is_least_squares(self):
        return False

    @staticmethod
    def get_default_options():
        """
        Create default options specific for the optimizer.
        """
        return None


class ScipyOptimizer(Optimizer):
    """
    Use the SciPy optimizers.
    """

    def __init__(self,
                 method: str = 'L-BFGS-B',
                 tol: float = 1e-9,
                 options: Dict = None):
        super().__init__()

        self.method = method

        self.tol = tol

        self.options = options
        if self.options is None:
            self.options = ScipyOptimizer.get_default_options()

    @fix_decorator
    @time_decorator
    @objective_decorator
    def optimize(
            self,
            problem: Problem,
            x0: np.ndarray,
            index: int
    ) -> OptimizerResult:
        lb = problem.lb
        ub = problem.ub
        objective = problem.objective

        if self.is_least_squares():
            # is a residual based least squares method

            if not objective.has_res:
                raise Exception(
                    "For least squares optimization, the objective "
                    "must be able to compute residuals.")

            ls_method = self.method[3:]
            bounds = (lb, ub)

            fun = objective.get_res
            jac = objective.get_sres if objective.has_sres else '2-point'
            # TODO: pass jac computing methods in options

            # optimize
            res = scipy.optimize.least_squares(
                fun=fun,
                x0=x0,
                method=ls_method,
                jac=jac,
                bounds=bounds,
                ftol=self.tol,
                tr_solver='exact',
                loss='linear',
                verbose=2 if 'disp' in
                self.options.keys() and self.options['disp']
                else 0,
            )

        else:
            # is an fval based optimization method

            if not objective.has_fun:
                raise Exception("For this optimizer, the objective must "
                                "be able to compute function values")

            bounds = scipy.optimize.Bounds(lb, ub)

            # fun_may_return_tuple = self.method.lower() in \
            #    ['cg', 'bfgs', 'newton-cg', 'l-bfgs-b', 'tnc', 'slsqp',
            #        'dogleg', 'trust-ncg']
            # TODO: is it more efficient to have tuple as output of fun?
            method_supports_grad = self.method.lower() in \
                ['cg', 'bfgs', 'newton-cg', 'l-bfgs-b', 'tnc', 'slsqp',
                 'dogleg', 'trust-ncg', 'trust-krylov', 'trust-exact',
                 'trust-constr']
            method_supports_hess = self.method.lower() in \
                ['newton-cg', 'dogleg', 'trust-ncg', 'trust-krylov',
                 'trust-exact', 'trust-constr']
            method_supports_hessp = self.method.lower() in \
                ['newton-cg', 'trust-ncg', 'trust-krylov', 'trust-constr']

            _fun = objective.get_fval
            _jac = objective.get_grad \
                if objective.has_grad and method_supports_grad \
                else None
            _hess = objective.get_hess \
                if objective.has_hess and method_supports_hess \
                else None
            _hessp = objective.get_hessp \
                if objective.has_hessp and method_supports_hessp \
                else None
            # minimize will ignore hessp otherwise
            if _hessp is not None:
                _hess = None

            sign = -1 \
                if objective.obj_type in MAXIMIZATION_OBJECTIVE_TYPES else 1

            fun = None if _fun is None else (lambda x: sign * _fun(x))
            jac = None if _jac is None else (lambda x: sign * _jac(x))
            hess = None if _hess is None else (lambda x: sign * _hess(x))
            hessp = None if _hessp is None else (lambda x: sign * _hessp(x))

            # optimize
            res = scipy.optimize.minimize(
                fun=fun,
                x0=x0,
                method=self.method,
                jac=jac,
                hess=hess,
                hessp=hessp,
                bounds=bounds,
                tol=self.tol,
                options=self.options,
            )

        # some fields are not filled by all optimizers, then fill in None
        grad = getattr(res, 'grad', None) if self.is_least_squares() \
            else getattr(res, 'jac', None)
        fval = res_to_chi2(res.fun) if self.is_least_squares() \
            else res.fun

        # fill in everything known, although some parts will be overwritten
        optimizer_result = OptimizerResult(
            x=res.x,
            fval=fval,
            grad=grad,
            hess=getattr(res, 'hess', None),
            n_fval=getattr(res, 'nfev', 0),
            n_grad=getattr(res, 'njev', 0),
            n_hess=getattr(res, 'nhev', 0),
            x0=x0,
            fval0=None,
            exitflag=res.status,
            message=res.message
        )

        return optimizer_result

    def is_least_squares(self):
        return re.match(r'(?i)^(ls_)', self.method)

    @staticmethod
    def get_default_options():
        options = {'maxiter': 1000, 'disp': False}
        return options


class DlibOptimizer(Optimizer):
    """
    Use the Dlib toolbox for optimization.
    """

    def __init__(self,
                 method: str,
                 options: Dict = None):
        super().__init__()

        self.method = method

        self.options = options
        if self.options is None:
            self.options = DlibOptimizer.get_default_options()

    @fix_decorator
    @time_decorator
    @objective_decorator
    def optimize(
            self,
            problem: Problem,
            x0: np.ndarray,
            index: int
    ) -> OptimizerResult:

        lb = problem.lb
        ub = problem.ub
        objective = problem.objective

        if dlib is None:
            raise ImportError(
                "This optimizer requires an installation of dlib."
            )

        if not objective.has_fun:
            raise Exception("For this optimizer, the objective must "
                            "be able to return function values.")

        sign = -1 \
            if objective.obj_type in MAXIMIZATION_OBJECTIVE_TYPES else 1

        # dlib requires variable length arguments
        def get_fval_vararg(*x):
            return sign * objective.get_fval(x)

        dlib.find_min_global(
            get_fval_vararg,
            list(lb),
            list(ub),
            int(self.options['maxiter']),
            0.002,
        )

        optimizer_result = OptimizerResult(
            x0=x0
        )

        return optimizer_result

    def is_least_squares(self):
        return False

    @staticmethod
    def get_default_options():
        return {}


class PyswarmOptimizer(Optimizer):
    """
    Global optimization using pyswarm.
    """

    def __init__(self, options: Dict = None):
        super().__init__()

        if options is None:
            options = {'maxiter': 200}
        self.options = options

    @fix_decorator
    @time_decorator
    @objective_decorator
    def optimize(
            self,
            problem: Problem,
            x0: np.ndarray,
            index: int
    ) -> OptimizerResult:
        lb = problem.lb
        ub = problem.ub
        if pyswarm is None:
            raise ImportError(
                "This optimizer requires an installation of pyswarm.")
        objective = problem.objective

        sign = -1 \
            if objective.obj_type in MAXIMIZATION_OBJECTIVE_TYPES \
            else 1

        # define cost function
        _fun = objective.get_fval
        fun = None if _fun is None else (lambda x: sign * _fun(x))

        # minimize
        xopt, fopt = pyswarm.pso(fun, lb, ub, **self.options)

        optimizer_result = OptimizerResult(
            x=xopt,
            fval=fopt
        )

        return optimizer_result

    def is_least_squares(self):
        return False

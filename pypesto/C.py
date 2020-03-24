"""
This is for (string) constants used in the objective module.
"""

# function modes
MODE_FUN = 'mode_fun'  # mode for function values
MODE_RES = 'mode_res'  # mode for residuals

# function return values
FVAL = 'fval'  # function value
GRAD = 'grad'  # gradient
HESS = 'hess'  # Hessian
HESSP = 'hessp'  # Hessian vector product
RES = 'res'  # residual
SRES = 'sres'  # residual sensitivities
RDATAS = 'rdatas'  # returned simulated data sets

# function types

COST_FUNCTION = 'COST_FUNCTION'
NEGATIVE_LOG_LIKELIHOOD = 'NEGATIVE_LOG_LIKELIHOOD'
NEGATIVE_LOG_POSTERIOR = 'NEGATIVE_LOG_POSTERIOR'
MINIMIZATION_OBJECTIVE_TYPES = [COST_FUNCTION, NEGATIVE_LOG_LIKELIHOOD,
                                NEGATIVE_LOG_POSTERIOR]
GAIN_FUNCTION = 'GAIN_FUNCTION'
LOG_LIKELIHOOD = 'LOG_LIKELIHOOD'
LOG_POSTERIOR = 'LOG_POSTERIOR'
MAXIMIZATION_OBJECTIVE_TYPES = [GAIN_FUNCTION, LOG_LIKELIHOOD, LOG_POSTERIOR]

OBJECTIVE_TYPES = [*MINIMIZATION_OBJECTIVE_TYPES,
                   *MAXIMIZATION_OBJECTIVE_TYPES]

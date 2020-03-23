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
LOG_LIKELIHOOD = 'LOG_LIKELIHOOD'  # obj type llh
NEGATIVE_LOG_LIKELIHOOD = 'NEGATIVE_LOG_LIKELIHOOD'  # obj type nllh
LOG_POSTERIOR = 'LOG_POSTERIOR'  # obj type lpost
NEGATIVE_LOG_POSTERIOR = 'NEGATIVE_LOG_POSTERIOR'  # obj type nlpost
OBJECTIVE_TYPES = [LOG_LIKELIHOOD, NEGATIVE_LOG_LIKELIHOOD,
                   LOG_POSTERIOR, NEGATIVE_LOG_POSTERIOR]
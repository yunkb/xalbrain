"""This module provides various utilities for internal use."""

__author__ = "Marie E. Rognes (meg@simula.no), 2012--2013"

__all__ = ["join", "state_space", "end_of_time", "convergence_rate"]

import math
import dolfin
import dolfin_adjoint

def join(subfunctions, V, annotate=False, solver_type="lu"):
    """
    Take a list of subfunctions s[i], and return the corresponding
    mixed function s = {s[0], s[1], ..., s[n]} in V

    **Optional arguments**

    * annotate (default: False)
      turn on annotation with annotate = True
    * solver_type (default: "lu")
      adjust solver_type of projection
    """

    # Project subfunctions onto mixed space
    return dolfin_adjoint.project(dolfin.as_vector(subfunctions), V,
                                  annotate=annotate, solver_type=solver_type)

def state_space(domain, d, family=None, k=1):
    """Return function space for the state variables.

    *Arguments*
      domain (:py:class:`dolfin.Mesh`)
        The computational domain
      d (int)
        The number of states
      family (string, optional)
        The finite element family, defaults to "CG" if None is given.
      k (int, optional)
        The finite element degree, defaults to 1

    *Returns*
      a function space (:py:class:`dolfin.FunctionSpace`)
    """
    if family is None:
        family = "CG"
    if d > 1:
        S = dolfin.VectorFunctionSpace(domain, family, k, d)
    else:
        S = dolfin.FunctionSpace(domain, family, k)
    return S

def end_of_time(T, t0, t1, dt):
    dolfin.info("End of time:%.16f > %.16f" % ((t1 + dt),
                                               T + dolfin.DOLFIN_EPS))
    return (t1 + dt) > (T + dolfin.DOLFIN_EPS)

def convergence_rate(hs, errors):
    assert (len(hs) == len(errors)), "hs and errors must have same length."
    # Compute converence rates
    rates = [(math.log(errors[i+1]/errors[i]))/(math.log(hs[i+1]/hs[i]))
             for i in range(len(hs)-1)]

    # Return convergence rates
    return rates

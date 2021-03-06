"""This module contains a AdEx neuronal cell model

The module was written by hand, in particular it was not
autogenerated.
"""

__author__ = "Jakob E. Schrein (jakob@xal.no), 2017"


from collections import OrderedDict
from xalbrain.cellmodels import CellModel

from dolfin import exp, assign, as_backend_type, Expression

import numpy as np


class AdexManual(CellModel):
    """Adaptive exponential integrate-and-fire model.

    This is a model containing two nonlinear, ODEs for the evolution
    of the transmembrane potential v and one additional state variable w
    """

    def __init__(self, params=None, init_conditions=None):
        """Create neuronal cell model, optionally from given parameters."""
        CellModel.__init__(self, params, init_conditions)

    @staticmethod
    def default_parameters():
        """Set-up and return default parameters."""
        params = OrderedDict([
            ("C", 59.0),          # Membrane capacitance (pF)
            ("g_L", 2.9),         # Leak conductance (nS)
            ("E_L", -62.0),       # Leak reversal potential (mV)
            ("V_T", -42.0),       # Spike threshold (mV)
            ("Delta_T", 3.0),     # Slope factor (mV)
            ("a", 16.0),          # Subthreshold adaptation (nS)
            ("tau_w", 144),       # Adaptation time constant (ms)
            ("b", 0.061),         # Spike-triggered adaptation (nA)
            ("spike", 20.0)       # When to reset (mV)
        ])
        return params

    def I(self, V, w, time=None):
        """Return the ionic current."""
        # Extract parameters
        C = self._parameters["C"]
        g_L = self._parameters["g_L"]
        E_L = self._parameters["E_L"]
        V_T = self._parameters["V_T"]
        Delta_T = self._parameters["Delta_T"]
        b = self._parameters["b"]
        spike = self._parameters["V_T"]

        I = (g_L*Delta_T*exp((V - V_T)/Delta_T) - g_L*(V - E_L) - w)/C
        return -I   # FIXME: Why -1?

    def F(self, V, w, time=None):
        """Return right-hand side for state variable evolution."""
        # Extract parameters
        a = self._parameters["a"]
        E_L = self._parameters["E_L"]
        tau_w = self._parameters["tau_w"]

        # Define model
        F = (a*(V - E_L) - w)/tau_w
        return -F   # FIXME: Why -1?

    #@staticmethod
    def default_initial_conditions(self):
        """Return default intial conditions. FIXME: I have no idea about values."""
        ic = OrderedDict(
            [("V", self._parameters["E_L"]),
            ("w", 0.0)
        ])
        return ic

    def num_states(self):
        """Return number of state variables."""
        return 1

    def update(self, vs):
        """Update solution if V > spike."""
        # Thanks to Miro
        functionSpace = vs.function_space()
        Vdofs = functionSpace.sub(0).dofmap().dofs()
        Wdofs = functionSpace.sub(1).dofmap().dofs()
    
        # Will do the manips via petsc
        vs_vec = as_backend_type(vs.vector()).vec()
    
        # fvec.array_r should be the read accessor
        toflip = np.where(vs_vec.array_r[Vdofs] > self._parameters["spike"])[0]
    
        # I want to make the first component its absolute value
        # NOTE that there are no copies of data underlying f
        vs_vec.array_w[Vdofs[toflip]] = self._parameters["E_L"]
        vs_vec.array_w[Wdofs[toflip]] += self._parameters["b"]

        """
        v, s = vs.split(deepcopy=True)
        v_idx = v.vector().array() > self._parameters["spike"]

        v.vector()[v_idx] = self._parameters["E_L"]
        s.vector()[v_idx] += self._parameters["b"]
        assign(vs.sub(0), v)
        assign(vs.sub(1), s)
        """

    def __str__(self):
        """Return string representation of class."""
        return "(Manual) AdEx neuronal cell model -- Slow version"

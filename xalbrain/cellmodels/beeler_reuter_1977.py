
"""This module contains a Beeler_reuter_1977 cardiac cell model

The module was autogenerated from a gotran ode file
"""
from __future__ import division
from collections import OrderedDict
import ufl

from xalbrain.dolfinimport import *
from xalbrain.cellmodels import CardiacCellModel

class Beeler_reuter_1977(CardiacCellModel):
    def __init__(self, params=None, init_conditions=None):
        """
        Create cardiac cell model

        *Arguments*
         params (dict, :py:class:`dolfin.Mesh`, optional)
           optional model parameters
         init_conditions (dict, :py:class:`dolfin.Mesh`, optional)
           optional initial conditions
        """
        CardiacCellModel.__init__(self, params, init_conditions)

    @staticmethod
    def default_parameters():
        "Set-up and return default parameters."
        params = OrderedDict([("E_Na", 50),
                              ("g_Na", 0.04),
                              ("g_Nac", 3e-05),
                              ("g_s", 0.0009),
                              ("IstimAmplitude", 0.0),
                              ("IstimEnd", 50000),
                              ("IstimPeriod", 1000),
                              ("IstimPulseDuration", 1),
                              ("IstimStart", 1),
                              ("C", 0.01)])
        return params

    @staticmethod
    def default_initial_conditions():
        "Set-up and return default initial conditions."
        ic = OrderedDict([("V", -84.624),
                          ("m", 0.011),
                          ("h", 0.988),
                          ("j", 0.975),
                          ("Cai", 0.0001),
                          ("d", 0.003),
                          ("f", 0.994),
                          ("x1", 0.0001)])
        return ic

    def _I(self, v, s, time):
        """
        Original gotran transmembrane current dV/dt
        """
        time = time if time else Constant(0.0)

        # Assign states
        V = v
        assert(len(s) == 7)
        m, h, j, Cai, d, f, x1 = s

        # Assign parameters
        E_Na = self._parameters["E_Na"]
        g_Na = self._parameters["g_Na"]
        g_Nac = self._parameters["g_Nac"]
        g_s = self._parameters["g_s"]
        IstimAmplitude = self._parameters["IstimAmplitude"]
        IstimPulseDuration = self._parameters["IstimPulseDuration"]
        IstimStart = self._parameters["IstimStart"]
        C = self._parameters["C"]

        # Init return args
        current = [ufl.zero()]*1

        # Expressions for the Sodium current component
        i_Na = (g_Nac + g_Na*(m*m*m)*h*j)*(-E_Na + V)

        # Expressions for the Slow inward current component
        E_s = -82.3 - 13.0287*ufl.ln(0.001*Cai)
        i_s = g_s*(-E_s + V)*d*f

        # Expressions for the Time dependent outward current component
        i_x1 = 0.00197277571153*(-1 +\
            21.7584023962*ufl.exp(0.04*V))*ufl.exp(-0.04*V)*x1

        # Expressions for the Time independent outward current component
        i_K1 = 0.0035*(-4 +\
            119.85640019*ufl.exp(0.04*V))/(8.33113748769*ufl.exp(0.04*V) +\
            69.4078518388*ufl.exp(0.08*V)) + 0.0035*(4.6 + 0.2*V)/(1 -\
            0.398519041085*ufl.exp(-0.04*V))

        # Expressions for the Stimulus protocol component
        Istim = ufl.conditional(ufl.And(ufl.ge(time, IstimStart),\
            ufl.le(time, IstimPulseDuration + IstimStart)), IstimAmplitude,\
            0)

        # Expressions for the Membrane component
        current[0] = (-i_K1 + Istim - i_Na - i_x1 - i_s)/C

        # Return results
        return current[0]

    def I(self, v, s, time=None):
        """
        Transmembrane current

           I = -dV/dt

        """
        return -self._I(v, s, time)

    def F(self, v, s, time=None):
        """
        Right hand side for ODE system
        """
        time = time if time else Constant(0.0)

        # Assign states
        V = v
        assert(len(s) == 7)
        m, h, j, Cai, d, f, x1 = s

        # Assign parameters
        g_s = self._parameters["g_s"]

        # Init return args
        F_expressions = [ufl.zero()]*7

        # Expressions for the Sodium current m gate component
        alpha_m = (-47 - V)/(-1 + 0.0090952771017*ufl.exp(-0.1*V))
        beta_m = 0.709552672749*ufl.exp(-0.056*V)
        F_expressions[0] = -beta_m*m + (1 - m)*alpha_m

        # Expressions for the Sodium current h gate component
        alpha_h = 5.49796243871e-10*ufl.exp(-0.25*V)
        beta_h = 1.7/(1 + 0.15802532089*ufl.exp(-0.082*V))
        F_expressions[1] = (1 - h)*alpha_h - beta_h*h

        # Expressions for the Sodium current j gate component
        alpha_j = 1.86904730072e-10*ufl.exp(-0.25*V)/(1 +\
            1.67882753e-07*ufl.exp(-0.2*V))
        beta_j = 0.3/(1 + 0.0407622039784*ufl.exp(-0.1*V))
        F_expressions[2] = (1 - j)*alpha_j - beta_j*j

        # Expressions for the Slow inward current component
        E_s = -82.3 - 13.0287*ufl.ln(0.001*Cai)
        i_s = g_s*(-E_s + V)*d*f
        F_expressions[3] = 7e-06 - 0.07*Cai - 0.01*i_s

        # Expressions for the Slow inward current d gate component
        alpha_d = 0.095*ufl.exp(1/20 - V/100)/(1 +\
            1.43328813857*ufl.exp(-0.0719942404608*V))
        beta_d = 0.07*ufl.exp(-44/59 - V/59)/(1 + ufl.exp(11/5 + V/20))
        F_expressions[4] = -beta_d*d + (1 - d)*alpha_d

        # Expressions for the Slow inward current f gate component
        alpha_f = 0.012*ufl.exp(-28/125 - V/125)/(1 +\
            66.5465065251*ufl.exp(0.149925037481*V))
        beta_f = 0.0065*ufl.exp(-3/5 - V/50)/(1 + ufl.exp(-6 - V/5))
        F_expressions[5] = (1 - f)*alpha_f - beta_f*f

        # Expressions for the Time dependent outward current x1 gate component
        alpha_x1 = 0.0311584109863*ufl.exp(0.0826446280992*V)/(1 +\
            17.4117080633*ufl.exp(0.0571428571429*V))
        beta_x1 = 0.000391646440562*ufl.exp(-0.0599880023995*V)/(1 +\
            ufl.exp(-4/5 - V/25))
        F_expressions[6] = (1 - x1)*alpha_x1 - beta_x1*x1

        # Return results
        return dolfin.as_vector(F_expressions)

    def num_states(self):
        return 7

    def __str__(self):
        return 'Beeler_reuter_1977 cardiac cell model'
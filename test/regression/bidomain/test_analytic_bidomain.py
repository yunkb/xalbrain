"""
This test just solves the bidomain equations with an analytic solution
(assuming no state variables) to verify the correctness of the
splitting solver.
"""

__author__ = "Marie E. Rognes (meg@simula.no), 2012--2013"
__all__ = []

from dolfin import *
from beatadjoint import *
from beatadjoint.utils import convergence_rate

def main(N, dt, T, theta):
    set_log_level(WARNING)

    mesh = UnitSquareMesh(N, N)

    # Create cardiac cell model
    cell_model = NoCellModel()

    # Create stimulus
    ac_str = "cos(t)*cos(2*pi*x[0])*cos(2*pi*x[1]) + 4*pow(pi, 2)*cos(2*pi*x[0])*cos(2*pi*x[1])*sin(t)"
    stimulus = Expression(ac_str, t=0, degree=3)

    # Create cardiac model
    heart = CardiacModel(mesh, 1.0, 1.0, cell_model, stimulus=stimulus)

    # Set-up solver
    parameters = SplittingSolver.default_parameters()
    parameters["theta"] = theta
    parameters["enable_adjoint"] = False # FIXME
    parameters["linear_variational_solver"]["linear_solver"] = "direct"
    solver = BasicSplittingSolver(heart, parameters)

    # Define exact solution (Note: v is returned at end of time
    # interval(s), u is computed at somewhere in the time interval
    # depending on theta)
    v_exact = Expression("cos(2*pi*x[0])*cos(2*pi*x[1])*sin(t)", t=T, degree=3)
    u_exact = Expression("-cos(2*pi*x[0])*cos(2*pi*x[1])*sin(t)/2.0",
                         t=T - (1 - theta)*dt, degree=3)

    # Define initial condition(s)
    vs0 = Function(solver.VS)
    (vs_, vs, u) = solver.solution_fields()
    vs_.assign(vs0)

    # Solve
    solutions = solver.solve((0, T), dt)
    for (timestep, vs, u) in solutions:
        continue

    (v, s) = vs.split(deepcopy=True)

    # Pre-computed reference errors (for regression checking):
    v_error = errornorm(v_exact, v, "L2", degree_rise=2)
    u_error = errornorm(u_exact, u, "L2", degree_rise=2)

    return (v_error, u_error, mesh.hmin(), dt, T)

def test_regression():

    # Create domain
    level = 0
    N = 10*(2**level)
    dt = 0.01/(2**level)
    T = 0.1
    (v_error, u_error, h, dt, T) = main(N, dt, T, 0.5)

    #v_reference = 4.1152719193176370e-03 # with degree = 5 and degree_rise=5
    #u_reference = 2.0271098018943513e-03 # with degree = 5 and degree_rise=5
    if level == 0:
        v_reference = 4.1142235248997714e-03
        u_reference = 2.0266633058042697e-03
    elif level == 1:
        v_reference = 1.0650181777538213e-03
        u_reference = 5.4032830628888496e-04
    elif level == 2:
        v_reference = 2.6874957469988218e-04
        u_reference = 1.3843820171918639e-04

    # Compute errors
    v_diff = abs(v_error - v_reference)
    u_diff = abs(u_error - u_reference)
    tolerance = 1.e-10
    msg = "Maximal %s value does not match reference: diff is %.16e"
    print "v_error = %.16e" % v_error
    print "u_error = %.16e" % u_error
    assert (v_diff < tolerance), msg % ("v", v_diff)
    assert (u_diff < tolerance), msg % ("u", u_diff)

def test_spatial_and_temporal_convergence():

    v_errors = []
    u_errors = []
    dts = []
    hs = []
    set_log_level(WARNING)
    T = 0.1
    dt = 0.01
    theta = 0.5
    N = 10
    for level in (0, 1, 2):
        a = dt/(2**level)
        (v_error, u_error, h, a, T) = main(N*(2**level), a, T, theta)
        v_errors.append(v_error)
        u_errors.append(u_error)
        dts.append(a)
        hs.append(h)

    v_rates = convergence_rate(hs, v_errors)
    u_rates = convergence_rate(hs, u_errors)
    print "v_errors = ", v_errors
    print "u_errors = ", u_errors
    print "v_rates = ", v_rates
    print "u_rates = ", u_rates

    assert all(v > 1.9 for v in v_rates), "Failed convergence for v"
    assert all(u > 1.9 for u in u_rates), "Failed convergence for u"

if __name__ == "__main__":

    test_regression()
    test_spatial_and_temporal_convergence()

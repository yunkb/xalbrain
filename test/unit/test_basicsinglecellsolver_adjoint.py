"""
Unit tests for various types of solvers for cardiac cell models.
"""

__author__ = "Marie E. Rognes (meg@simula.no), 2013"
__all__ = ["TestBasicSingleCellSolverAdjoint"]

from testutils import assert_equal, assert_true, assert_greater, adjoint, slow

import types
from beatadjoint.dolfinimport import UnitIntervalMesh, info_green
from beatadjoint import supported_cell_models, \
        Tentusscher_2004_mcell, FitzHughNagumoManual, \
        BasicSingleCellSolver, \
        replay_dolfin, InitialConditionParameter, \
        Constant, Expression, Function, Functional, \
        project, inner, assemble, dx, dt, FINISH_TIME, \
        parameters, compute_gradient_tlm, compute_gradient, \
        taylor_test, compute_adjoint

def set_dolfin_parameters():
    parameters["form_compiler"]["cpp_optimize"] = True
    flags = "-O3 -ffast-math -march=native"
    parameters["form_compiler"]["cpp_optimize_flags"] = flags

def basic_single_cell_closure(theta, Model):

    @adjoint
    @slow
    def test_replay(self):
        "Test that replay reports success for basic single cell solver"
        set_dolfin_parameters()
        model = Model()

        # Initialize solver
        params = BasicSingleCellSolver.default_parameters()
        params["theta"] = theta
        solver = BasicSingleCellSolver(model, None, params=params)

        info_green("Running %s with theta %g" % (model, theta))

        ics = Function(project(model.initial_conditions(), solver.VS),
                       name="ics")
        self._run(solver, model, ics)

        info_green("Replaying")
        success = replay_dolfin(tol=0.0, stop=True)
        assert_true(success)


    @adjoint
    @slow
    def test_compute_adjoint(self):
        "Test that we can compute the adjoint for some given functional"
        set_dolfin_parameters()
        model = Model()

        params = BasicSingleCellSolver.default_parameters()
        params["theta"] = theta
        solver = BasicSingleCellSolver(model, None, params=params)

        # Get initial conditions (Projection of expressions
        # don't get annotated, which is fine, because there is
        # no need.)
        ics = project(model.initial_conditions(), solver.VS)

        # Run forward model
        info_green("Running forward %s with theta %g" % (model, theta))
        self._run(solver, model, ics)

        (vs_, vs) = solver.solution_fields()

        # Define functional and compute gradient etc
        J = Functional(inner(vs_, vs_)*dx*dt[FINISH_TIME])

        # Compute adjoint
        info_green("Computing adjoint")
        z = compute_adjoint(J)

        # Check that no vs_ adjoint is None (== 0.0!)
        for (value, var) in z:
            if var.name == "vs_":
                msg = "Adjoint solution for vs_ is None (#fail)."
                assert (value is not None), msg

    @adjoint
    @slow
    def test_compute_gradient(self):
        "Test that we can compute the gradient for some given functional"
        set_dolfin_parameters()
        model = Model()

        params = BasicSingleCellSolver.default_parameters()
        params["theta"] = theta
        solver = BasicSingleCellSolver(model, None, params=params)

        # Get initial conditions (Projection of expressions
        # don't get annotated, which is fine, because there is
        # no need.)
        ics = project(model.initial_conditions(), solver.VS)

        # Run forward model
        info_green("Running forward %s with theta %g" % (model, theta))
        self._run(solver, model, ics)

        # Define functional
        (vs_, vs) = solver.solution_fields()
        J = Functional(inner(vs, vs)*dx*dt[FINISH_TIME])

        # Compute gradient with respect to vs_. Highly unclear
        # why with respect to ics and vs fail.
        info_green("Computing gradient")
        dJdics = compute_gradient(J, InitialConditionParameter(vs_))
        assert (dJdics is not None), "Gradient is None (#fail)."
        print dJdics.vector().array()

    @adjoint
    @slow
    def test_taylor_remainder(self):
        "Run Taylor remainder tests for selection of models and solvers."
        set_dolfin_parameters()
        model = Model()

        params = BasicSingleCellSolver.default_parameters()
        params["theta"] = theta
        solver = BasicSingleCellSolver(model, None, params=params)

        # Get initial conditions (Projection of expressions
        # don't get annotated, which is fine, because there is
        # no need.)
        ics = project(model.initial_conditions(), solver.VS)

        # Run forward model
        info_green("Running forward %s with theta %g" % (model, theta))
        self._run(solver, model, ics)

        # Define functional
        (vs_, vs) = solver.solution_fields()
        form = lambda w: inner(w, w)*dx
        J = Functional(form(vs)*dt[FINISH_TIME])

        # Compute value of functional with current ics
        Jics = assemble(form(vs))

        # Compute gradient with respect to vs_ (ics?)
        dJdics = compute_gradient(J, InitialConditionParameter(vs_),
                                  forget=False)

        # Stop annotating
        parameters["adjoint"]["stop_annotating"] = True

        # Set-up runner
        def Jhat(ics):
            self._run(solver, model, ics)
            (vs_, vs) = solver.solution_fields()
            return assemble(form(vs))

        # Run taylor test
        if isinstance(model, Tentusscher_2004_mcell):
            seed=1.e-5
        else:
            seed=None

        conv_rate = taylor_test(Jhat, InitialConditionParameter(vs_),
                                Jics, dJdics, seed=seed)

        # Check that minimal rate is greater than some given number
        assert_greater(conv_rate, 1.8)

    # Return functions with Model and theta fixed
    return tuple(func for func in locals().values() if isinstance(func, types.FunctionType))

class TestBasicSingleCellSolverAdjoint(object):
    "Test adjoint functionality for the basic single cell solver."

    def _run(self, solver, model, ics):
        # Assign initial conditions
        (vs_, vs) = solver.solution_fields()
        vs_.assign(ics)

        # Solve for a couple of steps
        dt = 0.01
        T = 2*dt
        solutions = solver.solve((0.0, T), dt)
        for ((t0, t1), vs) in solutions:
            pass

for theta, theta_name in ((0.0, "00"), (0.5, "05"), (1.0, "10")):
    for Model in (FitzHughNagumoManual, Tentusscher_2004_mcell):
        for func in basic_single_cell_closure(theta, Model):
            method_name = func.func_name+"_theta_"+theta_name+"_"+Model.__name__
            setattr(TestBasicSingleCellSolverAdjoint, method_name, func)

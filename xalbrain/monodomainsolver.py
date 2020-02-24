r"""
These solvers solve the (pure) monodomain equations on the form: find
the transmembrane potential :math:`v = v(x, t)` such that

.. math::

   v_t - \mathrm{div} ( G_i v) = I_s

where the subscript :math:`t` denotes the time derivative; :math:`G_i`
denotes a weighted gradient: :math:`G_i = M_i \mathrm{grad}(v)` for,
where :math:`M_i` is the intracellular cardiac conductivity tensor;
:math:`I_s` ise prescribed input. In addition, initial conditions are
given for :math:`v`:

.. math::

   v(x, 0) = v_0

Finally, boundary conditions must be prescribed. For now, this solver assumes pure
homogeneous Neumann boundary conditions for :math:`v`.
"""

# Copyright (C) 2013 Johan Hake (hake@simula.no)
# Use and modify at will
# Last changed: 2013-04-18

__all__ = [
    "BasicMonodomainSolver",
    "MonodomainSolver"
]

import dolfin as df

from xalbrain.utils import end_of_time

from typing import (
    Union,
    Dict,
    Tuple,
    Any,
)


class BasicMonodomainSolver:
    """This solver is based on a theta-scheme discretization in time
    and CG_1 elements in space.

    .. note::

       For the sake of simplicity and consistency with other solver
       objects, this solver operates on its solution fields (as state
       variables) directly internally. More precisely, solve (and
       step) calls will act by updating the internal solution
       fields. It implies that initial conditions can be set (and are
       intended to be set) by modifying the solution fields prior to
       simulation.

    *Arguments*
      mesh (:py:class:`dolfin.Mesh`)
        The spatial domain (mesh)

      time (:py:class:`dolfin.Constant` or None)
        A constant holding the current time. If None is given, time is
        created for you, initialized to zero.

      M_i (:py:class:`ufl.Expr`)
        The intracellular conductivity tensor (as an UFL expression)

      I_s (:py:class:`dict`, optional)
        A typically time-dependent external stimulus given as a dict,
        with domain markers as the key and a
        :py:class:`dolfin.Expression` as values. NB: it is assumed
        that the time dependence of I_s is encoded via the 'time'
        Constant.

      v\_ (:py:class:`ufl.Expr`, optional)
        Initial condition for v. A new :py:class:`dolfin.Function`
        will be created if none is given.

      params (:py:class:`dolfin.Parameters`, optional)
        Solver parameters

    """
    def __init__(
            self,
            mesh: df.Mesh,
            time: df.Constant,
            M_i: Union[df.Expression, Dict[int, df.Expression]],
            I_s: Union[df.Expression, Dict[int, df.Expression]] = None,
            v_: df.Function = None,
            cell_domains: df.MeshFunction = None,
            facet_domains: df.MeshFunction = None,
            params: df.Parameters = None
    ) -> None:
        # Check some input
        assert isinstance(mesh, df.Mesh), "Expecting mesh to be a Mesh instance, not {}".format(mesh)

        msg = "Expecting time to be a Constant instance (or None)."
        assert isinstance(time, df.Constant) or time is None, msg

        msg = "Expecting params to be a Parameters instance (or None)"
        assert isinstance(params, df.Parameters) or params is None, msg

        # Store input
        self._mesh = mesh
        self._I_s = I_s
        self._time = time

        # Initialize and update parameters if given
        self.parameters = self.default_parameters()
        if params is not None:
            self.parameters.update(params)

        # Set-up function spaces
        k = self.parameters["polynomial_degree"]
        V = df.FunctionSpace(self._mesh, "CG", k)

        self.V = V

        # Set-up solution fields:
        if v_ is None:
            self.v_ = df.Function(V, name="v_")
        else:
            self.v_ = v_

        self.v = df.Function(self.V, name="v")

        if cell_domains is None:
            cell_domains = df.MeshFunction("size_t", mesh, self._mesh.geometry().dim())
            cell_domains.set_all(0)

        # Chech that it is indeed a cell function.
        cell_dim = cell_domains.dim()
        mesh_dim = self._mesh.geometry().dim()
        msg = "Got {}, expected {}.".format(cell_dim, mesh_dim)
        assert cell_dim == mesh_dim, msg
        self._cell_domains = cell_domains

        if facet_domains is None:
            facet_domains = df.MeshFunction("size_t", mesh, self._mesh.geometry().dim() - 1)
            facet_domains.set_all(0)

        # Check that it is indeed a facet function.
        facet_dim = facet_domains.dim()
        msg = "Got {}, expected {}.".format(facet_dim, mesh_dim)
        assert facet_dim == mesh_dim - 1, msg
        self._facet_domains = facet_domains

        if not isinstance(M_i, dict):
            M_i = {int(i): M_i for i in set(self._cell_domains.array())}
        else:
            M_i_keys = set(M_i.keys())
            cell_keys = set(self._cell_domains.array())
            msg = "Got {}, expected {}.".format(M_i_keys, cell_keys)
            assert M_i_keys == cell_keys, msg
        self._M_i = M_i

    @property
    def time(self) -> df.Constant:
        """The internal time of the solver."""
        return self._time

    def solution_fields(self) -> Tuple[df.Function]:
        """Return tuple of previous and current solution objects.

        Modifying these will modify the solution objects of the solver
        and thus provides a way for setting initial conditions for
        instance.

        *Returns*
          (previous v, current v) (:py:class:`tuple` of :py:class:`dolfin.Function`)
        """
        return self.v_, self.v

    def solve(self, t0: float, t1: float, dt: float) -> None:
        """
        Solve the discretization on a given time interval (t0, t1)
        with a given timestep dt and return generator for a tuple of
        the interval and the current solution.

        *Arguments*
          interval (:py:class:`tuple`)
            The time interval for the solve given by (t0, t1)
          dt (int, optional)
            The timestep for the solve. Defaults to length of interval

        *Returns*
          (timestep, solution_field) via (:py:class:`genexpr`)

        *Example of usage*::

          # Create generator
          solutions = solver.solve((0.0, 1.0), 0.1)

          # Iterate over generator (computes solutions as you go)
          for (interval, solution_fields) in solutions:
            (t0, t1) = interval
            v_, v = solution_fields
            # do something with the solutions
        """
        # Solve on entire interval if no interval is given.
        if dt is None:
            dt = t1 - t0

        _t0 = t0
        _t1 = t0 + dt

        # Step through time steps until at end time
        while True:
            # info("Solving on t = (%g, %g)" % (t0, t1))
            self.step(_t0, _t1)

            # Yield solutions
            yield (_t0, _t1), self.solution_fields()

            # Break if this is the last step
            if end_of_time(t1, _t0, _t1, dt):
                break

            # If not: update members and move to next time
            if isinstance(self.v_, df.Function):
                self.v_.assign(self.v)

            _t0 = _t1
            _t1 = _t0 + dt

    def step(self, t0: float, t1: float) -> None:
        r"""Solve on the given time interval (t0, t1).

        *Arguments*
          interval (:py:class:`tuple`)
            The time interval (t0, t1) for the step

        *Invariants*
          Assuming that v\_ is in the correct state for t0, gives
          self.v in correct state at t1.
        """
        # Extract interval and thus time-step
        k_n = df.Constant(t1 - t0)

        # Extract theta parameter and conductivities
        theta = self.parameters["theta"]
        M_i = self._M_i

        # Set time
        t = t0 + theta*(t1 - t0)
        self.time.assign(t)

        # Get physical parameters
        chi = self.parameters["Chi"]
        capacitance = self.parameters["Cm"]
        lam = self.parameters["lambda"]
        lam_frac = df.Constant(lam/(1 + lam))

        # Define variational formulation
        v = df.TrialFunction(self.V)
        w = df.TestFunction(self.V)
        Dt_v_k_n = (v - self.v_)/k_n
        Dt_v_k_n *= chi*capacitance
        v_mid = theta*v + (1.0 - theta)*self.v_

        dz = df.Measure("dx", domain=self._mesh, subdomain_data=self._cell_domains)
        db = df.Measure("ds", domain=self._mesh, subdomain_data=self._facet_domains)
        # dz, rhs = rhs_with_markerwise_field(self._I_s, self._mesh, w)
        cell_tags = map(int, set(self._cell_domains.array()))   # np.int64 does not work
        facet_tags = map(int, set(self._facet_domains.array()))

        for key in cell_tags:
            G = Dt_v_k_n*w*dz(key)
            G += lam_frac*df.inner(M_i[key]*df.grad(v_mid), df.grad(w))*dz(key)

            if self._I_s is None:
                G -= chi*df.Constant(0)*w*dz(key)
            else:
                G -= chi*self._I_s*w*dz(key)

        # Define variational problem
        a, L = df.system(G)
        pde = df.LinearVariationalProblem(a, L, self.v)

        # Set-up solver
        solver_type = self.parameters["linear_solver_type"]
        solver = df.LinearVariationalSolver(pde)
        solver.solve()

    @staticmethod
    def default_parameters() -> df.Parameters:
        """
        Initialize and return a set of default parameters.

        *Returns*
          A set of parameters (:py:class:`dolfin.Parameters`)

        To inspect all the default parameters, do::

          info(BasicMonodomainSolver.default_parameters(), True)
        """
        params = df.Parameters("BasicMonodomainSolver")
        params.add("theta", 0.5)
        params.add("polynomial_degree", 1)
        params.add("enable_adjoint", False)
        params.add("default_timestep", 1.0)

        # Set default solver type to be iterative
        params.add("linear_solver_type", "direct")
        params.add("lu_type", "default")

        # Set default iterative solver choices (used if iterative
        # solver is invoked)
        params.add("algorithm", "cg")
        params.add("preconditioner", "petsc_amg")
        params.add("use_custom_preconditioner", False)

        params.add("Chi", 1.0)      # Membrane to volume ratio
        params.add("Cm", 1.0)      # Membrane Capacitance
        params.add("lambda", 1.0)
        return params

class MonodomainSolver(BasicMonodomainSolver):
    __doc__ = BasicMonodomainSolver.__doc__

    def __init__(
            self,
            mesh: df.Mesh,
            time: df.Constant,
            M_i: Union[df.Expression, Dict[int, df.Expression]],
            I_s: Union[df.Expression, Dict[int, df.Expression]] = None,
            v_: df.Function = None,
            cell_domains: df.MeshFunction = None,
            facet_domains: df.MeshFunction = None,
            params: df.Parameters = None
    ) -> None:
        super().__init__(
            mesh,
            time,
            M_i,
            I_s=I_s,
            v_=v_,
            cell_domains=cell_domains,
            facet_domains=facet_domains,
            params=params)

        # Create variational forms
        self._timestep = df.Constant(self.parameters["default_timestep"])
        self._lhs, self._rhs, self._prec = self.variational_forms(self._timestep)

        # Preassemble left-hand side (will be updated if time-step changes)
        self._lhs_matrix = df.assemble(self._lhs)
        self._rhs_vector = df.Vector(mesh.mpi_comm(), self._lhs_matrix.size(0))
        self._lhs_matrix.init_vector(self._rhs_vector, 0)

        # Create linear solver (based on parameter choices)
        self._linear_solver, self._update_solver = self._create_linear_solver()

    @property
    def linear_solver(self) -> Any:
        """The linear solver (:py:class:`dolfin.LUSolver` or :py:class:`dolfin.KrylovSolver`)."""
        return self._linear_solver

    def _create_linear_solver(self):
        "Helper function for creating linear solver based on parameters."
        solver_type = self.parameters["linear_solver_type"]

        if solver_type == "direct":
            solver = df.LUSolver(self._lhs_matrix, self.parameters["lu_type"])
            solver.parameters["symmetric"] = True
            update_routine = self._update_lu_solver

        elif solver_type == "iterative":
            # Preassemble preconditioner (will be updated if time-step changes)
            # Initialize KrylovSolver with matrix and preconditioner
            alg = self.parameters["algorithm"]
            prec = self.parameters["preconditioner"]
            if self.parameters["use_custom_preconditioner"]:
                self._prec_matrix = df.assemble(self._prec)
                solver = df.PETScKrylovSolver(alg, prec)
                solver.parameters.update(self.parameters["krylov_solver"])
                solver.set_operators(self._lhs_matrix, self._prec_matrix)
                solver.ksp().setFromOptions()
            else:
                solver = df.PETScKrylovSolver(alg, prec)
                solver.set_operator(self._lhs_matrix)
                solver.parameters["nonzero_initial_guess"] = True
                solver.parameters["monitor_convergence"] = True

                solver.ksp().setFromOptions()

            update_routine = self._update_krylov_solver
        else:
            assert False, "Unknown linear_solver_type given: {}".format(solver_type)
        return solver, update_routine

    @staticmethod
    def default_parameters() -> df.Parameters:
        """Initialize and return a set of default parameters

        *Returns*
          A set of parameters (:py:class:`dolfin.Parameters`)

        To inspect all the default parameters, do::

          info(MonodomainSolver.default_parameters(), True)
        """
        params = df.Parameters("MonodomainSolver")
        params.add("enable_adjoint", False)
        params.add("theta", 0.5)
        params.add("polynomial_degree", 1)
        params.add("default_timestep", 1.0)

        # Set default solver type to be iterative
        params.add("linear_solver_type", "direct")
        params.add("lu_type", "default")

        # Set default iterative solver choices (used if iterative solver is invoked)
        params.add("algorithm", "cg")
        params.add("preconditioner", "petsc_amg")
        params.add("use_custom_preconditioner", False)

        params.add("Chi", 1.0)        # Membrane to volume ratio
        params.add("Cm", 1.0)         # Membrane capacitance
        params.add("lambda", 1.0)
        return params

    def variational_forms(self, k_n: df.Constant):
        """Create the variational forms corresponding to the given
        discretization of the given system of equations.

        *Arguments*
          k_n (:py:class:`ufl.Expr` or float)
            The time step

        *Returns*
          (lhs, rhs, prec) (:py:class:`tuple` of :py:class:`ufl.Form`)
        """
        # Extract theta parameter and conductivities
        theta = self.parameters["theta"]
        M_i = self._M_i

        # Define variational formulation
        v = df.TrialFunction(self.V)
        w = df.TestFunction(self.V)

        chi = self.parameters["Chi"]
        capacitance = self.parameters["Cm"]
        lam = self.parameters["lambda"]
        lam_frac = df.Constant(lam/(1 + lam))

        # Set-up variational problem
        Dt_v_k_n = (v - self.v_)/k_n
        Dt_v_k_n *= chi*capacitance
        v_mid = theta*v + (1.0 - theta)*self.v_

        dz = df.Measure("dx", domain=self._mesh, subdomain_data=self._cell_domains)
        cell_tags = map(int, set(self._cell_domains.array()))   # np.int64 does not work

        # Currently not used
        db = df.Measure("ds", domain=self._mesh, subdomain_data=self._facet_domains)
        facet_tags = map(int, set(self._facet_domains.array()))

        prec = 0
        for key in cell_tags:
            G = Dt_v_k_n*w*dz(key)
            G += lam_frac*df.inner(M_i[key]*df.grad(v_mid), df.grad(w))*dz(key)

            if self._I_s is None:
                G -= chi*df.Constant(0)*w*dz(key)
            else:
                G -= chi*self._I_s*w*dz(key)

        # Define preconditioner based on educated(?) guess by Marie
        prec += (v*w + k_n/2.0*df.inner(M_i[key]*df.grad(v), df.grad(w)))*dz(key)

        a, L = df.system(G)
        return a, L, prec

    def step(self, t0: float, t1: float) -> None:
        """Solve on the given time step (t0, t1).

        *Arguments*
          interval (:py:class:`tuple`)
            The time interval (t0, t1) for the step

        *Invariants*
          Assuming that v\_ is in the correct state for t0, gives
          self.v in correct state at t1.
        """
        timer = df.Timer("PDE Step")

        # Extract interval and thus time-step
        dt = t1 - t0
        theta = self.parameters["theta"]
        t = t0 + theta*dt
        self.time.assign(t)

        # Update matrix and linear solvers etc as needed
        timestep_unchanged = (abs(dt - float(self._timestep)) < 1.e-12)
        self._update_solver(timestep_unchanged, dt)

        # Assemble right-hand-side
        timer0 = df.Timer("Assemble rhs")
        df.assemble(self._rhs, tensor=self._rhs_vector)
        del timer0

        # Solve problem
        self.linear_solver.solve(
            self.v.vector(),
            self._rhs_vector
        )
        timer.stop()

    def _update_lu_solver(self, timestep_unchanged, dt):
        """Helper function for updating an LUSolver depending on whether timestep has changed."""
        # Update reuse of factorization parameter in accordance with changes in timestep
        if timestep_unchanged:
            return

        # Update stored timestep
        self._timestep.assign(df.Constant(dt))

        # Reassemble matrix
        df.assemble(self._lhs, tensor=self._lhs_matrix)

    def _update_krylov_solver(self, timestep_unchanged: bool, dt: float) -> None:
        """Helper function for updating a KrylovSolver depending on whether timestep has changed."""
        # Update reuse of preconditioner parameter in accordance with changes in timestep
        if timestep_unchanged:
            return

        # Update stored timestep
        self._timestep.assign(df.Constant(dt))

        # Reassemble matrix
        df.assemble(self._lhs, tensor=self._lhs_matrix)

        # Reassemble preconditioner
        if self.parameters["use_custom_preconditioner"]:
            df.assemble(self._prec, tensor=self._prec_matrix)

class Problem:
    def __init__(self, MILPName, DataName, Solver):
        self.MILPName = MILPName
        self.DataName = DataName
        self.MILP_SOLVER = Solver
        self.RunMILPAlgo()

    def RunMILPAlgo(self):  # run GLPK to solve the target pb
        import swiglpk

        filename = r"Displaylog.txt"
        glpProblem = swiglpk.glp_create_prob()
        tran = swiglpk.glp_mpl_alloc_wksp()
        ret = swiglpk.glp_mpl_read_model(tran, self.MILPName, 1)
        if ret != 0:
            print("error reading Target MILP file")
        if ret == 0:
            ret = swiglpk.glp_mpl_read_data(tran, self.DataName)
            if ret != 0:
                print("error reading Target DATA file")
            if ret == 0:
                ret = swiglpk.glp_mpl_generate(tran, None)
                if ret != 0:
                    print("error reading Target DATA file")
                if ret == 0:
                    swiglpk.glp_mpl_build_prob(tran, glpProblem)
                    if self.MILP_SOLVER == "CPLEX":  # CPLEX Call line
                        import cplex

                        lpnam = r"problem_CPLEX.lp"
                        swiglpk.glp_write_lp(glpProblem, None, lpnam)
                        c = cplex.Cplex()
                        out = c.set_results_stream(None)
                        out = c.set_log_stream(None)
                        c.read(lpnam)

                        # Convergence tools
                        c.parameters.mip.display.set(5)  # Log ultra-détaillé
                        c.parameters.mip.interval.set(1)  # Affiche chaque noeud
                        c.parameters.mip.tolerances.mipgap.set(0.0003)  # Gap mini à 0.03% de l'objectif

                        c.solve()

                        print(f"Status: {c.solution.get_status_string()}")
                        print(f"Noeuds explorés: {c.solution.progress.get_num_nodes_processed()}")
                        print(f"Noeuds restants: {c.solution.progress.get_num_nodes_remaining()}")
                        print(f"Gap: {c.solution.MIP.get_mip_relative_gap()}")
                        print(f"Meilleure borne: {c.solution.MIP.get_best_objective()}")
                        print(f"Meilleure solution: {c.solution.get_objective_value()}")


                        c.solution.write(r"Solution.xml")
                        c.end()  # to be completed with the results extraction
                    else:

                        parm = swiglpk.glp_smcp()
                        swiglpk.glp_init_smcp(parm)
                        parm.presolve = swiglpk.GLP_ON
                        swiglpk.glp_simplex(glpProblem, parm)
                        swiglpk.glp_intopt(glpProblem, None)
                        ret = swiglpk.glp_mpl_postsolve(tran, glpProblem, 3)  # 3 is MIP
                        if ret != 0:
                            print("error on postsolving")
                        else:
                            swiglpk.glp_mpl_free_wksp(tran)
                            swiglpk.glp_print_sol(glpProblem, r"solution.txt")
                            Nrows = swiglpk.glp_get_num_rows(glpProblem)
                            Ncols = swiglpk.glp_get_num_cols(glpProblem)
                            for i in range(1, Ncols + 1):
                                name = swiglpk.glp_get_col_name(glpProblem, i)
                                # if name.find("Q_dot")!=-1:
                                if name == "TotalCost":
                                    value = swiglpk.glp_mip_col_val(glpProblem, i)
                                    print("The total Cost is =", value)

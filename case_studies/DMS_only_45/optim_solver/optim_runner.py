from solver_class import Problem
import os

os.chdir(os.path.dirname(__file__))

MOD_FILE = r"system_model.mod"
DAT_FILE = r"system_data.dat"

Problem(MILPName=MOD_FILE, 
        DataName=DAT_FILE, 
        Solver="CPLEX")

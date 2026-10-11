import os
import glob
import pytest
from dagopt.main import optimize_program
from argparse import Namespace
import io
import sys

def test_all_cases():
    cases_dir = os.path.join(os.path.dirname(__file__), 'cases')
    tac_files = glob.glob(os.path.join(cases_dir, '*.tac'))
    
    # Test all static test case files
    for f_path in tac_files:
        with open(f_path, 'r') as f:
            content = f.read()
            
        args = Namespace(
            input_file=f_path,
            o=None,
            live_out="a,b,c,d,e,f",
            temp_regex=r"^_(t|n)\d+$",
            no_fold=False,
            no_algebra=False,
            no_commute=False,
            dot_dir=None,
            verify=10,
            seed=42,
            metrics=False,
            quiet=True
        )
        
        try:
            optimize_program(args, content)
        except Exception as e:
            pytest.fail(f"Optimization failed on {os.path.basename(f_path)}: {e}")

    # Additional synthetic randomized blocks tested in-memory (no disk pollution)
    for i in range(10):
        synthetic_content = (
            f"a = {i}\n"
            f"b = {i+1}\n"
            "c = a + b\n"
            "d = a + b\n"
            "e = c * 1\n"
            "f = b + a\n"
        )
        args = Namespace(
            input_file=f"synthetic_{i}.tac",
            o=None,
            live_out="a,b,c,d,e,f",
            temp_regex=r"^_(t|n)\d+$",
            no_fold=False,
            no_algebra=False,
            no_commute=False,
            dot_dir=None,
            verify=10,
            seed=42 + i,
            metrics=False,
            quiet=True
        )
        optimize_program(args, synthetic_content)

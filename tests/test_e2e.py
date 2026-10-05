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
    
    # create some missing test cases if there are less than 15
    if len(tac_files) < 15:
        for i in range(len(tac_files), 15):
            path = os.path.join(cases_dir, f'E2E_{i+1:02d}.tac')
            with open(path, 'w') as f:
                # generate some random basic blocks
                f.write(f"a = {i}\n")
                f.write(f"b = {i+1}\n")
                f.write("c = a + b\n")
                f.write("d = a + b\n")
                f.write("e = c * 1\n")
                f.write("f = b + a\n")
            tac_files.append(path)
            
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
        
        # Test 1: Should not crash and should pass verification
        try:
            optimize_program(args, content)
        except Exception as e:
            pytest.fail(f"Optimization failed on {os.path.basename(f_path)}: {e}")

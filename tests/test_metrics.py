import io
from dagopt.metrics import BlockMetrics, TotalMetrics, print_metrics_table

def test_metrics_print():
    b = BlockMetrics(
        block_id=0, instrs_before=10, instrs_after=5,
        arith_before=5, arith_after=2, copy_before=2, copy_after=1,
        dag_nodes=8, cse_hits=3, constants_folded=1,
        algebraic_simplifications=0, dead_nodes_removed=2,
        verification_passed=True
    )
    t = TotalMetrics(
        total_instrs_before=10, total_instrs_after=5,
        total_arith_before=5, total_arith_after=2,
        total_copy_before=2, total_copy_after=1,
        total_dag_nodes=8, total_cse_hits=3,
        total_constants_folded=1, total_algebraic_simplifications=0,
        total_dead_nodes_removed=2, total_verification_passed=True
    )
    
    out = io.StringIO()
    print_metrics_table([b], t, out=out)
    output = out.getvalue()
    
    assert "Block" in output
    assert "TOTAL" in output
    assert "10" in output
    assert "True" in output

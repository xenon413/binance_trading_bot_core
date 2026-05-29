from core.log_handle import LogHandle
import pytest

@pytest.mark.precheck
def test_functionality(test_logger:LogHandle):
    test_logger.write_log("test")

@pytest.mark.precheck
def test_edge_case(test_logger:LogHandle):    
    # test for writing unicode
    test_logger.write_log("❌")
    test_logger.write_log("\u2705")
    test_logger.write_log("Ａ")
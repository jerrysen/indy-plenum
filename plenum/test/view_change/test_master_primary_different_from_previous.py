import types

import pytest

from plenum.test.helper import checkViewNoForNodes, \
    sendReqsToNodesAndVerifySuffReplies, countDiscarded
from plenum.test.malicious_behaviors_node import slow_primary
from plenum.test.test_node import getPrimaryReplica, ensureElectionsDone
from plenum.test.pool_transactions.conftest import clientAndWallet1, client1, \
    wallet1, client1Connected, looper
from plenum.test.view_change.helper import provoke_and_wait_for_view_change

from stp_core.common.log import getlogger
logger = getlogger()


@pytest.mark.skip(reason='SOV-1020')
def test_master_primary_different_from_previous(txnPoolNodeSet,
                                                 looper, client1,
                                                 wallet1, client1Connected):
    """
    After a view change, primary must be different from previous primary for
    master instance, it does not matter for other instance. The primary is
    benign and does not vote for itself.
    """
    old_view_no = checkViewNoForNodes(txnPoolNodeSet)
    pr = slow_primary(txnPoolNodeSet, 0, delay=10)
    old_pr_node_name = pr.node.name

    # View change happens
    provoke_and_wait_for_view_change(looper,
                                     txnPoolNodeSet,
                                     old_view_no + 1,
                                     wallet1,
                                     client1)
    logger.debug("VIEW HAS BEEN CHANGED!")
    # Elections done
    ensureElectionsDone(looper=looper, nodes=txnPoolNodeSet)
    # New primary is not same as old primary
    assert getPrimaryReplica(txnPoolNodeSet, 0).node.name != old_pr_node_name

    pr.outBoxTestStasher.resetDelays()

    # The new primary can still process requests
    sendReqsToNodesAndVerifySuffReplies(looper, wallet1, client1, 5)



@pytest.mark.skip(reason='SOV-1020')
def test_master_primary_different_from_previous_view_for_itself(txnPoolNodeSet,
                                                 looper, client1,
                                                 wallet1, client1Connected):
    """
    After a view change, primary must be different from previous primary for
    master instance, it does not matter for other instance. Break it into
    2 tests, one where the primary is malign and votes for itself but is still
    not made primary in the next view.
    """
    old_view_no = checkViewNoForNodes(txnPoolNodeSet)
    pr = slow_primary(txnPoolNodeSet, 0, delay=10)
    old_pr_node = pr.node

    def _get_undecided_inst_id(self):
        undecideds = [i for i, r in enumerate(self.replicas)
                      if r.isPrimary is None]
        # Try to nominate for the master instance
        return undecideds, 0

    # Patching old primary's elector's method to nominate itself
    # again for the the new view
    old_pr_node.elector._get_undecided_inst_id = types.MethodType(
        _get_undecided_inst_id, old_pr_node.elector)

    # View change happens
    provoke_and_wait_for_view_change(looper,
                                     txnPoolNodeSet,
                                     old_view_no + 1,
                                     wallet1,
                                     client1)

    # Elections done
    ensureElectionsDone(looper=looper, nodes=txnPoolNodeSet)
    # New primary is not same as old primary
    assert getPrimaryReplica(txnPoolNodeSet, 0).node.name != old_pr_node.name

    # All other nodes discarded the nomination by the old primary
    for node in txnPoolNodeSet:
        if node != old_pr_node:
            assert countDiscarded(node.elector,
                                  'of master in previous view too') == 1

    # The new primary can still process requests
    sendReqsToNodesAndVerifySuffReplies(looper, wallet1, client1, 5)
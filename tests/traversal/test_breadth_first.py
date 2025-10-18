import numpy as np
from bw2calc import LCA
from bw2data import Database, get_node
from bw2data.tests import bw2test

from bw_graph_tools import BreadthFirstGraphTraversal, GraphTraversalSettings


@bw2test
def test_breadth_first_basic_traversal():
    """Test basic breadth-first traversal without scores."""
    Database("t").write(
        {
            ("t", "1"): {
                "name": "1",
                "exchanges": [
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "1"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "2"): {
                "name": "2",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 2,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "3"): {
                "name": "3",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
        }
    )

    lca = LCA({("t", "1"): 1})
    lca.lci()

    settings = GraphTraversalSettings(max_calc=100, max_depth=None)
    bfgt = BreadthFirstGraphTraversal(lca, settings)
    bfgt.traverse()

    nodes = bfgt.nodes
    edges = bfgt.edges

    # Should have 4 nodes: functional unit + 3 activities
    assert len(nodes) == 4
    # Should have 3 edges
    assert len(edges) == 3

    # Verify depths are correct (breadth-first means all nodes at same depth processed together)
    t1_node = [n for n in nodes.values() if n.activity_datapackage_id == get_node(code="1").id][0]
    t2_node = [n for n in nodes.values() if n.activity_datapackage_id == get_node(code="2").id][0]
    t3_node = [n for n in nodes.values() if n.activity_datapackage_id == get_node(code="3").id][0]

    assert t1_node.depth == 1
    assert t2_node.depth == 2
    assert t3_node.depth == 3


@bw2test
def test_breadth_first_with_max_depth():
    """Test that max_depth stops traversal at the correct level."""
    Database("t").write(
        {
            ("t", "1"): {
                "name": "1",
                "exchanges": [
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "1"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "2"): {
                "name": "2",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 2,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "3"): {
                "name": "3",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
        }
    )

    lca = LCA({("t", "1"): 1})
    lca.lci()

    # Limit to depth 2
    settings = GraphTraversalSettings(max_calc=100, max_depth=2)
    bfgt = BreadthFirstGraphTraversal(lca, settings)
    bfgt.traverse()

    nodes = bfgt.nodes
    edges = bfgt.edges

    # Should have 3 nodes: functional unit + activities 1 and 2 (not 3 due to depth limit)
    assert len(nodes) == 3
    # Should have 2 edges
    assert len(edges) == 2


@bw2test
def test_breadth_first_with_static_activities():
    """Test that static activities stop traversal."""
    Database("t").write(
        {
            ("t", "1"): {
                "name": "1",
                "exchanges": [
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "1"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "2"): {
                "name": "2",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 2,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "3"): {
                "name": "3",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
        }
    )

    lca = LCA({("t", "1"): 1})
    lca.lci()

    t2_index = lca.dicts.activity[get_node(code="2").id]

    # Mark activity 2 as static
    settings = GraphTraversalSettings(max_calc=100)
    bfgt = BreadthFirstGraphTraversal(
        lca, settings, static_activity_indices={t2_index}
    )
    bfgt.traverse()

    nodes = bfgt.nodes
    edges = bfgt.edges

    # Should have 3 nodes: functional unit + activities 1 and 2 (not 3 because 2 is static)
    assert len(nodes) == 3
    # Should have 2 edges
    assert len(edges) == 2


@bw2test
def test_breadth_first_with_multiple_inputs():
    """Test breadth-first traversal with a node having multiple inputs."""
    Database("t").write(
        {
            ("t", "1"): {
                "name": "1",
                "exchanges": [
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "3"),
                        "amount": 2,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "1"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "2"): {
                "name": "2",
                "exchanges": [
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "3"): {
                "name": "3",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
        }
    )

    lca = LCA({("t", "1"): 1})
    lca.lci()

    settings = GraphTraversalSettings(max_calc=100)
    bfgt = BreadthFirstGraphTraversal(lca, settings)
    bfgt.traverse()

    nodes = bfgt.nodes
    edges = bfgt.edges

    # Should have 4 nodes: functional unit + 3 activities
    assert len(nodes) == 4
    # Should have 3 edges (1 -> 2, 1 -> 3, and FU -> 1)
    assert len(edges) == 3

    # Both activity 2 and 3 should be at depth 2
    t2_nodes = [n for n in nodes.values() if n.activity_datapackage_id == get_node(code="2").id]
    t3_nodes = [n for n in nodes.values() if n.activity_datapackage_id == get_node(code="3").id]
    
    assert len(t2_nodes) == 1
    assert len(t3_nodes) == 1
    assert t2_nodes[0].depth == 2
    assert t3_nodes[0].depth == 2


@bw2test
def test_breadth_first_with_max_calc():
    """Test that max_calc limits the number of nodes processed."""
    Database("t").write(
        {
            ("t", "1"): {
                "name": "1",
                "exchanges": [
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "1"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "2"): {
                "name": "2",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 2,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "3"): {
                "name": "3",
                "exchanges": [
                    {
                        "input": ("t", "3"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
        }
    )

    lca = LCA({("t", "1"): 1})
    lca.lci()

    # Limit to only 2 calculations (should stop before processing all nodes)
    settings = GraphTraversalSettings(max_calc=2)
    bfgt = BreadthFirstGraphTraversal(lca, settings)
    bfgt.traverse()

    nodes = bfgt.nodes
    # Should have stopped early due to max_calc
    assert len(nodes) <= 3  # functional unit + at most 2 activities


@bw2test
def test_breadth_first_terminal_nodes():
    """Test that terminal flag is set correctly."""
    Database("t").write(
        {
            ("t", "1"): {
                "name": "1",
                "exchanges": [
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "technosphere",
                    },
                    {
                        "input": ("t", "1"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
            ("t", "2"): {
                "name": "2",
                "exchanges": [
                    {
                        "input": ("t", "2"),
                        "amount": 1,
                        "type": "production",
                    },
                ],
            },
        }
    )

    lca = LCA({("t", "1"): 1})
    lca.lci()

    settings = GraphTraversalSettings(max_calc=100)
    bfgt = BreadthFirstGraphTraversal(lca, settings)
    bfgt.traverse()

    nodes = bfgt.nodes

    # Activity 2 should be terminal (no outgoing edges)
    t2_node = [n for n in nodes.values() if n.activity_datapackage_id == get_node(code="2").id][0]
    assert t2_node.terminal is True

    # Activity 1 and functional unit should not be terminal
    t1_node = [n for n in nodes.values() if n.activity_datapackage_id == get_node(code="1").id][0]
    fu_node = nodes[-1]
    assert t1_node.terminal is False
    assert fu_node.terminal is False

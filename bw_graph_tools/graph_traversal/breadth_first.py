from collections import deque
from typing import Dict, List, Optional

import matrix_utils as mu
import numpy as np
from bw2calc import LCA
from scipy.sparse import spmatrix

try:
    from bw2data import databases
except ImportError:
    databases = {}

from bw_graph_tools.graph_traversal.breadth_first_objects import SimplifiedEdge, SimplifiedNode
from bw_graph_tools.graph_traversal.settings import BreadthFirstSettings
from bw_graph_tools.graph_traversal.utils import Counter, get_demand_vector_for_activity
from bw_graph_tools.matrix_tools import guess_production_exchanges


class BreadthFirstGraphTraversal:
    """
    Traverse a supply chain using breadth-first search, visiting all edges at each level.

    This is a simplified version of NewNodeEachVisitGraphTraversal that:
    - Traverses ALL edges of ALL nodes on each supply chain level
    - Continues until static activities are reached
    - Does not require calculating scores or cumulative impacts
    - Uses simplified Node and Edge classes without score requirements

    This implementation uses a queue (FIFO) instead of a priority heap, processing nodes
    level-by-level until reaching static activities or the maximum depth.

    You must provide an `lca_object` which is already instantiated. The `lca_object` does 
    not have to be an instance of `bw2calc.LCA`, but it needs to support the following 
    methods and attributes:

    * `technosphere_matrix`
    * `technosphere_mm`
    * `demand`

    Parameters
    ----------
    lca : bw2calc.LCA
        Already instantiated `LCA` object with inventory calculated.
    settings : BreadthFirstSettings
        Settings for the breadth-first traversal
    functional_unit_unique_id : int
        An integer id we can use for the functional unit virtual activity.
        Shouldn't overlap any other activity ids. Don't change unless you
        really know what you are doing.
    static_activity_indices : set
        A set of activity matrix indices which we don't want the graph to
        traverse - i.e. we stop traversal when we hit these nodes, but
        still add them to the returned `nodes` dictionary.

    Examples
    --------
    Basic usage:

    >>> from bw2calc import LCA
    >>> from bw_graph_tools import BreadthFirstGraphTraversal, BreadthFirstSettings
    >>>
    >>> lca = LCA({("my_db", "my_activity"): 1})
    >>> lca.lci()
    >>>
    >>> settings = BreadthFirstSettings(max_calc=1000, max_depth=5)
    >>> bfgt = BreadthFirstGraphTraversal(lca, settings)
    >>> bfgt.traverse()
    >>>
    >>> print(f"Traversed {len(bfgt.nodes)} nodes")
    >>> print(f"Found {len(bfgt.edges)} edges")

    With static activities:

    >>> static_indices = {activity_index_1, activity_index_2}
    >>> bfgt = BreadthFirstGraphTraversal(lca, settings, static_activity_indices=static_indices)
    >>> bfgt.traverse()
    """

    def __init__(
        self,
        lca: LCA,
        settings: BreadthFirstSettings,
        functional_unit_unique_id: int = -1,
        static_activity_indices=None,
    ):
        if static_activity_indices is None:
            static_activity_indices = set()
        self.lca = lca
        self.settings = settings
        self.static_activity_indices = static_activity_indices

        # internal properties
        self._functional_unit_unique_id = functional_unit_unique_id
        self._max_calc = self.settings.max_calc
        self._calculation_count = Counter()
        self._root_node = SimplifiedNode(
            unique_id=functional_unit_unique_id,
            activity_datapackage_id=functional_unit_unique_id,
            activity_index=functional_unit_unique_id,
            reference_product_datapackage_id=functional_unit_unique_id,
            reference_product_index=functional_unit_unique_id,
            reference_product_production_amount=1.0,
            depth=0,
            supply_amount=1.0,
        )
        self._nodes: Dict[int, SimplifiedNode] = {
            self._functional_unit_unique_id: self._root_node
        }
        self._edges: List[SimplifiedEdge] = []
        self.production_exchange_mapping = {
            x: y for x, y in zip(*self.get_production_exchanges(self.lca.technosphere_mm))
        }

    @property
    def nodes(self):
        """
        Dictionary of `SimplifiedNode` dataclass instances.
        Keys are unique_id integers, values are SimplifiedNode instances.
        """
        return self._nodes

    @property
    def edges(self):
        """
        List of `SimplifiedEdge` instances. Edges link two `SimplifiedNode` instances.
        """
        return self._edges

    @property
    def calculation_count(self):
        """
        Total number of nodes processed during traversal.
        """
        return self._calculation_count.value + 1

    @property
    def exceeded_calculation_count(self):
        return self.calculation_count > self._max_calc

    @classmethod
    def get_production_exchanges(
        cls, mapped_matrix: mu.MappedMatrix
    ) -> (np.array, np.array):
        """
        Get matrix row and column indices of productions exchanges by trying a
        series of heuristics. See documentation for ``guess_production_exchanges``.

        Parameters
        ----------
        mapped_matrix : matrix_utils.MappedMatrix
            A matrix and mapping data (from database ids to matrix indices)
            from the ``matrix_utils`` library.

        Returns
        -------
        (numpy.array, numpy.array)
            The matrix row and column indices of the production exchanges.
        """
        return guess_production_exchanges(mapped_matrix)

    def traverse(
        self,
        nodes: Optional[List[SimplifiedNode]] = None,
        depth: Optional[int] = None,
        reset_results: bool = False,
    ) -> None:
        """
        Perform breadth-first graph traversal.

        If `nodes` is not specified, start at the given functional unit. If `nodes` is 
        specified, *only* traverse the graph starting from the given nodes.

        Parameters
        ----------
        nodes : List[SimplifiedNode]
            List of nodes to traverse. Uses the functional unit (`self._root_node`) as 
            the default
        depth : int
            Relative depth to traverse for each node provided up to `settings.max_depth`
        reset_results : bool
            Reset `self.nodes` and `self.edges`.

        Returns
        -------
        None
            Modifies the class object's state in-place
        """
        if reset_results:
            self._nodes: Dict[int, SimplifiedNode] = {}
            self._edges: List[SimplifiedEdge] = []

        if nodes is None:
            self._nodes[self._functional_unit_unique_id] = self._root_node
            self._traverse_breadth_first([self._root_node], depth)
        else:
            for node in nodes:
                node.max_depth = self._max_depth_for_node(node, depth)
                node.depth = 0
                self._nodes[node.unique_id] = node
            self._traverse_breadth_first(nodes, depth)

        # Mark terminal nodes
        non_terminal_nodes = {edge.consumer_unique_id for edge in self._edges}
        for key, obj in self._nodes.items():
            obj.terminal = key not in non_terminal_nodes

    def _max_depth_for_node(
        self, node: SimplifiedNode, relative_depth: Optional[int] = None
    ) -> Optional[int]:
        """Find `max_depth` for a given node when inputs are all optional."""
        if relative_depth is None and self.settings.max_depth is None:
            return None
        elif self.settings.max_depth is None:
            return node.depth + relative_depth
        elif relative_depth is None:
            return self.settings.max_depth
        else:
            return min(node.depth + relative_depth, self.settings.max_depth)

    def _traverse_breadth_first(
        self, start_nodes: List[SimplifiedNode], relative_depth: Optional[int] = None
    ):
        """
        Traverse the graph breadth-first, processing all nodes at each level before
        moving to the next level.

        Parameters
        ----------
        start_nodes : List[SimplifiedNode]
            Initial nodes to start traversal from
        relative_depth : int
            Relative depth limit for traversal
        """
        queue = deque(start_nodes)

        while queue:
            if self.exceeded_calculation_count:
                break

            node = queue.popleft()

            # Check depth constraints
            if node.max_depth is not None:
                if node.depth >= node.max_depth:
                    continue
            elif self.settings.max_depth is not None:
                if node.depth >= self.settings.max_depth:
                    continue

            # Skip if this is a static activity
            if node.activity_index in self.static_activity_indices:
                continue

            # Get demand vector for this node
            product_indices, product_amounts = self._get_demand_vector_for_activity(
                node=node,
                skip_coproducts=self.settings.skip_coproducts,
                matrix=self.lca.technosphere_matrix,
            )

            # Process all edges from this node
            for product_index, product_amount in zip(product_indices, product_amounts):
                if self.exceeded_calculation_count:
                    break

                producer_index = self.production_exchange_mapping[product_index]
                reference_product_net_production_amount = self.lca.technosphere_matrix[
                    product_index, producer_index
                ]
                scale = product_amount / reference_product_net_production_amount

                producing_node = SimplifiedNode(
                    unique_id=next(self._calculation_count),
                    activity_datapackage_id=self.lca.dicts.activity.reversed[producer_index],
                    activity_index=producer_index,
                    reference_product_datapackage_id=self.lca.dicts.product.reversed[
                        product_index
                    ],
                    reference_product_index=product_index,
                    reference_product_production_amount=reference_product_net_production_amount,
                    depth=node.depth + 1,
                    supply_amount=scale,
                    max_depth=node.max_depth,
                )

                self._nodes[producing_node.unique_id] = producing_node

                self._edges.append(
                    SimplifiedEdge(
                        consumer_index=node.activity_index,
                        consumer_unique_id=node.unique_id,
                        producer_index=producer_index,
                        producer_unique_id=producing_node.unique_id,
                        product_index=product_index,
                        amount=product_amount,
                    )
                )

                # Add producing node to queue if not a static activity
                if producer_index not in self.static_activity_indices:
                    queue.append(producing_node)

    def _get_demand_vector_for_activity(
        self,
        node: SimplifiedNode,
        skip_coproducts: bool,
        matrix: spmatrix,
    ) -> (list[int], list[float]):
        """
        Get demand vector for a node. Special handling for root node.
        """
        if node is self._root_node:
            product_indices = [self.lca.dicts.product[key] for key in self.lca.demand]
            product_amounts = list(self.lca.demand.values())
            return product_indices, product_amounts

        return get_demand_vector_for_activity(
            node=node, skip_coproducts=skip_coproducts, matrix=matrix
        )

from dataclasses import dataclass
from typing import Optional


@dataclass
class SimplifiedNode:
    """
    A simplified node for breadth-first traversal without score requirements.
    
    Parameters
    ----------
    unique_id : int
        A unique integer id for this visit to this activity node
    activity_datapackage_id : int
        The id that identifies this activity in the datapackage, and hence in the database
    activity_index : int
        The technosphere matrix column index of this activity
    reference_product_datapackage_id : int
        The id that identifies the reference product of this activity in the datapackage
    reference_product_index : int
        The technosphere matrix row index of this activity's reference product
    reference_product_production_amount : float
        The *net* production amount of this activity's reference product
    depth : int
        Depth in the supply chain graph, starting from 0 as the functional unit
    supply_amount : float
        The amount of the *activity* (not reference product!) needed to supply the demand from the
        requesting supply chain edge.
    terminal : bool
        Boolean flag indicating whether graph traversal was cutoff at this node
    """

    unique_id: int
    activity_datapackage_id: int
    activity_index: int
    reference_product_datapackage_id: int
    reference_product_index: int
    reference_product_production_amount: float
    depth: int
    supply_amount: float
    max_depth: Optional[int] = None
    terminal: bool = False


@dataclass
class SimplifiedEdge:
    """
    A simplified edge between two `SimplifiedNode` instances. The `amount` is the amount of the 
    product demanded by the `consumer`.

    Parameters
    ----------
    consumer_index : int
        The matrix column index of the consuming activity
    consumer_unique_id : int
        The traversal-specific unique id of the consuming activity
    producer_index : int
        The matrix column index of the producing activity
    producer_unique_id : int
        The traversal-specific unique id of the producing activity
    product_index : int
        The matrix row index of the consumed product
    amount : float
        The amount of the product demanded by the consumer. Not scaled to producer production
        amount.
    """

    consumer_index: int
    consumer_unique_id: int
    producer_index: int
    producer_unique_id: int
    product_index: int
    amount: float

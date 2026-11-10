"""Weighted NetworkX Max-Cut instances in the shared minimization QUBO format."""

from math import fsum, isfinite

from app.schemas.contracts import QUBO, GraphInput


class MaxCutConversionError(ValueError):
    """Finite graph weights cannot be represented by finite QUBO coefficients."""


def maxcut_to_qubo(problem: GraphInput) -> QUBO:
    """Minimize negative cut weight, with vertex i represented by API bit x[i].

    Each edge contributes -w*x[i] - w*x[j] + 2*w*x[i]*x[j]. The existing
    GraphInput contract supplies unique undirected edges and finite signed weights.
    Isolated vertices retain their indices. Zero-weight edges contribute zero.
    The supplied model is read-only. Import NetworkX only when conversion runs.
    """
    import networkx as nx

    graph = nx.Graph()
    graph.add_nodes_from(range(problem.num_vertices))
    graph.add_weighted_edges_from(
        (edge.i, edge.j, edge.coefficient)
        for edge in sorted(problem.edges, key=lambda edge: (edge.i, edge.j))
    )
    try:
        linear = [
            -fsum(weight for _, _, weight in graph.edges(vertex, data="weight"))
            for vertex in range(problem.num_vertices)
        ]
    except OverflowError as error:
        raise MaxCutConversionError("Max-Cut coefficient overflow; rescale edge weights") from error
    quadratic = [
        {"i": min(i, j), "j": max(i, j), "coefficient": 2 * weight}
        for i, j, weight in graph.edges(data="weight")
    ]
    if not all(isfinite(value) for value in linear) or not all(
        isfinite(term["coefficient"]) for term in quadratic
    ):
        raise MaxCutConversionError("Max-Cut coefficient overflow; rescale edge weights")
    return QUBO(
        num_variables=problem.num_vertices,
        linear=linear,
        quadratic=quadratic,
        original_sense="maximize",
    )

"""Run the benchmark locally with python -m app.experiments.search."""

from app.experiments.search.runner import run_search
from app.schemas.contracts import SearchRequest


def main() -> None:
    request = SearchRequest(num_qubits=3, marked_states=["001"])
    print(run_search(request).model_dump_json(indent=2))


if __name__ == "__main__":
    main()

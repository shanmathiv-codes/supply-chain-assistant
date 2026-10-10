"""Smoke test for LangGraph."""

from typing import TypedDict

from langgraph.graph import END, StateGraph


class SimpleState(TypedDict):
    step: str
    count: int


def node_a(state: SimpleState) -> SimpleState:
    return {"step": "node_a", "count": state["count"] + 1}


def node_b(state: SimpleState) -> SimpleState:
    return {"step": "node_b", "count": state["count"] + 2}


def run_smoke():
    builder = StateGraph(SimpleState)
    builder.add_node("a", node_a)
    builder.add_node("b", node_b)
    builder.set_entry_point("a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)

    graph = builder.compile()
    res = graph.invoke({"step": "start", "count": 0})
    assert res["count"] == 3
    assert res["step"] == "node_b"
    print("LangGraph smoke test passed: result count = 3")


if __name__ == "__main__":
    run_smoke()

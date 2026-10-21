"""
MicrobeGraph, graph analytics (Phase 5).

WHAT THIS PACKAGE DOES
    Until Phase 4c the project built the graph. From here it asks the graph
    questions. Each module answers one kind:

        labels.py           what to call a node in a table or a picture
                            (a protein becomes "dauE (aklaviketone reductase)")
        evidence_paths.py   which microbes might help a crop, by which route,
                            and how strong each step's evidence is
        centrality.py       which nodes are hubs (many arrows) and which are
                            bridges (on many routes between other nodes)
        communities.py      which nodes form groups that link mostly to each
                            other
        pictures.py         interactive pages you open in a browser (pyvis
                            for networks, plotly for charts)

    python -m microbegraph.analyze runs them (see src/microbegraph/analyze.py)
    and docs/07-graph-analytics.md explains each one from the start.

THE GROUND RULES
    * The database stays the one source of truth. Everything here reads the
      graph that build_graph.load_graph() rebuilds from it, read-only, and
      writes its results BESIDE it, in data/processed/analytics/. Nothing in
      this package changes a node or an arrow.
    * Every result can be repeated. Community detection and the whole-graph
      betweenness estimate start from a fixed random seed, and every list is
      sorted with a tie-break on names or identifiers, so the same graph
      always gives the same CSV files (the summary and the pages also record
      when they were made).
    * A path is only as strong as its weakest arrow (ontology.evidence_rank),
      and every path is shown with the evidence of each of its arrows.
"""

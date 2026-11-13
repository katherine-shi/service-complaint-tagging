"""Step 3: check the LLM's category against NHTSA's own component labels."""
import pandas as pd

from .config import map_nhtsa_components


def run(conn) -> dict:
    df = pd.read_sql_query(
        """SELECT c.odi_number, c.nhtsa_components, t.category
           FROM tags t JOIN complaints c USING (odi_number)""",
        conn,
    )
    if df.empty:
        raise SystemExit("No tagged complaints yet. Run the tag step first.")
    df["nhtsa_categories"] = df["nhtsa_components"].apply(map_nhtsa_components)
    # A complaint can carry several NHTSA components; the LLM picks one primary
    # category, so it counts as agreeing when its pick is among NHTSA's.
    df["agree"] = [cat in ref for cat, ref in zip(df["category"], df["nhtsa_categories"])]
    by_category = (
        df.groupby("category")["agree"].agg(complaints="count", agreement="mean")
        .sort_values("complaints", ascending=False)
        .reset_index()
    )
    by_category["agreement"] = (by_category["agreement"] * 100).round(1)
    disagreements = df.loc[~df["agree"], ["odi_number", "nhtsa_components", "category"]]
    return {
        "n": len(df),
        "agreement_pct": round(df["agree"].mean() * 100, 1),
        "by_category": by_category,
        "disagreements": disagreements,
    }

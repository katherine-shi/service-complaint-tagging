"""Step 4: run the SQL analysis and write the summary report automatically."""
import re
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import evaluate
from .config import MAKE, MODELS, MODEL_YEARS, REPORT_DIR, ROOT


def load_queries() -> dict:
    text = (ROOT / "sql" / "analysis.sql").read_text()
    parts = re.split(r"-- name: (\w+)\n", text)[1:]
    return dict(zip(parts[0::2], (q.strip() for q in parts[1::2])))


def run(conn):
    REPORT_DIR.mkdir(exist_ok=True)
    q = {name: pd.read_sql_query(sql, conn) for name, sql in load_queries().items()}
    ev = evaluate.run(conn)
    tagger = ", ".join(
        f"`{name}` ({n})"
        for name, n in conn.execute(
            "SELECT tagger, COUNT(*) FROM tags GROUP BY tagger ORDER BY COUNT(*) DESC"
        )
    )

    vol = q["volume_by_category"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(vol["category"][::-1], vol["complaints"][::-1], color="#3b6ea5")
    ax.set_xlabel("Complaints")
    ax.set_title("Tagged complaints by vehicle system")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "volume_by_category.png", dpi=150)
    plt.close(fig)

    top = vol.iloc[0]
    lines = [
        f"# {MAKE.title()} service complaint summary",
        "",
        f"Generated {date.today().isoformat()} from {ev['n']} NHTSA complaints "
        f"({', '.join(m.title() for m in MODELS)}, model years {MODEL_YEARS[0]}-{MODEL_YEARS[-1]}), "
        f"tagged by {tagger}.",
        "",
        "## Headline",
        "",
        f"- **{top['category']}** is the largest category: {top['complaints']} complaints "
        f"({top['share_pct']}% of the total), {top['safety_critical_pct']}% of them safety-critical.",
        f"- The LLM's category agrees with NHTSA's own component label on "
        f"**{ev['agreement_pct']}%** of complaints.",
        "",
        "## Volume by vehicle system",
        "",
        "![Complaints by vehicle system](volume_by_category.png)",
        "",
        vol.to_markdown(index=False),
        "",
        "## Failure type mix",
        "",
        q["failure_type_mix"].to_markdown(index=False),
        "",
        "## Out-of-pocket repair cost stated by owners",
        "",
        "Only complaints where the owner states an amount; categories with fewer than 3 are left out.",
        "",
        q["out_of_pocket_cost"].to_markdown(index=False)
        if not q["out_of_pocket_cost"].empty else "_Not enough complaints state a cost._",
        "",
        "## Complaints filed per month",
        "",
        q["monthly_trend"].to_markdown(index=False),
        "",
        "## Tagging quality",
        "",
        "Agreement means the LLM's single category is among the categories NHTSA assigned. "
        "The LLM only sees the complaint text, never NHTSA's label.",
        "",
        ev["by_category"].to_markdown(index=False),
        "",
        f"{len(ev['disagreements'])} disagreements are listed in `disagreements.csv` for manual review.",
        "",
    ]
    (REPORT_DIR / "report.md").write_text("\n".join(lines))
    q["category_by_model_year"].to_csv(REPORT_DIR / "category_by_model_year.csv", index=False)
    ev["disagreements"].to_csv(REPORT_DIR / "disagreements.csv", index=False)
    print(f"Agreement with NHTSA labels: {ev['agreement_pct']}% on {ev['n']} complaints")
    print(f"Report written to {REPORT_DIR / 'report.md'}")

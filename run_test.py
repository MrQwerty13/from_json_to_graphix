import os
import traceback
from json_to_graphix.json_reader import read_json
from json_to_graphix.json_formatter import format_for_analytics
from json_to_graphix.analyzer import create_graphs
from json_to_graphix.report_generator import generate_conclusion_and_pdf


def main():
    try:
        path = "sample_data.json"
        data = read_json(path)
        outdir = os.path.join("static", "outputs", "sample_data.json")
        csv_path, pretty_json_path, df = format_for_analytics(data, outdir)
        print("Wrote:", csv_path, pretty_json_path)

        graphs = create_graphs(df, outdir)
        print("Generated graphs:")
        for g in graphs:
            print(" -", g.get("path"), g.get("desc"))

        pdf_path = os.path.join(outdir, "report.pdf")
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        conclusion = generate_conclusion_and_pdf("Quick summary of sample data.", pdf_path, graph_infos=graphs, try_ollama=False)
        print("PDF written:", pdf_path)
        print("Conclusion sample:\n", conclusion)
    except Exception as e:
        print("ERROR during test run:")
        traceback.print_exc()


if __name__ == "__main__":
    main()

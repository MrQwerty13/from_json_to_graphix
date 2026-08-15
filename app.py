import os
from flask import Flask, request, render_template, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
from json_to_graphix.json_reader import read_json_from_fileobj
from json_to_graphix.json_formatter import format_for_analytics
from json_to_graphix.analyzer import create_graphs
from json_to_graphix.report_generator import generate_conclusion_and_pdf, ai_continue_json
import io
import json
from pathlib import Path

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "static/outputs"
ALLOWED_EXTENSIONS = {"json"}

app = Flask(__name__, template_folder="templates")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return render_template("upload.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return redirect(url_for("index"))
    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.stream.seek(0)
    with open(upload_path, "wb") as f:
        f.write(file.read())

    # Re-open for parsing
    with open(upload_path, "r", encoding="utf-8") as f:
        data = read_json_from_fileobj(f)

    output_dir = os.path.join(app.config["OUTPUT_FOLDER"], filename)
    csv_path, pretty_json_path, df = format_for_analytics(data, output_dir)
    graphs_meta = create_graphs(df, output_dir)

    # Convert graph paths to web paths for the template
    web_graphs = []
    for g in graphs_meta:
        path = g.get("path")
        rel = os.path.relpath(path, "static")
        web_graphs.append((rel.replace(os.path.sep, "/"), g.get("desc")))

    # Also provide links to formatted files
    formatted_csv = os.path.relpath(csv_path, ".").replace(os.path.sep, "/")
    formatted_json = os.path.relpath(pretty_json_path, ".").replace(os.path.sep, "/")

    columns = df.columns.tolist()

    return render_template(
        "result.html",
        graphs=web_graphs,
        csv_path=formatted_csv,
        json_path=formatted_json,
        columns=columns,
        upload_filename=filename,
    )



@app.route("/create_json", methods=["GET"]) 
def create_json_form():
    return render_template("create_json.html")


@app.route("/create_json", methods=["POST"]) 
def create_json():
    payload = request.form.get("content", "")
    lines = [l for l in payload.splitlines() if l.strip()]
    if len(lines) < 3:
        return render_template("create_json.html", error="Please provide at least 3 non-empty lines as a starting point.")

    existing = "\n".join(lines)
    ai_out = ai_continue_json(existing, try_ollama=True)

    if not ai_out:
        # fallback: just wrap lines into array of strings
        result_text = "[\n" + ",\n".join([json.dumps(l) for l in lines]) + "\n]"
    else:
        result_text = ai_out

    # Try to parse and pretty-print
    try:
        parsed = json.loads(result_text)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
    except Exception:
        pretty = result_text

    # Save to uploads
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    fname = f"created_{int(Path().stat().st_mtime)}.json"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(pretty)

    return render_template("create_json.html", result_path=os.path.relpath(save_path, ".").replace(os.path.sep, "/"), pretty=pretty)


@app.route("/download_grouped/<upload_filename>")
def download_grouped(upload_filename):
    # group_by query param
    group_by = request.args.get("group_by")
    if not group_by:
        return ("group_by parameter required", 400)

    pretty_path = os.path.join(app.config["OUTPUT_FOLDER"], upload_filename, "formatted.json")
    if not os.path.exists(pretty_path):
        return ("formatted data not found", 404)

    with open(pretty_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # If records is a dict, wrap
    if isinstance(records, dict):
        records_list = [records]
    else:
        records_list = records

    groups = {}
    for rec in records_list:
        key = rec.get(group_by, "<MISSING>")
        groups.setdefault(str(key), []).append(rec)

    # Build grouped output (sorted keys)
    out = {k: groups[k] for k in sorted(groups.keys())}

    bio = io.BytesIO()
    bio.write(json.dumps(out, indent=2, ensure_ascii=False).encode("utf-8"))
    bio.seek(0)
    return send_file(bio, as_attachment=True, download_name=f"grouped_{group_by}.json", mimetype="application/json")


@app.route("/generate_report/<upload_filename>")
def generate_report(upload_filename):
    pretty_path = os.path.join(app.config["OUTPUT_FOLDER"], upload_filename, "formatted.json")
    output_pdf = os.path.join(app.config["OUTPUT_FOLDER"], upload_filename, "report.pdf")
    if not os.path.exists(pretty_path):
        return ("formatted data not found", 404)

    with open(pretty_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Build a short summary from records
    summary_lines = []
    if isinstance(records, list):
        summary_lines.append(f"Records: {len(records)}")
        # sample first record keys
        if records:
            sample = records[0]
            summary_lines.append("Fields: " + ", ".join(list(sample.keys())[:20]))
    else:
        summary_lines.append("Single JSON object")

    summary_text = "\n".join(summary_lines)

    # Recompute graphs metadata to ensure stats are available
    import pandas as pd

    try:
        if isinstance(records, list):
            df = pd.json_normalize(records)
        else:
            df = pd.json_normalize([records])
    except Exception:
        df = pd.DataFrame(records)

    graphs_meta = create_graphs(df, os.path.join(app.config["OUTPUT_FOLDER"], upload_filename))

    # generate pdf (try ollama if available)
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    conclusion = generate_conclusion_and_pdf(summary_text, output_pdf, graph_infos=graphs_meta, try_ollama=True)

    # Return JSON with link to pdf and the text
    pdf_rel = os.path.relpath(output_pdf, ".").replace(os.path.sep, "/")
    return jsonify({"pdf": pdf_rel, "conclusion": conclusion})


if __name__ == "__main__":
    app.run(debug=True)

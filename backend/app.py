"""
FactChecker Backend — Flask API avec import de fichiers
Supporte : texte brut, PDF, Word (.docx), TXT
"""

import os
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
from fact_checker import FactChecker
from document_reader import read_document

app = Flask(__name__)
CORS(app)

# Taille max upload : 20 Mo
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

checker = FactChecker()


@app.route("/api/check", methods=["POST"])
def check_article():
    """Vérifie un texte brut envoyé en JSON."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Le champ 'text' est requis"}), 400

    text = data["text"].strip()
    if len(text) < 50:
        return jsonify({"error": "Le texte doit contenir au moins 50 caractères"}), 400
    if len(text) > 50000:
        return jsonify({"error": "Le texte ne doit pas dépasser 50 000 caractères"}), 400

    try:
        result = checker.analyze(text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Erreur lors de l'analyse: {str(e)}"}), 500


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """
    Reçoit un fichier (PDF, DOCX, TXT), extrait le texte,
    puis lance l'analyse fact-checking.
    """
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nom de fichier vide"}), 400

    filename = file.filename.lower()
    allowed = [".pdf", ".docx", ".doc", ".txt", ".rtf"]
    if not any(filename.endswith(ext) for ext in allowed):
        return jsonify({"error": f"Format non supporté. Formats acceptés : PDF, DOCX, TXT"}), 400

    try:
        file_bytes = file.read()
        # Extraire le texte selon le type de fichier
        text, page_count = read_document(file_bytes, filename)

        if not text or len(text.strip()) < 50:
            return jsonify({"error": "Impossible d'extraire du texte de ce fichier"}), 400

        print(f"[UPLOAD] Fichier: {file.filename} | {page_count} page(s) | {len(text)} caractères extraits")

        # Analyser le texte extrait
        result = checker.analyze(text)
        result["filename"] = file.filename
        result["page_count"] = page_count
        result["char_count"] = len(text)

        return jsonify(result)

    except Exception as e:
        print(f"[UPLOAD ERREUR] {e}")
        return jsonify({"error": f"Erreur lors de la lecture du fichier: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "FactChecker API en ligne (Groq + Upload)"})


if __name__ == "__main__":
    print("=" * 55)
    print("  FactChecker API — http://localhost:5000")
    print("  Moteur IA : Groq llama-3.3 (gratuit)")
    print("  Import    : PDF, DOCX, TXT supportés")
    print("=" * 55)
    app.run(debug=True, port=5000)

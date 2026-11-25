import os
import re
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # 16 KB request limit

MAX_PROMPT_LENGTH = 5000
CRITERIA = {
    "Clear task": 20,
    "Context": 20,
    "Specific details": 20,
    "Output format": 20,
    "Constraints": 20,
}
ACTION_VERBS = {
    "analyze", "build", "classify", "compare", "create", "define", "describe",
    "design", "develop", "draft", "explain", " generate", "generate", " list",
    "make", "plan", "rewrite", "review", "summarize", "translate", "write",
}
FORMAT_TERMS = {
    "bullet", "bullets", "table", "paragraph", "json", "csv", "markdown",
    "numbered list", "step-by-step", "steps", "checklist", "outline",
}
CONSTRAINT_TERMS = {
    "must", "should", "avoid", "don't", "do not", "under", "within",
    "maximum", "minimum", "limit", "tone", "include", "exclude", "no more than",
}


def contains_any(text, terms):
    return any(term.strip() in text for term in terms)


def analyze_prompt(prompt):
    """Score prompt structure with transparent, explainable heuristics."""
    normalized = re.sub(r"\s+", " ", prompt.lower()).strip()
    words = re.findall(r"\b[\w'-]+\b", normalized)

    checks = {
        "Clear task": contains_any(normalized, ACTION_VERBS),
        "Context": contains_any(normalized, {
            "for", "about", "context", "audience", "purpose", "scenario",
            "background", "target users", "intended for",
        }),
        "Specific details": (
            len(words) >= 15
            or bool(re.search(r"\b\d+\b", normalized))
            or contains_any(normalized, {"for example", "such as", "including"})
        ),
        "Output format": contains_any(normalized, FORMAT_TERMS),
        "Constraints": contains_any(normalized, CONSTRAINT_TERMS),
    }
    score = sum(CRITERIA[name] for name, passed in checks.items() if passed)

    suggestions = []
    if not checks["Clear task"]:
        suggestions.append("Begin with a direct action, such as explain, create, compare, or summarize.")
    if not checks["Context"]:
        suggestions.append("Add context: who the result is for, the situation, and the goal.")
    if not checks["Specific details"]:
        suggestions.append("Include useful details, examples, quantities, or the scope of the task.")
    if not checks["Output format"]:
        suggestions.append("Tell the assistant how to present the result, such as a table, bullets, or steps.")
    if not checks["Constraints"]:
        suggestions.append("Add constraints such as length, tone, required points, or things to avoid.")
    if not suggestions:
        suggestions.append("Your prompt covers all five checks. Add a sample input/output if you need even more consistency.")

    return score, checks, suggestions


def improve_prompt(prompt):
    return (
        "Act as a knowledgeable, careful subject-matter expert.\n\n"
        f"Task:\n{prompt.strip()}\n\n"
        "Instructions:\n"
        "1. Identify the intended goal and audience before answering.\n"
        "2. Use accurate, relevant, and practical information.\n"
        "3. Follow the requested format and all stated constraints.\n"
        "4. Organize the response with clear headings and concise steps where useful.\n"
        "5. Do not invent facts. Clearly state uncertainty and assumptions.\n"
        "6. If essential information is missing, ask a focused clarifying question.\n\n"
        "Deliverable:\nProvide a complete, useful response that directly addresses the task."
    )


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    return response


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if not request.is_json:
        return jsonify({"error": "Send the prompt as JSON with Content-Type: application/json."}), 415

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON body. Expected an object containing 'prompt'."}), 400

    raw_prompt = data.get("prompt")
    if not isinstance(raw_prompt, str):
        return jsonify({"error": "The prompt must be text."}), 400

    prompt = raw_prompt.strip()
    if len(prompt) < 3:
        return jsonify({"error": "Please enter a prompt with at least 3 characters."}), 400
    if len(prompt) > MAX_PROMPT_LENGTH:
        return jsonify({"error": f"Prompt is too long. Maximum length is {MAX_PROMPT_LENGTH} characters."}), 413

    score, checks, suggestions = analyze_prompt(prompt)
    return jsonify({
        "score": score,
        "checks": checks,
        "suggestions": suggestions,
        "improved": improve_prompt(prompt),
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Request is too large. Please shorten your prompt."}), 413


@app.errorhandler(500)
def internal_error(_error):
    app.logger.exception("Unexpected server error")
    return jsonify({"error": "An unexpected server error occurred. Please try again."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
